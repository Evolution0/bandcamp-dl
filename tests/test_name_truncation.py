from types import SimpleNamespace

import responses
from mutagen.id3 import ID3

from bandcamp_dl.bandcampdownloader import BandcampDownloader

TRACK_URL = "https://t4.bcbits.com/stream/abc/mp3-128/1"
# 20 silent MPEG-1 Layer III frames (128 kbps, 44.1 kHz, 417 bytes each)
MP3_BYTES = (b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20

ALBUM = {"tracks": [{"duration": 1.0, "track": "1", "title": "A Track With A Very Long Name",
                    "artist": "Loopy", "track_id": 1, "url": TRACK_URL}],
         "title": "An Album With A Very Long Title", "artist": "Loopy", "label": None,
         "full": True, "art": "", "date": "2026",
         "url": "https://loopy.bandcamp.com/album/first", "genres": "", "album_id": 7}


def make_downloader(base_dir, truncate_album=0, truncate_track=0):
    config = SimpleNamespace(
        limit_req_per_minute=0, template="%{artist}/%{album}/%{track} - %{title}",
        base_dir=str(base_dir), untitled_path_from_slug=False, no_slugify=False,
        truncate_album=truncate_album, truncate_track=truncate_track, ascii_only=False,
        ok_chars="-_~", space_char="-", keep_spaces=False, case_mode="lower", overwrite=False,
        debug=True, embed_art=False, embed_genres=False, embed_lyrics=False, group=False,
        no_confirm=True, retag=False, progress="auto")
    return BandcampDownloader(config, ALBUM["url"])


@responses.activate
def test_long_names_are_cut_to_the_configured_lengths(tmp_path):
    # Some Bandcamp titles are long enough to blow past filename limits on Windows; the
    # tags keep the full title, only the path is shortened
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})

    downloader = make_downloader(tmp_path, truncate_album=8, truncate_track=5)

    assert downloader.download_album(ALBUM) is True

    tags = ID3(tmp_path / "loopy" / "an-album" / "01 - a-tra.mp3")
    assert str(tags["TALB"]) == ALBUM["title"]
    assert str(tags["TIT2"]) == ALBUM["tracks"][0]["title"]


@responses.activate
def test_a_name_shorter_than_the_limit_is_left_whole(tmp_path):
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})

    make_downloader(tmp_path, truncate_album=999, truncate_track=999).download_album(ALBUM)

    assert (tmp_path / "loopy" / "an-album-with-a-very-long-title" /
            "01 - a-track-with-a-very-long-name.mp3").exists()
