import importlib
import importlib.metadata
import pathlib
import tomllib

import bandcamp_dl


def test_the_version_falls_back_to_pyproject_when_not_installed(monkeypatch):
    # Running from a checkout there is no installed distribution to ask importlib about,
    # so the version comes from pyproject.toml instead of crashing the import
    def no_distribution(_name):
        raise importlib.metadata.PackageNotFoundError("bandcamp-dl")

    monkeypatch.setattr(importlib.metadata, "version", no_distribution)

    module = importlib.reload(bandcamp_dl)

    pyproject = (pathlib.Path(module.__file__).parent.parent / "pyproject.toml")
    with pyproject.open("rb") as handle:
        expected = tomllib.load(handle)["project"]["version"]

    assert module.__version__ == expected
    assert module.__version__ != ""
