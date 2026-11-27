import os
from types import SimpleNamespace

import requests
import responses
from mutagen.id3 import ID3

from bandcamp_dl import __version__
from bandcamp_dl.bandcampdownloader import BandcampDownloader, DOWNLOAD_CHUNK_SIZE

TRACK_URL = "https://t4.bcbits.com/stream/abc/mp3-128/1"
# 20 silent MPEG-1 Layer III frames (128 kbps, 44.1 kHz, 417 bytes each)
MP3_BYTES = (b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20

ALBUM = {"tracks": [{"duration": 1.0, "track": "1", "title": "One", "artist": "Loopy",
                    "track_id": 1, "url": TRACK_URL}],
         "title": "First", "artist": "Loopy", "label": None, "full": True, "art": "",
         "date": "2026", "url": "https://loopy.bandcamp.com/album/first", "genres": "",
         "album_id": 7}


def make_downloader(base_dir):
    config = SimpleNamespace(
        limit_req_per_minute=0, template="%{artist}/%{album}/%{track} - %{title}",
        base_dir=str(base_dir), untitled_path_from_slug=False, no_slugify=False,
        truncate_album=0, truncate_track=0, ascii_only=False, ok_chars="-_~",
        space_char="-", keep_spaces=False, case_mode="lower", overwrite=False,
        debug=True, embed_art=False, embed_genres=False, embed_lyrics=False, group=False,
        no_confirm=True, retag=False, progress="auto")
    return BandcampDownloader(config, ALBUM["url"])


class DeadStream:
    """A body that stops part way through, the way a real connection drops"""

    ok = True
    headers = {"content-length": str(len(MP3_BYTES) * 4)}

    def iter_content(self, chunk_size):
        yield MP3_BYTES[:100]
        raise requests.exceptions.ChunkedEncodingError("connection dropped")


class ShortStream:
    """A server that promises more bytes than it sends and never says anything went wrong.
    urllib3 usually raises for this instead; the size check is what catches the quiet kind."""

    ok = True
    headers = {"content-length": str(len(MP3_BYTES) * 4)}

    def iter_content(self, chunk_size):
        yield MP3_BYTES[:100]


class StubbornSession:
    """Answers every request with the same broken body"""

    def __init__(self, response):
        self.response = response

    def get(self, url, headers=None, stream=None):
        return self.response


@responses.activate
def test_a_tmp_file_that_arrived_whole_is_only_tagged(tmp_path):
    album_dir = tmp_path / "loopy" / "first"
    album_dir.mkdir(parents=True)
    (album_dir / "01 - one.mp3.tmp").write_bytes(MP3_BYTES)
    responses.add(responses.GET, TRACK_URL, body=b"the body is never read",
                  headers={"Content-Length": str(len(MP3_BYTES))})

    assert make_downloader(tmp_path).download_album(ALBUM) is True

    finished = album_dir / "01 - one.mp3"
    assert not (album_dir / "01 - one.mp3.tmp").exists()
    assert str(ID3(finished)["TALB"]) == "First"
    assert len(responses.calls) == 1


def test_a_body_shorter_than_promised_is_retried_then_given_up_on(tmp_path, capsys):
    # A stalled CDN that answers with fewer bytes than the length it promised, without
    # saying so: the size check is what turns that into a retry instead of a truncated file
    downloader = make_downloader(tmp_path)
    downloader.session = StubbornSession(ShortStream())

    assert downloader.download_album(ALBUM) is False

    output = capsys.readouterr().out
    assert output.count("is incomplete, retrying..") == 3
    # Giving up also means deleting the .tmp: a truncated file must never be mistaken
    # for a finished track
    assert list((tmp_path / "loopy" / "first").iterdir()) == []


def test_a_connection_that_drops_mid_file_leaves_nothing_behind(tmp_path, capsys):
    downloader = make_downloader(tmp_path)
    downloader.session = StubbornSession(DeadStream())

    assert downloader.download_album(ALBUM) is False

    output = capsys.readouterr().out
    assert "failed, moving on to the next track.." in output
    assert list((tmp_path / "loopy" / "first").iterdir()) == []


@responses.activate
def test_a_track_that_only_fails_while_tagging_keeps_its_audio(tmp_path, monkeypatch, capsys):
    def cannot_tag(self, filepath, meta):
        raise ValueError("not an mp3")

    monkeypatch.setattr(BandcampDownloader, "write_id3_tags", cannot_tag)
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})

    assert make_downloader(tmp_path).download_album(ALBUM) is False

    album_dir = tmp_path / "loopy" / "first"
    # The download is complete, so the next run re-tags it instead of fetching it again
    assert (album_dir / "01 - one.mp3.tmp").read_bytes() == MP3_BYTES
    assert "Tagging 01 - one.mp3 failed" in capsys.readouterr().out


@responses.activate
def test_a_completed_run_clears_the_unfinished_marker(tmp_path):
    marker = tmp_path / f"{__version__}.not.finished"
    marker.write_text("album was interrupted\n")
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})

    make_downloader(tmp_path).download_album(ALBUM)

    assert not marker.exists()


class RecordingStream:
    """A body that reports the chunk size it was asked to be read in"""

    ok = True
    headers = {"content-length": str(len(MP3_BYTES))}

    def __init__(self):
        self.chunk_sizes = []

    def iter_content(self, chunk_size):
        self.chunk_sizes.append(chunk_size)
        yield MP3_BYTES


def test_a_download_is_read_in_one_fixed_chunk_size(tmp_path):
    # One hundredth of the file used to be the chunk size, so a large track arrived in
    # megabyte reads and a small one in tiny ones, each with its own progress redraw
    downloader = make_downloader(tmp_path)
    stream = RecordingStream()
    downloader.session = StubbornSession(stream)

    assert downloader.download_album(ALBUM) is True

    assert stream.chunk_sizes == [DOWNLOAD_CHUNK_SIZE]


def test_a_tmp_file_the_os_will_not_rename_back_is_reported(tmp_path, monkeypatch, caplog):
    def refuse(src, dst):
        raise OSError("the mount went read only")

    monkeypatch.setattr(os, "rename", refuse)
    album_dir = tmp_path / "loopy" / "first"
    album_dir.mkdir(parents=True)
    stale_tmp = album_dir / "01 - one.mp3.tmp"
    stale_tmp.write_bytes(MP3_BYTES)

    make_downloader(tmp_path).rename_tmp_back(str(stale_tmp))

    assert "Could not restore" in caplog.text
    assert stale_tmp.exists()
