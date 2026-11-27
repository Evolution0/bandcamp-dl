"""Download progress output: a per-track display (like brew and docker compose) or plain lines"""
import shutil
import unicodedata

from rich.progress import (BarColumn, DownloadColumn, Progress, ProgressColumn, SpinnerColumn,
                           Task, TextColumn)
from rich.table import Column
from rich.text import Text

PROGRESS_AUTO = "auto"
PROGRESS_PLAIN = "plain"
ICON_DONE = "✔"
ICON_FAILED = "✘"
STEP_WAITING = "Waiting"
STEP_DOWNLOADING = "Downloading"
STEP_TAGGING = "Tagging"
STEP_DOWNLOADED = "Downloaded"
STEP_TAGGED = "Tagged"
STEP_SKIPPED = "Already downloaded"
STEP_FAILED = "Failed"
# Widest DownloadColumn text, so the step and size line up from album to album
SIZE_WIDTH = len("999.9/999.9 MB")
RTL_BAR_WIDTH = 20
# Icon, step, size and bar, plus the one-cell gaps between the five columns
RTL_FIXED_WIDTH = 1 + len(STEP_SKIPPED) + SIZE_WIDTH + RTL_BAR_WIDTH + 4


def display_title(title: str) -> str:
    """Drop invisible format and control characters (like U+200B) that terminals draw
    with a width rich doesn't expect, which pushes the line past the window edge"""
    # shortcut: also splits emoji joined with U+200D, fine for track titles
    return "".join(c for c in title if unicodedata.category(c) not in ("Cf", "Cc"))


def is_rtl(text: str) -> bool:
    return any(unicodedata.bidirectional(c) in ("R", "AL") for c in text)


def print_clean(msg, width: int):
    """Erase what a longer line left behind by padding the new one to the window width

    :param msg: the line to print without a newline
    :param width: the terminal width the padding is measured against
    """
    print(f'{msg}{" " * (width - len(msg))}', end='')


class StatusColumn(SpinnerColumn):
    """Blank while waiting, a spinner while working, then the icon set on the task"""

    def render(self, task: Task) -> Text:
        if task.fields.get('icon'):
            style = "red" if task.fields['icon'] == ICON_FAILED else "green"
            return Text(task.fields['icon'], style=style)
        if not task.started:
            return Text(" ")
        return super().render(task)


class DownloadBarColumn(BarColumn):
    """A bar that fills the free width while the track downloads, blank otherwise"""

    def render(self, task: Task) -> Text:
        if task.fields.get('step') != STEP_DOWNLOADING:
            return Text("")
        return super().render(task)


class StepColumn(ProgressColumn):
    """The step the track is on: waiting, downloading, tagging, then the outcome"""

    def render(self, task: Task) -> Text:
        step = task.fields.get('step', "")
        style = {STEP_WAITING: "dim", STEP_FAILED: "red"}.get(step, "")
        return Text(step, style=style)


class SizeColumn(DownloadColumn):
    """Downloaded/total size, blank until the size is known"""

    def render(self, task: Task) -> Text:
        if task.total is None:
            return Text("")
        return super().render(task)


def title_column(max_width: int | None = None) -> TextColumn:
    # markup=False: titles like "[PLEASE HOLD…]" would otherwise be read as rich markup
    return TextColumn("{task.description}", markup=False,
                      table_column=Column(no_wrap=True, overflow="ellipsis", max_width=max_width))


def step_column() -> StepColumn:
    return StepColumn(table_column=Column(width=len(STEP_SKIPPED)))


def size_column() -> SizeColumn:
    return SizeColumn(table_column=Column(width=SIZE_WIDTH, justify="right"))


class RichProgress:
    """One line per track that updates in place, laid out like brew: icon and title on the
    left, a bar that grows with the window, then the step and size at the right edge"""

    def __init__(self, debug: bool):
        self.debug = debug
        bar = DownloadBarColumn(bar_width=None, table_column=Column(ratio=1))
        self.progress = Progress(StatusColumn(), title_column(), bar, step_column(), size_column(),
                                 expand=True, disable=debug)
        self.tasks = []
        self.titles = []
        self.task = None
        self.title = ""
        self.downloaded = False

    def __enter__(self):
        self.progress.start()
        return self

    def __exit__(self, *exc_info):
        self.progress.stop()

    def album(self, album: dict):
        if not self.debug:
            self.progress.console.print(Text(f"{album['artist']} - {album['title']}", style="bold"))
        self.titles = [f"{str(track['track']).zfill(2)} {display_title(track['title'])}" for track in album['tracks']]
        if any(is_rtl(title) for title in self.titles):
            self.title_last()
        self.tasks = [self.progress.add_task(title, start=False, total=None, step=STEP_WAITING)
                      for title in self.titles]

    def title_last(self):
        """Terminal.app draws Arabic script wider than rich counts, at no fixed ratio, so
        no padding lines up the columns after it. Put the title last, with no padding
        after it and room to be drawn up to twice as wide without wrapping."""
        room = (self.progress.console.width - RTL_FIXED_WIDTH) // 2
        bar = DownloadBarColumn(bar_width=RTL_BAR_WIDTH, table_column=Column(width=RTL_BAR_WIDTH))
        self.progress.columns = (StatusColumn(), step_column(), size_column(), bar,
                                 title_column(max_width=max(room, 1)))
        self.progress.expand = False

    def track(self, index: int, filename: str):
        self.task = self.tasks[index]
        self.title = self.titles[index]
        self.downloaded = False

    def downloading(self, size: int):
        self.progress.start_task(self.task)
        self.progress.update(self.task, total=size or None, completed=0, step=STEP_DOWNLOADING)
        self.downloaded = True

    def advance(self, downloaded: int):
        self.progress.update(self.task, completed=downloaded)

    def tagging(self):
        # Retagging and leftover .tmp files are tagged without downloading first
        self.progress.start_task(self.task)
        self.progress.update(self.task, step=STEP_TAGGING)

    def finished(self, size: int):
        self.progress.update(self.task, icon=ICON_DONE, total=size, completed=size,
                             step=STEP_DOWNLOADED if self.downloaded else STEP_TAGGED)

    def skipped(self):
        self.progress.update(self.task, icon=ICON_DONE, step=STEP_SKIPPED)

    def failed(self, message: str):
        self.progress.update(self.task, icon=ICON_FAILED, step=STEP_FAILED)
        if not self.debug:
            self.progress.console.print(Text(f"{ICON_FAILED} {self.title}: {message}", style="red"))


class PlainProgress:
    """The original output: one line per track, rewritten in place with a text bar"""

    def __init__(self, debug: bool):
        self.debug = debug
        self.num_tracks = 0
        self.track_num = 0
        self.filename = ""
        self.size = 0
        # The terminal width is stable within a track: asking per progress step costs
        # an environment lookup and a COLUMNS check thousands of times per album
        self.width = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass

    def album(self, album: dict):
        self.num_tracks = len(album['tracks'])

    def track(self, index: int, filename: str):
        self.track_num = index + 1
        self.filename = filename
        self.width = shutil.get_terminal_size().columns

    def downloading(self, size: int):
        self.size = size

    def advance(self, downloaded: int):
        if not self.debug and self.size:
            done = int(50 * downloaded / self.size)
            print_clean(f'\r({self.track_num}/{self.num_tracks}) '
                        f'[{"=" * done}{" " * (50 - done)}] :: '
                        f'Downloading: {self.filename[:-8]}', self.width)

    def tagging(self):
        if not self.debug:
            print_clean(f'\r({self.track_num}/{self.num_tracks}) [{"=" * 50}] '
                        f':: Encoding: {self.filename[:-8]}', self.width)

    def finished(self, size: int):
        if not self.debug:
            print_clean(f'\r({self.track_num}/{self.num_tracks}) [{"=" * 50}] '
                        f':: Finished: {self.filename[:-8]}', self.width)

    def skipped(self):
        print(f"File: {self.filename[:-4]} already exists and is complete, skipping..")

    def failed(self, message: str):
        print(message)


def make_progress(mode: str, debug: bool) -> RichProgress | PlainProgress:
    return PlainProgress(debug) if mode == PROGRESS_PLAIN else RichProgress(debug)
