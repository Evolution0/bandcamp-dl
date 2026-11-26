"""The options bandcamp-dl runs with, where they are stored, and how renamed
options move between builds that know different names for the same setting.

One field per option, the value a first run writes out being the default.
The file spells the names with hyphens, the code with underscores, so the
two are mapped at the read/write boundary and nowhere in between.
"""

import json
import os
import pathlib
import sys
from dataclasses import dataclass, fields

from bandcamp_dl.progress import PROGRESS_AUTO

TEMPLATE = '%{artist}/%{album}/%{track} - %{title}'
OK_CHARS = '-_~'
SPACE_CHAR = '-'
CASE_LOWER = 'lower'
CASE_UPPER = 'upper'
CASE_CAMEL = 'camel'
CASE_NONE = 'none'
USER_HOME = pathlib.Path.home()
# For Linux/BSD https://www.freedesktop.org/wiki/Software/xdg-user-dirs/
# For Windows and MacOS .appname is fine
CONFIG_PATH = USER_HOME / (".config" if os.name == "posix" else ".bandcamp-dl") / "bandcamp-dl.json"


@dataclass
class Config:
    """the option set as this build understands it"""

    base_dir: str = str(USER_HOME)  # TODO: pass the Path object instead?
    template: str = TEMPLATE
    overwrite: bool = False
    retag: bool = False
    no_art: bool = False
    embed_art: bool = False
    embed_lyrics: bool = False
    group: bool = False
    no_slugify: bool = False
    ok_chars: str = OK_CHARS
    space_char: str = SPACE_CHAR
    ascii_only: bool = False
    keep_spaces: bool = False
    case_mode: str = CASE_LOWER
    no_confirm: bool = False
    debug: bool = False
    embed_genres: bool = False
    cover_quality: int = 0
    untitled_path_from_slug: bool = False
    truncate_album: int = 0
    truncate_track: int = 0
    limit_req_per_minute: int = 0
    progress: str = PROGRESS_AUTO


def option_names() -> set[str]:
    """the option names this build stores, spelled the way the code spells them

    :return: the field names of Config, with underscores
    """
    return {field.name for field in fields(Config)}


def migrate_option(key: str, val: object, known: set[str]) -> tuple[str, object] | None:
    """translate an option this build does not store into the one it does

    the direction follows from which name of a rename ``known``, the option set
    of the build doing the migrating, carries: an older file's option is brought
    forward, a newer file's option is answered in the older vocabulary. Either
    way the returned name is one the migrating build stores, so the caller can
    hold it on the Config it is building and write it back out.

    :param key: the option name read from the file
    :param val: the value it carries there
    :param known: the option names of the build doing the migrating
    :return: the (name, value) to store instead, None when this name is not a rename
    """
    if key == "keep_upper" and "case_mode" in known:
        # forward migration: the old boolean picked between two of the new cases
        return "case_mode", (CASE_NONE if val else CASE_LOWER)
    if key == "case_mode" and "keep_upper" in known:
        # reverse migration: this build has not gained case_mode yet, so it
        # answers with keep_upper, and only the lower/none split survives
        if val in (CASE_UPPER, CASE_CAMEL):
            sys.stderr.write(f"Warning, lossy reverse migration, new value '{val}' is not backwards compatible\n")
        return "keep_upper", val != CASE_LOWER
    return None


def _sanity_check() -> tuple[bool, bool]:
    """look at the config file without reading it

    :return: (first_run, writable), whether the file must be created and
             whether it can be written to at all
    """
    if CONFIG_PATH.exists():
        sys.stderr.write("Config file exists.\n")
        if os.access(CONFIG_PATH, os.W_OK):
            sys.stderr.write("The config file is writable.\n")
            return False, True
        sys.stderr.write("The config file is not writable.\n")
        return False, False
    return True, True


def _as_json(conf: Config) -> dict[str, object]:
    """the options of a Config as the file stores them, with hyphenated keys

    :param conf: the options to store
    :return: the JSON-ready mapping
    """
    return {name.replace('_', '-'): getattr(conf, name) for name in option_names()}


def _write(conf: Config) -> None:
    """store a Config in the config file

    :param conf: the options to store
    """
    with pathlib.Path.open(CONFIG_PATH, 'w') as fobj:
        json.dump(_as_json(conf), fobj)


def load() -> Config:
    """read the config file, creating it on a first run and updating it when
    the file holds options this build names differently, does not know or is
    missing

    :return: the options as this build understands them
    """
    conf = Config()
    first_run, writable = _sanity_check()
    names = option_names()

    if first_run:
        sys.stderr.write("No config found - populate it with the defaults.\n")
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        _write(conf)
        sys.stderr.write(f"Configuration has been written to `{CONFIG_PATH}'.\n")
        return conf

    sys.stderr.write(f"Opening config file `{CONFIG_PATH}'\n")
    try:
        with pathlib.Path.open(CONFIG_PATH, 'r') as fobj:
            user_options = {key.replace('-', '_'): value
                            for key, value in json.load(fobj).items()}
    except json.JSONDecodeError:
        sys.stderr.write(f"Malformed configuration file `{CONFIG_PATH}'. Check json syntax.\n")
        return conf

    modified = False
    for key, val in user_options.items():
        if key in names:
            setattr(conf, key, val)
            continue
        migrated = migrate_option(key, val, names)
        if migrated is None:
            sys.stderr.write(f"Dropping unknown config option '{key}={val}'\n")
        else:
            name, value = migrated
            sys.stderr.write(f"Migration of config option: '{key}={val}' -> '{name}={value}'\n")
            setattr(conf, name, value)
        modified = True

    # a rewrite is also needed when the file is simply missing options this build
    # would store, even though every option it carries is one this build knows
    if modified or names - set(user_options):
        sys.stderr.write("Modifying config file.\n")
        if writable:
            _write(conf)
            sys.stderr.write(f"Modified configuration has been written to `{CONFIG_PATH}'.\n")
    return conf
