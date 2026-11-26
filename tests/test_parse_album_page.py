import copy
import html
import json

import pytest
import responses

from bandcamp_dl.bandcamp import Bandcamp

ALBUM_URL = "https://loopy.bandcamp.com/album/first"
ART_URL = "https://f4.bcbits.com/img/a1234567890_10.jpg"


def item(url, track_id, position):
    """One entry of the schema.org music list the album page publishes"""
    entry = {"position": position, "item": {"@id": url}}
    if track_id is not None:
        entry["item"]["additionalProperty"] = [{"name": "track_id", "value": track_id}]
    return entry


SCHEMA = {
    "@type": "MusicAlbum",
    "@id": ALBUM_URL,
    "artist": "Loopy",
    "image": ART_URL,
    "albumRelease": [{"@type": "MusicRelease",
                      "additionalProperty": [{"name": "item_id", "value": 77}]}],
    "track": {"@type": "MusicList", "itemListElement": [
        item(f"{ALBUM_URL}?tk=one", 11, 1),
        item(f"{ALBUM_URL}?tk=two", 22, 2),
    ]},
}

TRALBUM = {
    "url": ALBUM_URL,
    "album_release_date": "20 Jan 2026 12:00:00 GMT",
    "current": {"title": "First", "selling_band_id": 5, "release_date": None},
    "item_sellers": {"5": {"name": "Loopy Store"}},
    "keywords": ["ambient", "field recording"],
    "trackinfo": [
        {"track_num": 1, "title": "One", "artist": "Loopy", "duration": 60.0,
         "title_link": "/album/first?tk=one", "has_lyrics": False, "lyrics": None,
         "file": {"mp3-128": "https://t4.bcbits.com/stream/one/mp3-128/1"}},
        {"track_num": 2, "title": "Two", "artist": "Loopy", "duration": 30.0,
         "title_link": "/album/first?tk=two", "has_lyrics": False, "lyrics": None,
         "file": {"mp3-128": "https://t4.bcbits.com/stream/two/mp3-128/2"}},
    ],
}


def album_html(schema=None, tralbum=None, body=""):
    """A page laid out like the ones Bandcamp serves: pagedata blob, ld+json, tralbum blob"""
    schema = copy.deepcopy(schema if schema is not None else SCHEMA)
    tralbum = copy.deepcopy(tralbum if tralbum is not None else TRALBUM)
    return ('<html><body>' +
            f'<div id="tralbumArt"><a href="{ART_URL}">cover</a></div>' + body +
            f'<div id="pagedata" data-blob="{html.escape(json.dumps({"app": "tralbum"}))}">'
            f'</div>'
            f'<script type="application/ld+json">{json.dumps(schema)}</script>'
            f'<script data-tralbum="{html.escape(json.dumps(tralbum))}"></script>'
            '</body></html>')


def parse_page(body, **kwargs):
    """Serve one album page and parse it the way the CLI does"""
    responses.add(responses.GET, ALBUM_URL, body=body)
    return Bandcamp().parse(ALBUM_URL, **kwargs)


@responses.activate
def test_an_album_page_becomes_a_complete_album():
    album = parse_page(album_html(), art=True, genres=True, cover_quality=16)

    assert album == {
        "tracks": [
            {"duration": 60.0, "track": "1", "title": "One", "artist": "Loopy",
             "track_id": 11, "url": "https://t4.bcbits.com/stream/one/mp3-128/1"},
            {"duration": 30.0, "track": "2", "title": "Two", "artist": "Loopy",
             "track_id": 22, "url": "https://t4.bcbits.com/stream/two/mp3-128/2"},
        ],
        "title": "First",
        "artist": "Loopy",
        "label": "Loopy Store",
        "full": True,
        "art": "https://f4.bcbits.com/img/a1234567890_16.jpg",
        "date": "2026",
        "url": ALBUM_URL,
        "genres": "ambient; field recording",
        "album_id": 77,
    }


@responses.activate
def test_an_item_without_an_id_is_skipped_with_a_warning(caplog):
    schema = copy.deepcopy(SCHEMA)
    schema["track"]["itemListElement"] = [item(None, 11, 1), item(f"{ALBUM_URL}?tk=two", 22, 2)]

    album = parse_page(album_html(schema=schema))

    assert "Track URL is missing, skipping..." in caplog.text
    assert [track["track_id"] for track in album["tracks"]] == [None, 22]


@responses.activate
def test_no_art_leaves_the_cover_empty_even_with_a_cover_on_the_page():
    assert parse_page(album_html(), art=False)["art"] == ""


@responses.activate
def test_a_missing_page_exits_with_the_bandcamp_message(capsys):
    responses.add(responses.GET, ALBUM_URL, status=404)

    with pytest.raises(SystemExit) as exit_info:
        Bandcamp().parse(ALBUM_URL)

    assert exit_info.value.code == 2
    assert f"The Album/Track requested does not exist at: {ALBUM_URL}" in capsys.readouterr().out


@responses.activate
def test_a_server_error_is_reported_as_http_status(capsys):
    responses.add(responses.GET, ALBUM_URL, status=503)

    with pytest.raises(SystemExit) as exit_info:
        Bandcamp().parse(ALBUM_URL)

    assert exit_info.value.code == 2
    assert f"Could not fetch {ALBUM_URL}: HTTP 503" in capsys.readouterr().out


@responses.activate
def test_duplicate_track_numbers_are_renumbered_from_the_page_order():
    schema = copy.deepcopy(SCHEMA)
    schema["track"]["itemListElement"] = [item(f"{ALBUM_URL}?tk=one", 11, 2),
                                          item(f"{ALBUM_URL}?tk=two", 22, 4)]
    tralbum = copy.deepcopy(TRALBUM)
    # A mis-entered album can list three tracks under number 1; the page order is the only
    # thing that can number them, and a track missing from the list falls back to its index
    tralbum["trackinfo"] = [
        {"track_num": 1, "title": "One", "artist": "Loopy", "duration": 60.0,
         "title_link": "/album/first?tk=one", "has_lyrics": False, "lyrics": None,
         "file": {"mp3-128": "https://t4.bcbits.com/stream/one"}},
        {"track_num": 1, "title": "Two", "artist": "Loopy", "duration": 30.0,
         "title_link": "/album/first?tk=two", "has_lyrics": False, "lyrics": None,
         "file": {"mp3-128": "https://t4.bcbits.com/stream/two"}},
        {"track_num": 1, "title": "Three", "artist": "Loopy", "duration": 30.0,
         "title_link": "/album/first?tk=four", "has_lyrics": False, "lyrics": None,
         "file": {"mp3-128": "https://t4.bcbits.com/stream/three"}},
    ]

    album = parse_page(album_html(schema=schema, tralbum=tralbum))

    assert [track["track"] for track in album["tracks"]] == ["2", "4", "3"]
    assert [track["track_id"] for track in album["tracks"]] == [11, 22, None]


@responses.activate
def test_a_private_track_is_kept_out_but_makes_the_album_incomplete():
    tralbum = copy.deepcopy(TRALBUM)
    tralbum["trackinfo"][1]["file"] = None

    album = parse_page(album_html(tralbum=tralbum))

    assert album["full"] is False
    assert [track["title"] for track in album["tracks"]] == ["One"]


@responses.activate
def test_lyrics_are_read_from_each_track_page():
    tralbum = copy.deepcopy(TRALBUM)
    for entry in tralbum["trackinfo"]:
        entry["has_lyrics"] = True
    responses.add(responses.GET, ALBUM_URL, body=album_html(tralbum=tralbum))
    responses.add(responses.GET, f"{ALBUM_URL}?tk=one#lyrics",
                  body='<html><body><div class="lyricsText">first line</div></body></html>')
    responses.add(responses.GET, f"{ALBUM_URL}?tk=two#lyrics",
                  body='<html><body><p>no lyrics here</p></body></html>')

    album = Bandcamp().parse(ALBUM_URL, lyrics=True)

    assert album["tracks"][0]["lyrics"] == "first line"
    assert album["tracks"][1]["lyrics"] == ""


@responses.activate
def test_a_release_date_only_the_embed_knows_is_still_used():
    tralbum = copy.deepcopy(TRALBUM)
    tralbum["album_release_date"] = None
    tralbum["current"]["release_date"] = None
    tralbum["embed_info"] = {"item_public": "03 Mar 2026 01:02:03 GMT"}

    assert parse_page(album_html(tralbum=tralbum))["date"] == "2026"


@responses.activate
def test_the_track_page_without_a_title_dates_from_its_release():
    tralbum = copy.deepcopy(TRALBUM)
    del tralbum["current"]["title"]
    tralbum["current"]["release_date"] = "03 Mar 2026 01:02:03 GMT"
    tralbum["album_release_date"] = None

    album = parse_page(album_html(tralbum=tralbum))

    assert album["title"] == "One"
    assert album["date"] == "2026"


@responses.activate
def test_an_album_without_a_seller_has_no_label():
    tralbum = copy.deepcopy(TRALBUM)
    tralbum["item_sellers"] = {}

    assert parse_page(album_html(tralbum=tralbum))["label"] is None


def test_a_url_without_a_scheme_parses_to_none():
    # Typos like bandcamp.com/album/x used to raise out of main()
    assert Bandcamp().parse("loopy.bandcamp.com/album/first") is None
