from types import SimpleNamespace

import responses
from mutagen.id3 import ID3, TIT2

from bandcamp_dl.bandcampdownloader import BandcampDownloader

# 20 silent MPEG-1 Layer III frames (128 kbps, 44.1 kHz, 417 bytes each)
MP3_BYTES = (b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20

ALBUM = {
    "tracks": [{"duration": 1.0, "track": "1", "title": "One", "artist": "Loopy",
                "track_id": 1, "url": "https://t4.bcbits.com/stream/abc/mp3-128/1"}],
    "title": "First", "artist": "Loopy", "label": None, "full": True, "art": "",
    "date": "2026", "url": "https://loopy.bandcamp.com/album/first",
    "genres": "ambient; drone", "album_id": 7,
}


def make_downloader(base_dir, retag):
    config = SimpleNamespace(
        limit_req_per_minute=0, template="%{artist}/%{album}/%{track} - %{title}",
        base_dir=str(base_dir), untitled_path_from_slug=False, no_slugify=False,
        truncate_album=0, truncate_track=0, ascii_only=False, ok_chars="-_~",
        space_char="-", keep_spaces=False, case_mode="lower", overwrite=False,
        debug=True, embed_art=False, embed_genres=True, embed_lyrics=False, group=False,
        no_confirm=True, retag=retag, progress="auto")
    return BandcampDownloader(config, ALBUM["url"])


def make_existing_track(base_dir):
    album_dir = base_dir / "loopy" / "first"
    album_dir.mkdir(parents=True)
    track = album_dir / "01 - one.mp3"
    track.write_bytes(MP3_BYTES)
    tags = ID3()
    tags.add(TIT2(encoding=3, text="One"))
    tags.save(track)
    return track


@responses.activate
def test_retag_updates_tags_of_existing_track_without_downloading(tmp_path):
    track = make_existing_track(tmp_path)

    make_downloader(tmp_path, retag=True).download_album(ALBUM)

    assert len(responses.calls) == 0
    assert str(ID3(track)["TCON"]) == "ambient; drone"
    assert not track.with_name(track.name + ".tmp").exists()


@responses.activate
def test_existing_track_is_left_alone_without_retag(tmp_path):
    responses.add(responses.GET, ALBUM["tracks"][0]["url"], body=MP3_BYTES)
    track = make_existing_track(tmp_path)

    make_downloader(tmp_path, retag=False).download_album(ALBUM)

    assert "TCON" not in ID3(track)


@responses.activate
def test_retag_replaces_a_stale_tmp_file(tmp_path):
    track = make_existing_track(tmp_path)
    stale = track.with_name(track.name + ".tmp")
    stale.write_bytes(b"half a download from a run that was interrupted")

    make_downloader(tmp_path, retag=True).download_album(ALBUM)

    assert not stale.exists()
    assert str(ID3(track)["TCON"]) == "ambient; drone"


@responses.activate
def test_a_failed_retag_restores_the_finished_file(tmp_path, monkeypatch):
    def cannot_tag(self, filepath, meta):
        raise ValueError("not an mp3")

    monkeypatch.setattr(BandcampDownloader, "write_id3_tags", cannot_tag)
    track = make_existing_track(tmp_path)
    before = track.read_bytes()

    assert make_downloader(tmp_path, retag=True).download_album(ALBUM) is False

    assert not track.with_name(track.name + ".tmp").exists()
    assert track.read_bytes() == before
