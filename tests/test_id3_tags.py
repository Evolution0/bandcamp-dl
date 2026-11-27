import os
from types import SimpleNamespace

import responses
from mutagen.id3 import ID3

from bandcamp_dl.bandcampdownloader import BandcampDownloader

TRACK_URL = "https://t4.bcbits.com/stream/abc/mp3-128/1"
# 20 silent MPEG-1 Layer III frames (128 kbps, 44.1 kHz, 417 bytes each)
MP3_BYTES = (b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20

BASE_TRACK = {"duration": 1.0, "track": "1", "title": "One", "artist": "Loopy",
              "track_id": 1, "url": TRACK_URL}


def track(**overrides):
    return {**BASE_TRACK, **overrides}


def make_album(**overrides):
    album = {"tracks": [dict(BASE_TRACK)], "title": "First", "artist": "Loopy",
             "label": "Loopy Store", "full": True, "art": "", "date": "2026",
             "url": "https://loopy.bandcamp.com/album/first", "genres": "ambient; drone",
             "album_id": 7}
    if "tracks" in overrides:
        album["tracks"] = overrides.pop("tracks")
    return {**album, **overrides}


def download_tags(tmp_path, album, filename="01 - one.mp3", **config_overrides):
    """Run one download and read the tags back off the finished file"""
    values = dict(
        limit_req_per_minute=0, template="%{artist}/%{album}/%{track} - %{title}",
        base_dir=str(tmp_path), untitled_path_from_slug=False, no_slugify=False,
        truncate_album=0, truncate_track=0, ascii_only=False, ok_chars="-_~",
        space_char="-", keep_spaces=False, case_mode="lower", no_confirm=True,
        retag=False, progress="auto", debug=True, overwrite=False,
        embed_art=False, embed_genres=False, embed_lyrics=False, group=False)
    config = SimpleNamespace(**{**values, **config_overrides})
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})

    assert BandcampDownloader(config, album["url"]).download_album(album) is True

    return ID3(tmp_path / "loopy" / "first" / filename)


@responses.activate
def test_grouping_uses_the_seller_as_the_itunes_grouping(tmp_path):
    tags = download_tags(tmp_path, make_album(), group=True)

    assert str(tags["TIT1"]) == "Loopy Store"


@responses.activate
def test_without_grouping_the_label_stays_out_of_the_tags(tmp_path):
    assert "TIT1" not in download_tags(tmp_path, make_album())


@responses.activate
def test_lyrics_are_embedded_as_an_unsynced_text_frame(tmp_path):
    album = make_album(tracks=[track(lyrics="first line")])

    tags = download_tags(tmp_path, album, embed_lyrics=True)

    assert tags.getall("USLT")[0].text == "first line"


@responses.activate
def test_a_numberless_single_is_tagged_as_track_one(tmp_path):
    tags = download_tags(tmp_path, make_album(tracks=[track(track="None")]),
                         filename="single - one.mp3")

    assert str(tags["TRCK"]) == "1"


@responses.activate
def test_a_track_that_names_its_performer_keeps_it(tmp_path):
    tags = download_tags(tmp_path, make_album(tracks=[track(artist="Singer")]))

    assert str(tags["TPE1"]) == "Singer"
    assert str(tags["TPE2"]) == "Loopy"


@responses.activate
def test_a_track_without_an_artist_is_tagged_with_the_album_artist(tmp_path):
    # Private pressings ship tracks with no artist; mutagen refuses None, which used to
    # abort the album part way through
    tags = download_tags(tmp_path, make_album(tracks=[track(artist=None)]))

    assert str(tags["TPE1"]) == "Loopy"


@responses.activate
def test_a_rename_the_os_refuses_still_replaces_the_finished_file(tmp_path, monkeypatch):
    # Windows refuses to rename onto an existing file, which is exactly what an
    # --overwrite run asks for
    album_dir = tmp_path / "loopy" / "first"
    album_dir.mkdir(parents=True)
    finished = album_dir / "01 - one.mp3"
    finished.write_bytes(MP3_BYTES)

    real_rename = os.rename
    refused = []

    def rename_once(src, dst):
        if not refused and dst.endswith(".mp3"):
            refused.append(dst)
            raise FileExistsError(dst)
        real_rename(src, dst)

    monkeypatch.setattr(os, "rename", rename_once)

    tags = download_tags(tmp_path, make_album(), overwrite=True)

    # The downloader joins the path with a forward slash, tmp_path does not
    assert [dst.replace("\\", "/") for dst in refused] == [str(finished).replace("\\", "/")]
    assert str(tags["TALB"]) == "First"
