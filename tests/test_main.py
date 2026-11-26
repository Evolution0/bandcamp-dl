import sys

import pytest

from bandcamp_dl import __main__ as entry_point
from bandcamp_dl.bandcamp import Bandcamp
from bandcamp_dl.bandcampdownloader import BandcampDownloader
from bandcamp_dl import config as config_module


def make_album(url, full=True):
    return {"tracks": [], "title": url.rsplit('/', 1)[-1], "artist": "A", "label": None,
            "full": full, "art": "", "date": "2026", "url": url, "genres": "", "album_id": 1}


@pytest.fixture
def downloaded(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "bandcamp-dl.json")
    urls = []
    monkeypatch.setattr(BandcampDownloader, "start",
                        lambda self, album: urls.append(album["url"]) or None)
    return urls


def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ("bandcamp-dl",) + argv)
    entry_point.main()


def test_artist_with_album_slug_downloads_that_one_album(downloaded, monkeypatch):
    monkeypatch.setattr(Bandcamp, "parse", lambda self, url, *args: make_album(url))

    run(monkeypatch, "--artist", "loopy", "--album", "first")

    assert downloaded == ["https://loopy.bandcamp.com/album/first"]


def test_a_playlist_adds_its_tracks_to_the_other_urls(downloaded, monkeypatch):
    monkeypatch.setattr(Bandcamp, "get_playlist",
                        lambda self, url: [f"{url}/track/{name}" for name in ("one", "two")])
    monkeypatch.setattr(Bandcamp, "parse", lambda self, url, *args: make_album(url))

    run(monkeypatch, "https://a.bandcamp.com/album/first", "https://a.bandcamp.com/playlist/mix")

    assert downloaded == ["https://a.bandcamp.com/album/first",
                          "https://a.bandcamp.com/playlist/mix/track/one",
                          "https://a.bandcamp.com/playlist/mix/track/two"]


def test_full_album_pruning_checks_every_album(downloaded, monkeypatch):
    monkeypatch.setattr(Bandcamp, "parse",
                        lambda self, url, *args: make_album(url, full="incomplete" not in url))

    incomplete = ["https://a.bandcamp.com/album/incomplete-one",
                  "https://a.bandcamp.com/album/incomplete-two"]
    run(monkeypatch, "-f", *incomplete, "https://a.bandcamp.com/album/complete")

    assert downloaded == ["https://a.bandcamp.com/album/complete"]


def test_an_unparsable_url_is_reported_and_fails_the_run(downloaded, monkeypatch, capsys):
    def parse_only_complete_urls(self, url, *args):
        return None if "://" not in url else make_album(url)

    monkeypatch.setattr(Bandcamp, "parse", parse_only_complete_urls)

    with pytest.raises(SystemExit) as exit_info:
        run(monkeypatch, "a.bandcamp.com/album/first", "https://a.bandcamp.com/album/second")

    assert exit_info.value.code == 1
    assert "Could not parse" in capsys.readouterr().out
    assert downloaded == ["https://a.bandcamp.com/album/second"]


def test_a_failed_album_exits_nonzero(downloaded, monkeypatch):
    monkeypatch.setattr(Bandcamp, "parse", lambda self, url, *args: make_album(url))
    monkeypatch.setattr(BandcampDownloader, "start", lambda self, album: False)

    with pytest.raises(SystemExit) as exit_info:
        run(monkeypatch, "https://a.bandcamp.com/album/first")

    assert exit_info.value.code == 1
