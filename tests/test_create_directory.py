import os
from types import SimpleNamespace

from bandcamp_dl.bandcampdownloader import BandcampDownloader


def test_create_directory_tolerates_existing_dir_missed_by_exists_check(tmp_path, monkeypatch):
    # A flaky network mount can make os.path.exists() report False for a folder that exists
    album_dir = tmp_path / "artist" / "album"
    album_dir.mkdir(parents=True)
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    downloader = BandcampDownloader(SimpleNamespace(limit_req_per_minute=0))

    directory = downloader.create_directory(str(album_dir / "01 - one.mp3.tmp"))

    assert directory == str(album_dir)
