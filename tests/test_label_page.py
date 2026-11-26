import responses

from bandcamp_dl.bandcamp import Bandcamp


def label_page(links):
    """A label page: no music grid, the bands are listed in the label cells"""
    cells = "".join(f'<div class="ipCellLabel1"><a href="{link}">x</a></div>' for link in links)
    return (f'<html><body><script id="band-menuitem-template">template</script>'
            f'{cells}</body></html>')


@responses.activate
def test_a_label_page_lists_bands_with_absolute_and_relative_links():
    url = "https://some-label.bandcamp.com/music"
    responses.add(responses.GET, url, body=label_page([
        "/band/relative",
        "https://other.bandcamp.com",
        "https://gone.bandcamp.com/-disabled-/band/x",
        "",
    ]))

    urls = Bandcamp().get_full_discography("some-label", "music")

    # Deleted or disabled bands have mangled links; downloading them would only fail later
    assert sorted(urls) == ["https://other.bandcamp.com",
                            "https://some-label.bandcamp.com/band/relative"]


@responses.activate
def test_a_page_with_neither_a_grid_nor_a_label_template_finds_nothing(caplog):
    url = "https://mystery.bandcamp.com/music"
    responses.add(responses.GET, url, body="<html><body><p>nothing to scrape</p></body></html>")

    assert Bandcamp().get_full_discography("mystery", "music") == []
    assert "Could not find music grid on the page. No albums found." in caplog.text
    assert "Retrying as a Label page." in caplog.text
