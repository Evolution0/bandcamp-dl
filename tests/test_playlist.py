import html
import json

import responses

from bandcamp_dl.bandcamp import Bandcamp

PLAYLIST_URL = "https://mix.bandcamp.com/playlist/late-nights"
PLAYER_API = "https://bandcamp.com/api/player/2/player_data_web"
PAGE_TRACKS = [f"https://a.bandcamp.com/track/p{i}" for i in range(50)]
API_TRACKS = [f"https://a.bandcamp.com/track/p{i}" for i in range(25, 75)]


def playlist_page(urls, total):
    blob = html.escape(json.dumps({
        "appData": {
            "playlistId": 77,
            "tracklist": {
                "tracksSummary": {"totalCount": total},
                "tracks": [{"url": url} for url in urls],
            },
        }
    }))
    return f'<html><body><div id="PlaylistPage" data-blob="{blob}"></div></body></html>'


@responses.activate
def test_the_cursor_loop_stops_after_the_tracks_the_playlist_advertises():
    responses.add(responses.GET, PLAYLIST_URL, body=playlist_page(PAGE_TRACKS, 120))
    api_page = {"tracklist": {"nextCursor": 99, "tracks": [{"url": url} for url in API_TRACKS]}}
    # The server keeps handing back a cursor; without a bound this never terminates
    responses.add(responses.POST, PLAYER_API, json=api_page)

    urls = Bandcamp().get_playlist(PLAYLIST_URL)

    assert len([call for call in responses.calls if call.request.url == PLAYER_API]) == 2
    # The page and the paged API overlap on 25 tracks; downloading one twice is pointless
    assert len(urls) == len(set(urls)) == 75


@responses.activate
def test_a_failing_page_request_keeps_the_tracks_already_fetched(caplog):
    responses.add(responses.GET, PLAYLIST_URL, body=playlist_page(PAGE_TRACKS, 120))
    responses.add(responses.POST, PLAYER_API, status=500)

    urls = Bandcamp().get_playlist(PLAYLIST_URL)

    assert len(urls) == 50
    assert "Playlist tracklist request failed" in caplog.text


@responses.activate
def test_tracks_from_short_playlists_are_left_untouched():
    responses.add(responses.GET, PLAYLIST_URL, body=playlist_page(PAGE_TRACKS[:10], 10))

    assert Bandcamp().get_playlist(PLAYLIST_URL) == PAGE_TRACKS[:10]


@responses.activate
def test_the_cursor_loop_stops_when_the_api_returns_no_more_tracks():
    responses.add(responses.GET, PLAYLIST_URL, body=playlist_page(PAGE_TRACKS, 120))
    responses.add(responses.POST, PLAYER_API, json={"tracklist": {"nextCursor": 99, "tracks": []}})

    assert Bandcamp().get_playlist(PLAYLIST_URL) == PAGE_TRACKS
    assert len([call for call in responses.calls if call.request.url == PLAYER_API]) == 1


@responses.activate
def test_tracks_from_a_disabled_band_are_dropped_from_the_queue():
    urls = PAGE_TRACKS[:3] + ["https://gone.bandcamp.com/-disabled-/track/x"]
    responses.add(responses.GET, PLAYLIST_URL, body=playlist_page(urls, len(urls)))

    assert Bandcamp().get_playlist(PLAYLIST_URL) == PAGE_TRACKS[:3]
