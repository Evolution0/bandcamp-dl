"""The parser choice every page parse shares

bs4 without lxml used to raise out of every single parse, so each page paid for a
BeautifulSoup construction it could not use; the choice is made once now.
"""

import bs4
import pytest

from bandcamp_dl.bandcamp import make_soup, soup_builder


@pytest.fixture
def fresh_probe(monkeypatch):
    """Undo a patched bs4 and drop whatever parser the probe cached from it"""
    yield
    soup_builder.cache_clear()


def test_a_page_is_parsed_with_the_cached_builder():
    soup = make_soup("<html><body><p id='x'>hi</p></body></html>")

    assert soup.find(id="x").text == "hi"
    assert soup_builder() in ("lxml", "html.parser")


def test_the_probe_runs_once_per_run(monkeypatch, fresh_probe):
    real_soup = bs4.BeautifulSoup
    asked = []

    def counting_soup(markup, features):
        asked.append(features)
        if features == "lxml":
            raise bs4.FeatureNotFound("lxml is not installed here")
        return real_soup(markup, features)

    monkeypatch.setattr(bs4, "BeautifulSoup", counting_soup)
    soup_builder.cache_clear()

    make_soup("<html><body><p>one</p></body></html>")
    make_soup("<html><body><p>two</p></body></html>")

    # Only the probe pays for the lxml attempt; the parses themselves go straight to
    # the builder this install has
    assert asked == ["lxml", "html.parser", "html.parser"]


def test_an_install_with_lxml_chooses_it(monkeypatch, fresh_probe):
    real_soup = bs4.BeautifulSoup
    asked = []

    def counting_soup(markup, features):
        asked.append(features)
        return real_soup(markup, "html.parser")

    monkeypatch.setattr(bs4, "BeautifulSoup", counting_soup)
    soup_builder.cache_clear()

    assert soup_builder() == "lxml"
    assert asked == ["lxml"]
