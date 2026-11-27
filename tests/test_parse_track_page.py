import copy
import html
import json

import responses

from bandcamp_dl.bandcamp import Bandcamp

TRACK_URL = "https://loopy.bandcamp.com/track/one"
ART_URL = "https://f4.bcbits.com/img/a1234567890_10.jpg"

SCHEMA = {
    "@type": "MusicRecording",
    "@id": TRACK_URL,
    "artist": "Loopy",
    "image": ART_URL,
    "additionalProperty": [{"name": "track_id", "value": 99}],
}

TRALBUM = {
    "url": TRACK_URL,
    "album_release_date": None,
    "current": {"title": "One", "release_date": "20 Jan 2026 12:00:00 GMT", "selling_band_id": 5},
    "item_sellers": {},
    "keywords": ["ambient", "drone"],
    "trackinfo": [{
        "track_num": None, "title": "One", "artist": "Loopy", "duration": 60.0,
        "title_link": "/track/one", "has_lyrics": False, "lyrics": None,
        "file": {"mp3-128": "https://t4.bcbits.com/stream/one/mp3-128/1"},
    }],
}


def track_html(schema=None, tralbum=None):
    """A single track page: no schema.org music list, the id lives on the recording"""
    schema = copy.deepcopy(schema if schema is not None else SCHEMA)
    tralbum = copy.deepcopy(tralbum if tralbum is not None else TRALBUM)
    return ('<html><body>'
            f'<div id="tralbumArt"><a href="{ART_URL}">cover</a></div>'
            f'<div id="pagedata" data-blob="{html.escape(json.dumps({"app": "tralbum"}))}"></div>'
            f'<script type="application/ld+json">{json.dumps(schema)}</script>'
            f'<script data-tralbum="{html.escape(json.dumps(tralbum))}"></script>'
            '</body></html>')


@responses.activate
def test_a_single_track_page_keeps_its_recording_id():
    responses.add(responses.GET, TRACK_URL, body=track_html())

    album = Bandcamp().parse(TRACK_URL, art=True, genres=True, cover_quality=10)

    assert album == {
        "tracks": [{
            "duration": 60.0, "track": "None", "title": "One", "artist": "Loopy",
            "track_id": 99,
            "url": "https://t4.bcbits.com/stream/one/mp3-128/1",
        }],
        "title": "One",
        "artist": "Loopy",
        "label": None,
        "full": True,
        "art": "https://f4.bcbits.com/img/a1234567890_10.jpg",
        "date": "2026",
        "url": TRACK_URL,
        "genres": "ambient; drone",
        "album_id": 99,
    }


@responses.activate
def test_a_track_page_without_the_extra_properties_has_no_id():
    schema = copy.deepcopy(SCHEMA)
    del schema["additionalProperty"]
    responses.add(responses.GET, TRACK_URL, body=track_html(schema=schema))

    album = Bandcamp().parse(TRACK_URL)

    assert album["album_id"] is None
    assert album["tracks"][0]["track_id"] is None


@responses.activate
def test_a_track_page_listing_the_whole_tracklist_renumbers_by_position():
    schema = copy.deepcopy(SCHEMA)
    schema["track"] = {"@type": "MusicList", "itemListElement": [
        {"position": 2, "item": {"@id": TRACK_URL}},
        {"position": 3, "item": {"@id": "https://loopy.bandcamp.com/track/two"}},
    ]}
    tralbum = copy.deepcopy(TRALBUM)
    tralbum["trackinfo"] = [
        {"track_num": 1, "title": "One", "artist": "Loopy", "duration": 60.0,
         "title_link": "/track/one", "has_lyrics": False, "lyrics": None,
         "file": {"mp3-128": "https://t4.bcbits.com/stream/one"}},
        {"track_num": 1, "title": "Two", "artist": "Loopy", "duration": 30.0,
         "title_link": "/track/two", "has_lyrics": False, "lyrics": None,
         "file": {"mp3-128": "https://t4.bcbits.com/stream/two"}},
    ]
    responses.add(responses.GET, TRACK_URL, body=track_html(schema=schema, tralbum=tralbum))

    album = Bandcamp().parse(TRACK_URL)

    assert [track["track"] for track in album["tracks"]] == ["2", "3"]
