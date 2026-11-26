from types import SimpleNamespace

import requests
import responses
from mutagen.id3 import ID3

from bandcamp_dl.bandcampdownloader import BandcampDownloader

TRACK_URL = "https://t4.bcbits.com/stream/abc/mp3-128/1"
ART_URL = "https://f4.bcbits.com/img/a1234567890_16.jpg"
# 20 silent MPEG-1 Layer III frames (128 kbps, 44.1 kHz, 417 bytes each)
MP3_BYTES = (b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20
COVER_BYTES = b"\xff\xd8\xff\xe0" + b"cover" * 40


def make_album(art):
    return {"tracks": [{"duration": 1.0, "track": "1", "title": "One", "artist": "Loopy",
                        "track_id": 1, "url": TRACK_URL}],
            "title": "First", "artist": "Loopy", "label": None, "full": True, "art": art,
            "date": "2026", "url": "https://loopy.bandcamp.com/album/first", "genres": "",
            "album_id": 7}


def make_downloader(base_dir, embed_art):
    config = SimpleNamespace(
        limit_req_per_minute=0, template="%{artist}/%{album}/%{track} - %{title}",
        base_dir=str(base_dir), untitled_path_from_slug=False, no_slugify=False,
        truncate_album=0, truncate_track=0, ascii_only=False, ok_chars="-_~",
        space_char="-", keep_spaces=False, case_mode="lower", overwrite=False,
        debug=True, embed_art=embed_art, embed_genres=False, embed_lyrics=False, group=False,
        no_confirm=True, retag=False, progress="auto")
    return BandcampDownloader(config, "https://loopy.bandcamp.com/album/first")


def add_track():
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})


@responses.activate
def test_the_cover_is_saved_once_next_to_the_tracks(tmp_path):
    add_track()
    responses.add(responses.GET, ART_URL, body=COVER_BYTES)

    downloader = make_downloader(tmp_path, embed_art=False)
    assert downloader.download_album(make_album(ART_URL)) is True

    cover = tmp_path / "loopy" / "first" / "cover.jpg"
    assert cover.read_bytes() == COVER_BYTES
    # The downloader joins the cover on with a forward slash, so compare the paths flat
    assert downloader.album_art.replace("\\", "/") == str(cover).replace("\\", "/")


@responses.activate
def test_an_existing_cover_is_reused_without_a_second_request(tmp_path):
    add_track()
    cover = tmp_path / "loopy" / "first" / "cover.jpg"
    cover.parent.mkdir(parents=True)
    cover.write_bytes(COVER_BYTES)

    downloader = make_downloader(tmp_path, embed_art=False)
    assert downloader.download_album(make_album(ART_URL)) is True

    assert len(responses.calls) == 1
    assert cover.read_bytes() == COVER_BYTES


@responses.activate
def test_embedding_a_downloaded_cover_removes_the_file(tmp_path):
    add_track()
    responses.add(responses.GET, ART_URL, body=COVER_BYTES)

    assert make_downloader(tmp_path, embed_art=True).download_album(make_album(ART_URL)) is True

    tags = ID3(tmp_path / "loopy" / "first" / "01 - one.mp3")
    assert tags.getall("APIC")[0].data == COVER_BYTES
    assert not (tmp_path / "loopy" / "first" / "cover.jpg").exists()


@responses.activate
def test_a_dead_cdn_only_costs_the_cover(tmp_path, capsys):
    add_track()
    responses.add(responses.GET, ART_URL, body=requests.exceptions.ConnectionError("cdn down"))

    assert make_downloader(tmp_path, embed_art=True).download_album(make_album(ART_URL)) is True

    output = capsys.readouterr().out
    assert "Couldn't download album art." in output
    assert "cdn down" in output
    tags = ID3(tmp_path / "loopy" / "first" / "01 - one.mp3")
    assert not tags.getall("APIC")
