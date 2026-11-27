import re

import pytest
import responses

from bandcamp_dl import bandcamp as bandcamp_module
from bandcamp_dl.bandcamp import API_RETRIES, MOBILE_API, SEARCH_API, Bandcamp

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


def add_loop(bandcamp_host, custom_host):
    """A band's bandcamp.com subdomain and its custom domain redirect to each other forever"""
    responses.add(responses.GET, re.compile(rf"https://{bandcamp_host}\.bandcamp\.com/.*"),
                  status=301, headers={"Location": f"https://{custom_host}/music"})
    responses.add(responses.GET, re.compile(rf"https://{re.escape(custom_host)}/.*"),
                  status=303, headers={"Location": f"https://{bandcamp_host}.bandcamp.com/music"})


def add_redirect_loop(host):
    """name.bandcamp.com and its custom domain redirect to each other forever"""
    add_loop(host, "loopy.example")


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
def test_a_rate_limited_api_advises_limiting_the_requests_once(caplog):
    responses.add(responses.GET, f"{MOBILE_API}/tralbum_details", status=429,
                  headers={"Retry-After": "0"})
    responses.add(responses.GET, f"{MOBILE_API}/tralbum_details", status=429,
                  headers={"Retry-After": "0"})
    responses.add(responses.GET, f"{MOBILE_API}/tralbum_details", json=TRALBUM)

    assert Bandcamp().api_request("GET", f"{MOBILE_API}/tralbum_details")["id"] == 7
    # The retries are debug chatter, so without --debug this is the only 429 the user sees
    assert caplog.text.count("--limit-req-per-minute") == 1


@responses.activate
def test_a_rate_limited_band_lookup_warns_instead_of_only_denying_the_band(caplog):
    responses.add(responses.GET, re.compile(r"https://loopy\.bandcamp\.com/.*"), status=429)
    responses.add(responses.POST, SEARCH_API, json={"auto": {"results": []}})

    assert Bandcamp().find_band_id("loopy") is None
    assert "--limit-req-per-minute" in caplog.text


@responses.activate
def test_band_on_lookalike_domain_is_not_matched():
    add_redirect_loop("loopy")
    responses.add(responses.POST, SEARCH_API, json={"auto": {"results": [
        {"type": "b", "id": 666, "item_url_root": "https://loopy.evil.example"},
    ]}})

    assert Bandcamp().find_band_id("loopy") is None


@responses.activate
def test_discography_returns_empty_when_band_not_found():
    add_redirect_loop("loopy")
    responses.add(responses.POST, SEARCH_API, json={"auto": {"results": []}})

    assert Bandcamp().get_full_discography("loopy", "music") == []


@responses.activate
def test_api_request_gives_up_instead_of_sleeping_after_the_last_retry(monkeypatch):
    import requests

    slept = []
    monkeypatch.setattr(bandcamp_module.time, "sleep", lambda seconds: slept.append(seconds))
    responses.add(responses.GET, f"{MOBILE_API}/tralbum_details", status=429)

    with pytest.raises(requests.exceptions.HTTPError):
        Bandcamp().api_request("GET", f"{MOBILE_API}/tralbum_details")

    assert len(slept) == API_RETRIES - 1


@responses.activate
def test_band_details_failure_is_reported_as_no_discography(caplog):
    add_redirect_loop("loopy")
    responses.add(responses.POST, SEARCH_API, json=SEARCH)
    responses.add(responses.POST, f"{MOBILE_API}/band_details", status=500)

    assert Bandcamp().get_full_discography("loopy", "music") == []
    assert "Could not fetch discography for loopy from the mobile API" in caplog.text


@responses.activate
def test_one_failing_release_does_not_drop_the_others(caplog):
    band = {"discography": [{"item_id": 8, "item_type": "album", "band_id": 42, "title": "Broken"},
                            {"item_id": 7, "item_type": "album", "band_id": 42, "title": "First"}]}
    add_redirect_loop("loopy")
    responses.add(responses.POST, SEARCH_API, json=SEARCH)
    responses.add(responses.POST, f"{MOBILE_API}/band_details", json=band)
    responses.add(responses.GET, f"{MOBILE_API}/tralbum_details?band_id=42&tralbum_type=a"
                                f"&tralbum_id=8", status=500)
    responses.add(responses.GET, f"{MOBILE_API}/tralbum_details", json=TRALBUM)

    assert Bandcamp().get_full_discography("loopy", "music") == [ALBUM_URL]
    assert "Skipping Broken, mobile API request failed" in caplog.text


@responses.activate
def test_a_release_the_api_does_not_list_is_reported_as_missing(capsys):
    add_redirect_loop("loopy")
    responses.add(responses.POST, SEARCH_API, json=SEARCH)
    responses.add(responses.POST, f"{MOBILE_API}/band_details", json={"discography": []})

    with pytest.raises(SystemExit) as exit_info:
        Bandcamp().parse("https://loopy.bandcamp.com/album/first")

    assert exit_info.value.code == 2
    assert (f"The Album/Track requested does not exist at: "
            f"https://loopy.bandcamp.com/album/first") in capsys.readouterr().out


@responses.activate
def test_the_api_fallback_says_lyrics_are_unavailable(caplog):
    add_redirect_loop("loopy")
    add_api()

    album = Bandcamp().parse("https://loopy.bandcamp.com/album/first", lyrics=True)

    assert "lyrics" not in album["tracks"][0]
    assert "Track lyrics are not available" in caplog.text


# A playlist hands out the band's own domain, not its bandcamp.com subdomain: the first
# label of music.custom.example is "music", while the band lives on businesscasual87.

CUSTOM_TRACK_URL = "https://music.custom.example/track/twenty-mako"
CUSTOM_SEARCH = {"auto": {"results": [
    {"type": "a", "id": 9, "item_url_root": "https://elsewhere.example"},
    {"type": "b", "id": 42, "item_url_root": "https://music.custom.example"},
]}}


@responses.activate
def test_a_track_url_on_a_custom_domain_resolves_to_its_band():
    add_loop("businesscasual87", "music.custom.example")
    responses.add(responses.POST, SEARCH_API, json=CUSTOM_SEARCH)
    responses.add(responses.POST, f"{MOBILE_API}/band_details",
                  json={"discography": [{"item_id": 7, "item_type": "track", "band_id": 42}]})
    responses.add(responses.GET, f"{MOBILE_API}/tralbum_details",
                  json={**TRALBUM, "bandcamp_url": CUSTOM_TRACK_URL})

    album = Bandcamp().parse(CUSTOM_TRACK_URL, art=False)

    assert album["title"] == "First"
    assert album["url"] == CUSTOM_TRACK_URL
    # Nothing may be looked up as the band "music"
    assert all("music.bandcamp.com" not in call.request.url for call in responses.calls)


@responses.activate
def test_resolve_band_name_reads_the_chain_not_the_first_label():
    add_loop("businesscasual87", "music.custom.example")

    assert Bandcamp().resolve_band_name(CUSTOM_TRACK_URL) == "businesscasual87"
    # A bandcamp.com url is already named, so the chain costs no requests
    assert Bandcamp().resolve_band_name("https://loopy.bandcamp.com/album/first") == "loopy"
    assert len(responses.calls) == 1


@responses.activate
def test_resolve_band_name_gives_up_on_a_chain_without_bandcamp(caplog):
    responses.add(responses.GET, re.compile(r"https://music\.custom\.example/.*"), status=301,
                  headers={"Location": "https://elsewhere.example/x"})
    responses.add(responses.GET, re.compile(r"https://elsewhere\.example/.*"), status=301,
                  headers={"Location": "https://music.custom.example/x"})

    with pytest.raises(SystemExit) as exit_info:
        Bandcamp().parse(CUSTOM_TRACK_URL)

    assert exit_info.value.code == 2
    assert ("Could not follow https://music.custom.example/track/twenty-mako to a bandcamp.com "
            "page, looking up the band as: music") in caplog.text
