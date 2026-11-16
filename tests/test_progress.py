from types import SimpleNamespace

import responses

from bandcamp_dl.bandcampdownloader import BandcampDownloader
from bandcamp_dl.progress import ICON_DONE, STEP_DOWNLOADED, STEP_SKIPPED, RichProgress

# 20 silent MPEG-1 Layer III frames (128 kbps, 44.1 kHz, 417 bytes each)
MP3_BYTES = (b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20
ALBUM = {
    "tracks": [
        {"duration": 1.0, "track": "1", "title": "One", "artist": "Loopy", "track_id": 1,
         "url": "https://t4.bcbits.com/stream/1"},
        {"duration": 1.0, "track": "2", "title": "[PLEASE HOLD…] Two", "artist": "Loopy",
         "track_id": 2, "url": "https://t4.bcbits.com/stream/2"},
    ],
    "title": "First", "artist": "Loopy", "label": None, "full": True, "art": "",
    "date": "2026", "url": "https://loopy.bandcamp.com/album/first", "genres": "", "album_id": 7,
}


def make_downloader(base_dir, progress):
    config = SimpleNamespace(
        limit_req_per_minute=0, template="%{artist}/%{album}/%{track} - %{title}",
        base_dir=str(base_dir), untitled_path_from_slug=False, no_slugify=False,
        truncate_album=0, truncate_track=0, ascii_only=False, ok_chars="-_~",
        space_char="-", keep_spaces=False, case_mode="lower", overwrite=False,
        debug=False, embed_art=False, embed_genres=False, embed_lyrics=False, group=False,
        no_confirm=True, progress=progress, retag=False)
    return BandcampDownloader(config, ALBUM["url"])


def add_tracks(tmp_path):
    """Track 1 is already downloaded, track 2 needs downloading"""
    album_dir = tmp_path / "loopy" / "first"
    album_dir.mkdir(parents=True)
    (album_dir / "01 - one.mp3").write_bytes(MP3_BYTES)
    for track in ALBUM["tracks"]:
        responses.add(responses.GET, track["url"], body=MP3_BYTES,
                      headers={"Content-Length": str(len(MP3_BYTES))})


@responses.activate
def test_auto_progress_marks_each_track_and_prints_titles_literally(tmp_path, capsys):
    add_tracks(tmp_path)
    downloader = make_downloader(tmp_path, "auto")

    assert downloader.download_album(ALBUM) is True

    assert isinstance(downloader.progress, RichProgress)
    tasks = downloader.progress.progress.tasks
    assert [task.fields["icon"] for task in tasks] == [ICON_DONE, ICON_DONE]
    assert [task.fields["step"] for task in tasks] == [STEP_SKIPPED, STEP_DOWNLOADED]
    output = capsys.readouterr().out
    assert "Loopy - First" in output
    assert "[PLEASE HOLD…] Two" in output


@responses.activate
def test_plain_progress_keeps_original_output(tmp_path, capsys):
    add_tracks(tmp_path)

    assert make_downloader(tmp_path, "plain").download_album(ALBUM) is True

    output = capsys.readouterr().out
    assert "File: 01 - one.mp3 already exists and is complete, skipping.." in output
    assert "(2/2) [" in output
    assert ":: Finished: 02 - please-hold-two" in output


def test_titles_drop_zero_width_characters():
    # Terminal.app draws U+200B one cell wide while rich counts it as zero,
    # so the line overflows the window and the live display repeats it
    progress = RichProgress(debug=True)
    progress.album({**ALBUM, "tracks": [{**ALBUM["tracks"][0], "title": "お帰りなさい​!​!"}]})

    assert progress.titles == ["01 お帰りなさい!!"]


def test_step_and_size_columns_keep_a_fixed_width():
    progress = RichProgress(debug=True)
    step, size = progress.progress.columns[-2:]

    assert step.get_table_column().width == len(STEP_SKIPPED)
    assert size.get_table_column().width == len("999.9/999.9 MB")


def test_albums_with_right_to_left_titles_put_the_title_last():
    # Terminal.app draws Arabic script wider than rich counts, which shifts every column after it
    progress = RichProgress(debug=True)
    progress.album({**ALBUM, "tracks": [ALBUM["tracks"][0], {**ALBUM["tracks"][1], "title": "گاوچو"}]})

    title = progress.progress.columns[-1]
    assert title.text_format == "{task.description}"
    assert progress.progress.expand is False
    assert title.get_table_column().max_width < progress.progress.console.width // 2


def test_albums_without_right_to_left_titles_keep_the_title_second():
    progress = RichProgress(debug=True)
    progress.album(ALBUM)

    assert progress.progress.columns[1].text_format == "{task.description}"
    assert progress.progress.expand is True
