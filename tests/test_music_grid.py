import html
import json

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
