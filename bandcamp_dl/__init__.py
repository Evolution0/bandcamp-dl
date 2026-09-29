import importlib.metadata
import pathlib
import tomllib


try:
    __version__ = importlib.metadata.version("bandcamp-downloader")
except importlib.metadata.PackageNotFoundError:
    # If running in a development environment we ideally are not installed in the venv as such fetch from pyproject.toml
    here = pathlib.Path(__file__).parent.parent.resolve()
    with open(f'{here}/pyproject.toml', 'rb') as pyproject:
        metadata = tomllib.load(pyproject)
        __version__ = metadata['project']['version']
