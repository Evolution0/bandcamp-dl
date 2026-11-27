import pytest
import responses

from bandcamp_dl import bandcamp as bandcamp_module
from bandcamp_dl.bandcamp import Bandcamp, PAGE_RETRIES

ALBUM_URL = "https://busy.bandcamp.com/album/first"
MUSIC_URL = "https://busy.bandcamp.com/music"


def add_rate_limited(url):
    responses.add(responses.GET, url, status=429, headers={"Retry-After": "0"})


@responses.activate
def test_get_page_retries_after_rate_limit():
    add_rate_limited(ALBUM_URL)
    responses.add(responses.GET, ALBUM_URL, body="<html>ok</html>")

    response = Bandcamp().get_page(ALBUM_URL)

    assert response.status_code == 200
    assert len(responses.calls) == 2


@responses.activate
def test_parse_reports_rate_limit_instead_of_missing_album(capsys):
    add_rate_limited(ALBUM_URL)

    with pytest.raises(SystemExit) as exit_info:
        Bandcamp().parse(ALBUM_URL)

    assert exit_info.value.code == 2
    output = capsys.readouterr().out
    assert "HTTP 429" in output
    assert "does not exist" not in output


@responses.activate
def test_discography_fails_loudly_when_rate_limited(capsys):
    add_rate_limited(MUSIC_URL)

    with pytest.raises(SystemExit) as exit_info:
        Bandcamp().get_full_discography("busy", "music")

    assert exit_info.value.code == 2
    assert "HTTP 429" in capsys.readouterr().out


@responses.activate
def test_get_page_does_not_sleep_after_the_last_attempt(monkeypatch):
    slept = []
    monkeypatch.setattr(bandcamp_module.time, "sleep", lambda seconds: slept.append(seconds))
    add_rate_limited(MUSIC_URL)

    with pytest.raises(SystemExit):
        Bandcamp().get_full_discography("busy", "music")

    assert len(slept) == PAGE_RETRIES - 1


@responses.activate
def test_a_rate_limited_run_says_to_limit_the_requests_once(caplog):
    add_rate_limited(ALBUM_URL)
    responses.add(responses.GET, ALBUM_URL, body="<html>ok</html>")
    add_rate_limited(MUSIC_URL)
    responses.add(responses.GET, MUSIC_URL, body="<html>ok</html>")

    bandcamp = Bandcamp()
    bandcamp.get_page(ALBUM_URL)
    bandcamp.get_page(MUSIC_URL)

    assert "--limit-req-per-minute" in caplog.text
    # Four rate limited requests, one piece of advice
    assert caplog.text.count("--limit-req-per-minute") == 1
