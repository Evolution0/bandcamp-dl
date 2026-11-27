from types import SimpleNamespace

import responses

from bandcamp_dl.bandcampdownloader import BandcampDownloader

TRACK_URL = "https://t4.bcbits.com/stream/abc/mp3-128/1"
# 20 silent MPEG-1 Layer III frames (128 kbps, 44.1 kHz, 417 bytes each)
MP3_BYTES = (b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20


def make_album(full):
    return {"tracks": [{"duration": 1.0, "track": "1", "title": "One", "artist": "Loopy",
                        "track_id": 1, "url": TRACK_URL}],
            "title": "First", "artist": "Loopy", "label": None, "full": full, "art": "",
            "date": "2026", "url": "https://loopy.bandcamp.com/album/first", "genres": "",
            "album_id": 7}


def make_downloader(base_dir, no_confirm):
    config = SimpleNamespace(
        limit_req_per_minute=0, template="%{artist}/%{album}/%{track} - %{title}",
        base_dir=str(base_dir), untitled_path_from_slug=False, no_slugify=False,
        truncate_album=0, truncate_track=0, ascii_only=False, ok_chars="-_~",
        space_char="-", keep_spaces=False, case_mode="lower", overwrite=False,
        debug=True, embed_art=False, embed_genres=False, embed_lyrics=False, group=False,
        no_confirm=no_confirm, retag=False, progress="auto")
    return BandcampDownloader(config, "https://loopy.bandcamp.com/album/first")


@responses.activate
def test_a_yes_answer_starts_the_download_of_an_incomplete_album(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})

    assert make_downloader(tmp_path, no_confirm=False).start(make_album(full=False)) is True

    assert "Starting download process." in capsys.readouterr().out
    assert (tmp_path / "loopy" / "first" / "01 - one.mp3").stat().st_size >= len(MP3_BYTES)


@responses.activate
def test_a_short_yes_answer_is_enough(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "Y")
    responses.add(responses.GET, TRACK_URL, body=MP3_BYTES,
                  headers={"Content-Length": str(len(MP3_BYTES))})

    assert make_downloader(tmp_path, no_confirm=False).start(make_album(full=False)) is True


@responses.activate
def test_a_no_answer_cancels_without_touching_the_server(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "no")

    assert make_downloader(tmp_path, no_confirm=False).start(make_album(full=False)) is None

    assert "Cancelling download process." in capsys.readouterr().out
    assert len(responses.calls) == 0


def test_no_confirm_downloads_an_incomplete_album_without_asking(tmp_path, monkeypatch):
    # --no-confirm is what scripts use; a prompt waiting on stdin would hang them
    def refuse(prompt):
        raise AssertionError(f"prompted without --no-confirm: {prompt}")

    monkeypatch.setattr("builtins.input", refuse)
    monkeypatch.setattr(BandcampDownloader, "download_album", lambda self, album: True)

    assert make_downloader(tmp_path, no_confirm=False).start(make_album(full=True)) is True
    assert make_downloader(tmp_path, no_confirm=True).start(make_album(full=False)) is True
