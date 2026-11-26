import html
import json

import requests
import responses

from bandcamp_dl.bandcamp import Bandcamp

MUSIC_URL = "https://grid.bandcamp.com/music"


def music_page(links, client_items=None):
    items = "".join(f'<li class="music-grid-item"><a href="{link}">x</a></li>' for link in links)
    attr = f' data-client-items="{html.escape(json.dumps(client_items))}"' if client_items else ""
    return f'<html><body><ol id="music-grid"{attr}>{items}</ol></body></html>'


@responses.activate
def test_discography_reads_grid_links_without_client_items():
    responses.add(responses.GET, MUSIC_URL, body=music_page(["/album/one", "/track/two"]))

    urls = Bandcamp().get_full_discography("grid", "music")

    assert sorted(urls) == ["https://grid.bandcamp.com/album/one",
                            "https://grid.bandcamp.com/track/two"]


@responses.activate
def test_discography_combines_grid_links_and_client_items():
    page = music_page(["/album/four", "/album/one"],
                      [{"page_url": "/album/one"}, {"page_url": "/album/three"}])
    responses.add(responses.GET, MUSIC_URL, body=page)

    urls = Bandcamp().get_full_discography("grid", "music")

    assert sorted(urls) == ["https://grid.bandcamp.com/album/four",
                            "https://grid.bandcamp.com/album/one",
                            "https://grid.bandcamp.com/album/three"]


@responses.activate
def test_unreadable_client_items_do_not_hide_the_grid_links(caplog):
    page = ('<html><body><ol id="music-grid" data-client-items="this is not json">'
            '<li class="music-grid-item"><a href="/album/one">x</a></li></ol></body></html>')
    responses.add(responses.GET, MUSIC_URL, body=page)

    urls = Bandcamp().get_full_discography("grid", "music")

    assert urls == ["https://grid.bandcamp.com/album/one"]
    assert "Failed to parse data-client-items JSON" in caplog.text


@responses.activate
def test_an_unreachable_artist_page_is_not_reported_as_an_empty_one(caplog):
    responses.add(responses.GET, MUSIC_URL,
                  body=requests.exceptions.ConnectionError("no route to the host"))

    assert Bandcamp().get_full_discography("grid", "music") == []
    assert "Could not fetch artist/label page" in caplog.text
