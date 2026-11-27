import pathlib
import runpy
import sys

import pytest

from bandcamp_dl import __version__
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


@pytest.fixture
def configs(tmp_path, monkeypatch, downloaded):
    """Keep the argument namespace each album was downloaded with"""
    kept = []

    def record_start(self, album):
        kept.append(self.config)
        downloaded.append(album["url"])

    monkeypatch.setattr(BandcampDownloader, "start", record_start)
    monkeypatch.setattr(config_module, "USER_HOME", tmp_path)
    return kept


def test_the_version_flag_prints_the_version_and_stops(capsys, monkeypatch):
    run(monkeypatch, "--version")

    assert capsys.readouterr().out == f"bandcamp-dl {__version__}\n"


def test_debug_sends_the_chatter_to_the_log(downloaded, monkeypatch, caplog):
    def parse_with_chatter(self, url, *args):
        self.logger.debug("parsing %s", url)
        return make_album(url)

    monkeypatch.setattr(Bandcamp, "parse", parse_with_chatter)

    run(monkeypatch, "--debug", "https://a.bandcamp.com/album/first")

    assert "parsing https://a.bandcamp.com/album/first" in caplog.text


def test_without_a_url_or_an_artist_the_usage_is_printed(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exit_info:
        run(monkeypatch)

    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "required: URL or --artist" in captured.err


def test_a_track_slug_with_an_artist_downloads_that_one_track(downloaded, monkeypatch):
    monkeypatch.setattr(Bandcamp, "parse", lambda self, url, *args: make_album(url))

    run(monkeypatch, "--artist", "loopy", "--track", "one")

    assert downloaded == ["https://loopy.bandcamp.com/track/one"]


def test_an_artist_alone_downloads_their_whole_discography(downloaded, monkeypatch):
    monkeypatch.setattr(Bandcamp, "get_full_discography",
                        lambda self, name, page_type: [f"https://{name}.bandcamp.com/album/{slug}"
                                                       for slug in ("one", "two")])
    monkeypatch.setattr(Bandcamp, "parse", lambda self, url, *args: make_album(url))

    run(monkeypatch, "--artist", "loopy")

    assert downloaded == ["https://loopy.bandcamp.com/album/one",
                         "https://loopy.bandcamp.com/album/two"]


def test_an_artist_page_url_is_expanded_before_downloading(downloaded, monkeypatch):
    monkeypatch.setattr(Bandcamp, "get_full_discography",
                        lambda self, name, page_type: [f"https://{name}.bandcamp.com/album/one"])
    monkeypatch.setattr(Bandcamp, "parse", lambda self, url, *args: make_album(url))

    run(monkeypatch, "https://loopy.bandcamp.com/music")

    assert downloaded == ["https://loopy.bandcamp.com/album/one"]


def test_a_url_that_is_not_an_album_or_a_track_is_left_alone(downloaded, monkeypatch):
    merch_only = ["https://a.bandcamp.com/merch/shirt"]
    monkeypatch.setattr(Bandcamp, "get_playlist", lambda self, url: merch_only)
    monkeypatch.setattr(Bandcamp, "parse", lambda self, url, *args: make_album(url))

    run(monkeypatch, "https://a.bandcamp.com/playlist/mix")

    assert downloaded == []


def test_an_empty_option_falls_back_to_the_configured_default(configs, monkeypatch):
    # --base-dir '' is what a wrapper script with an unset variable leaves behind
    monkeypatch.setattr(Bandcamp, "parse", lambda self, url, *args: make_album(url))

    run(monkeypatch, "--base-dir", "", "--template", "", "https://a.bandcamp.com/album/first")

    assert configs[0].base_dir == config_module.USER_HOME
    assert configs[0].template == config_module.TEMPLATE


def test_the_console_entry_point_runs_main(tmp_path, capsys, monkeypatch):
    # `python -m bandcamp_dl` executes this module as __main__; the guard has to keep working
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "bandcamp-dl.json")
    monkeypatch.setattr(sys, "argv", ["bandcamp-dl", "--version"])

    runpy.run_path(str(pathlib.Path(entry_point.__file__)), run_name="__main__")

    assert capsys.readouterr().out.endswith(f"bandcamp-dl {__version__}\n")
