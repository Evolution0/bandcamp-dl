from types import SimpleNamespace

import responses

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


def make_downloader(base_dir):
    config = SimpleNamespace(
        limit_req_per_minute=0, template="%{artist}/%{album}/%{track} - %{title}",
        base_dir=str(base_dir), untitled_path_from_slug=False, no_slugify=False,
        truncate_album=0, truncate_track=0, ascii_only=False, ok_chars="-_~",
        space_char="-", keep_spaces=False, case_mode="lower", overwrite=False,
        debug=True, embed_art=False, embed_genres=False, embed_lyrics=False, group=False,
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
