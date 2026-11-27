from types import SimpleNamespace

import responses
from mutagen.id3 import ID3

from bandcamp_dl.bandcampdownloader import BandcampDownloader

TRACK_URL = "https://t4.bcbits.com/stream/abc/mp3-128/1"
# 20 silent MPEG-1 Layer III frames (128 kbps, 44.1 kHz, 417 bytes each)
MP3_BYTES = (b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20

ALBUM = {
    "tracks": [{"duration": 1.0, "track": "1", "title": "One", "artist": "Loopy",
                "track_id": 1, "url": TRACK_URL}],
    "title": "First", "artist": "Loopy", "label": None, "full": True, "art": "",
    "date": "2026", "url": "https://loopy.bandcamp.com/album/first", "genres": "",
    "album_id": 7,
}


def make_downloader(base_dir, group=False):
    config = SimpleNamespace(
        limit_req_per_minute=0, template="%{artist}/%{album}/%{track} - %{title}",
        base_dir=str(base_dir), untitled_path_from_slug=False, no_slugify=False,
        truncate_album=0, truncate_track=0, ascii_only=False, ok_chars="-_~",
        space_char="-", keep_spaces=False, case_mode="lower", overwrite=False,
        debug=True, embed_art=False, embed_genres=False, embed_lyrics=False, group=group,
        no_confirm=True, retag=False, progress="auto")
    return BandcampDownloader(config, ALBUM["url"])


@responses.activate
def test_error_response_is_not_saved_as_audio(tmp_path):
    responses.add(responses.GET, TRACK_URL, status=429, body=b"rate limited")

    make_downloader(tmp_path).download_album(ALBUM)

    album_dir = tmp_path / "loopy" / "first"
    assert list(album_dir.iterdir()) == []
    assert len(responses.calls) == 3


@responses.activate
def test_a_rate_limited_download_says_to_limit_the_requests_once(tmp_path, capsys):
    responses.add(responses.GET, TRACK_URL, status=429, body=b"rate limited")

    make_downloader(tmp_path).download_album(ALBUM)

    out = capsys.readouterr().out
    assert "failed with HTTP 429, retrying" in out
    assert out.count("--limit-req-per-minute") == 1


@responses.activate
def test_leftover_empty_tmp_file_is_redownloaded(tmp_path):
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})
    album_dir = tmp_path / "loopy" / "first"
    album_dir.mkdir(parents=True)
    (album_dir / "01 - one.mp3.tmp").write_bytes(b"")

    make_downloader(tmp_path).download_album(ALBUM)

    assert (album_dir / "01 - one.mp3").stat().st_size > len(MP3_BYTES)
    assert not (album_dir / "01 - one.mp3.tmp").exists()


@responses.activate
def test_download_without_content_length_is_saved(tmp_path):
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES)

    make_downloader(tmp_path).download_album(ALBUM)

    assert (tmp_path / "loopy" / "first" / "01 - one.mp3").stat().st_size > len(MP3_BYTES)


@responses.activate
def test_grouping_with_an_album_that_has_no_label_still_tags(tmp_path):
    # label is None for most releases and mutagen raises on None text, which used to
    # abort the album halfway through and leave a .tmp behind
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})

    assert make_downloader(tmp_path, group=True).download_album(ALBUM) is True

    tags = ID3(tmp_path / "loopy" / "first" / "01 - one.mp3")
    assert not tags.getall("TIT1")
    assert str(tags["TALB"]) == "First"


@responses.activate
def test_one_failing_track_does_not_stop_the_rest_of_the_album(tmp_path):
    responses.add(responses.GET, "https://t4.bcbits.com/stream/bad/mp3-128/1", status=500)
    responses.add(responses.GET, "https://t4.bcbits.com/stream/good/mp3-128/2",
                  body=MP3_BYTES, headers={"Content-Length": str(len(MP3_BYTES))})
    album = {**ALBUM, "tracks": [
        {"duration": 1.0, "track": "1", "title": "Bad", "artist": "Loopy",
         "track_id": 1, "url": "https://t4.bcbits.com/stream/bad/mp3-128/1"},
        {"duration": 1.0, "track": "2", "title": "Good", "artist": "Loopy",
         "track_id": 2, "url": "https://t4.bcbits.com/stream/good/mp3-128/2"}]}

    assert make_downloader(tmp_path).download_album(album) is False

    album_dir = tmp_path / "loopy" / "first"
    assert [f.name for f in album_dir.iterdir()] == ["02 - good.mp3"]


@responses.activate
def test_a_track_without_a_download_url_does_not_abort_the_album(tmp_path):
    responses.add(responses.GET, "https://t4.bcbits.com/stream/good/mp3-128/2",
                  body=MP3_BYTES, headers={"Content-Length": str(len(MP3_BYTES))})
    album = {**ALBUM, "tracks": [
        {"duration": 1.0, "track": "1", "title": "NoScheme", "artist": "Loopy",
         "track_id": 1, "url": "t4.bcbits.com/stream/noscheme/mp3-128/1"},
        {"duration": 1.0, "track": "2", "title": "Good", "artist": "Loopy",
         "track_id": 2, "url": "https://t4.bcbits.com/stream/good/mp3-128/2"}]}

    assert make_downloader(tmp_path).download_album(album) is False

    album_dir = tmp_path / "loopy" / "first"
    assert [f.name for f in album_dir.iterdir()] == ["02 - good.mp3"]
