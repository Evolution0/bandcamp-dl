import bs4

from bandcamp_dl.bandcamp import Bandcamp


def art_page(href):
    return f'<html><body><div id="tralbumArt"><a href="{href}">cover</a></div></body></html>'


def soup_for(body):
    bandcamp = Bandcamp()
    bandcamp.soup = bs4.BeautifulSoup(body, "html.parser")
    return bandcamp


def test_a_page_without_cover_is_not_fatal():
    bandcamp = soup_for('<html><body><div id="other"></div></body></html>')
    assert bandcamp.get_album_art(0) == ""


def test_a_cover_element_without_a_link_is_not_fatal():
    bandcamp = soup_for('<html><body><div id="tralbumArt"></div></body></html>')
    assert bandcamp.get_album_art(0) == ""


def test_the_quality_token_is_replaced_not_appended():
    bandcamp = soup_for(art_page("https://f4.bcbits.com/img/a1234567890_10.jpg"))

    assert bandcamp.get_album_art(0) == "https://f4.bcbits.com/img/a1234567890_0.jpg"
    assert bandcamp.get_album_art(16) == "https://f4.bcbits.com/img/a1234567890_16.jpg"


def test_a_cover_url_without_a_quality_token_is_left_alone():
    bandcamp = soup_for(art_page("https://f4.bcbits.com/img/a1234567890.jpg"))
    assert bandcamp.get_album_art(16) == "https://f4.bcbits.com/img/a1234567890.jpg"
