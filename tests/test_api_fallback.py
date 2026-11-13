import re

import responses

from bandcamp_dl.bandcamp import MOBILE_API, SEARCH_API, Bandcamp

ALBUM_URL = "https://loopy.example/album/first"

SEARCH = {"auto": {"results": [
    {"type": "a", "id": 9, "item_url_root": "https://loopy.example"},
    {"type": "b", "id": 42, "item_url_root": "https://loopy.example"},
]}}
BAND = {"discography": [{"item_id": 7, "item_type": "album", "band_id": 42, "title": "First"}]}
TRALBUM = {
    "id": 7, "title": "First", "tralbum_artist": "Loopy", "label": None,
    "art_id": 123, "release_date": 1793232000, "bandcamp_url": ALBUM_URL,
    "tags": [{"name": "ambient"}, {"name": "drone"}],
    "tracks": [
        {"track_id": 1, "track_num": 1, "title": "One", "duration": 60.5, "band_name": "Loopy",
         "streaming_url": {"mp3-128": "https://bandcamp.com/stream_redirect?track_id=1"}},
        {"track_id": 2, "track_num": 2, "title": "Two", "duration": 30.0, "band_name": "Loopy",
         "streaming_url": None},
    ],
}


def add_redirect_loop(host):
    """name.bandcamp.com and its custom domain redirect to each other forever"""
    responses.add(responses.GET, re.compile(rf"https://{host}\.bandcamp\.com/.*"), status=301,
                  headers={"Location": "https://loopy.example/music"})
    responses.add(responses.GET, re.compile(r"https://loopy\.example/.*"), status=303,
                  headers={"Location": f"https://{host}.bandcamp.com/music"})


def add_api():
    responses.add(responses.POST, SEARCH_API, json=SEARCH)
    responses.add(responses.POST, f"{MOBILE_API}/band_details", json=BAND)
    responses.add(responses.GET, f"{MOBILE_API}/tralbum_details", json=TRALBUM)


@responses.activate
def test_discography_falls_back_to_mobile_api_on_redirect_loop():
    add_redirect_loop("loopy")
    add_api()

    urls = Bandcamp().get_full_discography("loopy", "music")

    assert urls == [ALBUM_URL]


@responses.activate
def test_parse_uses_cached_api_data_without_fetching_page():
    add_redirect_loop("loopy")
    add_api()
    bandcamp = Bandcamp()
    bandcamp.get_full_discography("loopy", "music")
    calls_before = len(responses.calls)

    album = bandcamp.parse(ALBUM_URL, art=True, genres=True, cover_quality=10)

    assert len(responses.calls) == calls_before
    assert album == {
        "tracks": [{"duration": 60.5, "track": "1", "title": "One", "artist": "Loopy",
                    "track_id": 1, "url": "https://bandcamp.com/stream_redirect?track_id=1"}],
        "title": "First", "artist": "Loopy", "label": None, "full": False,
        "art": "https://f4.bcbits.com/img/a123_10.jpg", "date": "2026",
        "url": ALBUM_URL, "genres": "ambient; drone", "album_id": 7,
    }


@responses.activate
def test_parse_direct_url_falls_back_to_mobile_api_on_redirect_loop():
    add_redirect_loop("loopy")
    add_api()

    album = Bandcamp().parse("https://loopy.bandcamp.com/album/first", art=False)

    assert album["title"] == "First"
    assert album["art"] == ""
    assert album["url"] == "https://loopy.bandcamp.com/album/first"


@responses.activate
def test_api_request_retries_after_rate_limit():
    responses.add(responses.GET, f"{MOBILE_API}/tralbum_details", status=429,
                  headers={"Retry-After": "0"})
    responses.add(responses.GET, f"{MOBILE_API}/tralbum_details", json=TRALBUM)

    result = Bandcamp().api_request("GET", f"{MOBILE_API}/tralbum_details")

    assert result["id"] == 7
    assert len(responses.calls) == 2


@responses.activate
def test_discography_returns_empty_when_band_not_found():
    add_redirect_loop("loopy")
    responses.add(responses.POST, SEARCH_API, json={"auto": {"results": []}})

    assert Bandcamp().get_full_discography("loopy", "music") == []
