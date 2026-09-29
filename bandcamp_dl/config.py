import argparse
import ast
import json
import os
import pathlib
import sys

from bandcamp_dl import __version__

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
OPTION_MIGRATION_FORWARD = "forward"
OPTION_MIGRATION_REVERSE = "reverse"


class Config(dict):

    # TODO: change this to dataclass when support for Python < 3.7 is dropped
    _defaults = {"base_dir": str(USER_HOME),  # TODO: pass the Path object instead?
                 "template": TEMPLATE,
                 "overwrite": False,
                 "no_art": False,
                 "embed_art": False,
                 "embed_lyrics": False,
                 "group": False,
                 "no_slugify": False,
                 "ok_chars": OK_CHARS,
                 "space_char": SPACE_CHAR,
                 "ascii_only": False,
                 "keep_spaces": False,
                 "case_mode": CASE_LOWER,
                 "no_confirm": False,
                 "debug": False,
                 "embed_genres": False,
                 "cover_quality": 0,
                 "untitled_path_from_slug": False,
                 "truncate_album": 0,
                 "truncate_track": 0,
                 "limit_req_per_minute": 0}

    def __init__(self, dict_=None):
        if dict_ is None:
            super().__init__(**Config._defaults)
        else:
            super().__init__(**dict_)
        self.__dict__ = self
        self._read_write_config()

    def _read_write_config(self):
        if CONFIG_PATH.exists():
            with pathlib.Path.open(CONFIG_PATH, 'r+') as fobj:
                try:
                    user_config = json.load(fobj)
                    # change hyphen with underscore
                    user_config = {k.replace('-', '_'): v for k, v in user_config.items()}
                    # overwrite defaults with user provided config
                    if self._update_with_dict(user_config) or \
                      set(user_config.keys()).difference(set(self.keys())) :
                        # persist migrated options, removal of unsupported options, or missing
                        # options with their defaults
                        sys.stderr.write(f"Modified configuration has been written to "
                                         f"`{CONFIG_PATH}'.\n")
                        fobj.seek(0)  # r/w mode
                        fobj.truncate()  # r/w mode
                        json.dump({k: v for k, v in self.items()}, fobj)
                except json.JSONDecodeError:
                    # NOTE: we don't have logger yet
                    sys.stderr.write(f"Malformed configuration file `{CONFIG_PATH}'. Check json syntax.\n")
        else:
            # No config found - populate it with the defaults
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with pathlib.Path.open(CONFIG_PATH, mode="w") as fobj:
                conf = {k.replace('_', '-'): v for k, v in self.items()}
                json.dump(conf, fobj)
            sys.stderr.write(f"Configuration has been written to `{CONFIG_PATH}'.\n")

    def _update_with_dict(self, dict_):
        """update this config instance with the persisted key-value
           set, migrating or dropping any unknown options and returning
           true when the underlying config needs updating"""
        modified = False
        for key, val in dict_.items():
            if key not in self:
                modified = True
                if not self._migrate_option(key, val):
                    sys.stderr.write(f"Dropping unknown config option '{key}={val}'\n")
                continue
            self[key] = val

    def _migrate_option(self, key, val):
        """where supported, migrate legacy options and their values
           to update this config instance's new option, returning
           true / false to indicate whether or not this key was
           supported"""
        migration_type = migration_key = migration_val = None
        if key == "keep_upper":
            # forward migration
            migration_type = OPTION_MIGRATION_FORWARD
            migration_key = "case_mode"
            migration_val = self.case_mode = CASE_NONE if val else CASE_LOWER
        elif key == "case_mode":
            # reverse migration
            migration_type = OPTION_MIGRATION_REVERSE
            migration_key = "keep_upper"
            migration_val = self.keep_upper = False if val == CASE_LOWER else True
            if val in [CASE_UPPER, CASE_CAMEL]:
                sys.stderr.write(f"Warning, lossy reverse migration, new value '{val}' is not backwards compatible\n")
        if migration_type:
            sys.stderr.write(f"{migration_type.capitalize()} migration of config option: '{key}={val}' -> " \
                             f"'{migration_key}={migration_val}'\n")
            return True
        else:
            return False
