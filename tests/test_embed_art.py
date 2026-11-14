from types import SimpleNamespace

import responses
from mutagen.id3 import ID3

from bandcamp_dl.bandcampdownloader import BandcampDownloader

TRACK_URL = "https://t4.bcbits.com/stream/abc/mp3-128/1"
# 20 silent MPEG-1 Layer III frames (128 kbps, 44.1 kHz, 417 bytes each)
MP3_BYTES = (b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20


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
        no_confirm=True, progress="auto")
    return BandcampDownloader(config, "https://loopy.bandcamp.com/album/first")


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
