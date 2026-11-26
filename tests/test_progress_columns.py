from bandcamp_dl.progress import (DownloadBarColumn, ICON_DONE, ICON_FAILED, PlainProgress,
                                  RichProgress, STEP_DOWNLOADING, STEP_FAILED, STEP_TAGGING,
                                  STEP_WAITING, SizeColumn, StatusColumn, StepColumn)

ALBUM = {"tracks": [{"track": "1", "title": "One"}], "artist": "Loopy", "title": "First"}


def column(progress, kind):
    return next(col for col in progress.progress.columns if isinstance(col, kind))


def test_the_status_icon_is_blank_until_the_task_starts():
    # A spinner on a track that has not started yet makes an untouched track look busy
    progress = RichProgress(debug=True)
    progress.album(ALBUM)
    task = progress.progress.tasks[0]

    assert column(progress, StatusColumn).render(task).plain == " "


def test_the_bar_is_only_drawn_while_the_track_downloads():
    progress = RichProgress(debug=True)
    progress.album(ALBUM)
    task = progress.progress.tasks[0]
    bar = column(progress, DownloadBarColumn)

    assert bar.render(task).plain == ""

    progress.track(0, "01 - one.mp3.tmp")
    progress.downloading(1000)

    downloading = bar.render(task)
    assert downloading.total == 1000
    assert task.fields["step"] == STEP_DOWNLOADING


def test_the_step_column_names_the_step_the_track_is_on():
    progress = RichProgress(debug=True)
    progress.album(ALBUM)
    task = progress.progress.tasks[0]
    step = column(progress, StepColumn)

    assert step.render(task).plain == STEP_WAITING

    progress.track(0, "01 - one.mp3.tmp")
    progress.tagging()
    assert step.render(task).plain == STEP_TAGGING

    progress.failed("not an mp3")
    assert step.render(task).plain == STEP_FAILED


def test_the_size_column_stays_blank_until_the_size_is_known():
    progress = RichProgress(debug=True)
    progress.album(ALBUM)
    task = progress.progress.tasks[0]
    size = column(progress, SizeColumn)

    assert size.render(task).plain == ""

    progress.track(0, "01 - one.mp3.tmp")
    progress.finished(1024)
    assert "1.0/1.0 kB" in size.render(task).plain


def test_a_failure_names_the_track_outside_debug_mode(capsys):
    # The failure line has to be printed somewhere or a skipped track is invisible
    progress = RichProgress(debug=False)
    progress.album(ALBUM)
    progress.track(0, "01 - one.mp3.tmp")

    progress.failed("not an mp3")

    output = capsys.readouterr().out
    assert f"{ICON_FAILED} 01 One: not an mp3" in output


def test_a_failure_is_quiet_in_debug_mode(capsys):
    progress = RichProgress(debug=True)
    progress.album(ALBUM)
    progress.track(0, "01 - one.mp3.tmp")

    progress.failed("not an mp3")

    assert capsys.readouterr().out == ""


def test_the_status_column_spins_while_a_track_is_working():
    progress = RichProgress(debug=True)
    progress.album(ALBUM)
    task = progress.progress.tasks[0]
    status = column(progress, StatusColumn)
    progress.track(0, "01 - one.mp3.tmp")
    progress.downloading(1000)

    assert status.render(task).plain.strip() != ""

    progress.finished(1000)
    assert status.render(task).plain == ICON_DONE


def test_plain_progress_still_reports_a_failure(capsys):
    progress = PlainProgress(debug=False)
    progress.failed("Maximum retries reached.. skipping.")

    assert capsys.readouterr().out == "Maximum retries reached.. skipping.\n"
