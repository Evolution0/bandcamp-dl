from types import SimpleNamespace

import responses
from mutagen.id3 import ID3

from bandcamp_dl.bandcampdownloader import BandcampDownloader

TRACK_URL = "https://t4.bcbits.com/stream/abc/mp3-128/1"
SECOND_TRACK_URL = "https://t4.bcbits.com/stream/def/mp3-128/2"
ART_URL = "https://f4.bcbits.com/img/a1234567890_16.jpg"
# 20 silent MPEG-1 Layer III frames (128 kbps, 44.1 kHz, 417 bytes each)
MP3_BYTES = (b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20
COVER_BYTES = b"\xff\xd8\xff\xe0" + b"cover" * 40


def make_album(tracks):
    return {"tracks": tracks, "title": "First", "artist": "Loopy", "label": None,
            "full": True, "art": "", "date": "2026",
            "url": "https://loopy.bandcamp.com/album/first", "genres": "", "album_id": 7}


def make_downloader(base_dir):
    config = SimpleNamespace(
        limit_req_per_minute=0, template="%{artist}/%{album}/%{track} - %{title}",
        base_dir=str(base_dir), untitled_path_from_slug=False, no_slugify=False,
        truncate_album=0, truncate_track=0, ascii_only=False, ok_chars="-_~",
        space_char="-", keep_spaces=False, case_mode="lower", overwrite=False,
        debug=True, embed_art=True, embed_genres=False, embed_lyrics=False, group=False,
        no_confirm=True, retag=False, progress="auto")
    return BandcampDownloader(config, "https://loopy.bandcamp.com/album/first")


@responses.activate
def test_the_cover_is_read_once_and_reused_for_every_track(tmp_path):
    responses.add(responses.GET, ART_URL, body=COVER_BYTES)
    for url in (TRACK_URL, SECOND_TRACK_URL):
        responses.add(responses.GET, url, body=MP3_BYTES,
                      headers={"Content-Length": str(len(MP3_BYTES))})
    album = make_album([
        {"duration": 1.0, "track": "1", "title": "One", "artist": "Loopy",
         "track_id": 1, "url": TRACK_URL},
        {"duration": 1.0, "track": "2", "title": "Two", "artist": "Loopy",
         "track_id": 2, "url": SECOND_TRACK_URL}])

    downloader = make_downloader(tmp_path)
    assert downloader.download_album({**album, "art": ART_URL}) is True

    for name in ("01 - one.mp3", "02 - two.mp3"):
        tags = ID3(tmp_path / "loopy" / "first" / name)
        assert tags.getall("APIC")[0].data == COVER_BYTES
    # The image sat in memory from the first track, so the second never opened the file
    assert downloader.cover_bytes == COVER_BYTES
    assert len([call for call in responses.calls if call.request.url == ART_URL]) == 1


def test_embed_art_with_no_tracks_and_no_cover_does_not_crash(tmp_path):
    assert make_downloader(tmp_path).download_album(make_album([])) is True


@responses.activate
def test_embed_art_with_no_cover_tags_track_without_art(tmp_path):
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})
    album = make_album([{"duration": 1.0, "track": "1", "title": "One", "artist": "Loopy",
                         "track_id": 1, "url": TRACK_URL}])

    assert make_downloader(tmp_path).download_album(album) is True

    tags = ID3(tmp_path / "loopy" / "first" / "01 - one.mp3")
    assert not tags.getall("APIC")
