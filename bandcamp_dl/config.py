import argparse
import ast
import json
import logging
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
                 "retag": False,
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
                 "limit_req_per_minute": 0,
                 "progress": "auto"}

    def __init__(self, dict_=None):
        if dict_ is None:
            super().__init__(**Config._defaults)
        else:
            super().__init__(**dict_)
        self.__dict__ = self
        self.first_run = True
        self._read_write_config()

    def _sanity_check(self):
        if CONFIG_PATH.exists():
            sys.stderr.write("Config dir exists.\n")
            if os.access(CONFIG_PATH, os.W_OK):
                sys.stderr.write("The config file is writable.\n")
                self.first_run = False
                self.touch = True
            else:
                sys.stderr.write("The config file is not writable.\n")
                self.first_run = False
                self.touch = False
        else:
            self.first_run = True
            self.touch = True

    def _read_write_config(self):
        self._sanity_check()
        if self.touch:
            file_mode = 'r+'
        else:
            file_mode = 'r'

        if self.first_run:
            sys.stderr.write("No config found - populate it with the defaults.\n")
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with pathlib.Path.open(CONFIG_PATH, mode="w") as fobj:
                json.dump(self._as_json(), fobj)
            sys.stderr.write(f"Configuration has been written to `{CONFIG_PATH}'.\n")
        else:
            sys.stderr.write(f"Opening config file `{CONFIG_PATH}` as {file_mode}\n")
            with pathlib.Path.open(CONFIG_PATH, file_mode) as fobj:
                try:
                    user_config = json.load(fobj)
                    # change hyphen with underscore
                    user_config = {k.replace('-', '_'): v for k, v in user_config.items()}
                    if self._update_with_dict(user_config) or \
                            set(user_config.keys()).difference(set(self.keys())) or \
                            set(self._defaults).difference(set(user_config.keys())):
                        # overwrite defaults with user provided config
                        sys.stderr.write("Modifying config file.\n")
                        # persist migrated options, removal of unsupported options, or missing
                        # options with their defaults
                        if self.touch:
                            sys.stderr.write(f"Modified configuration has been written to "
                                                f"`{CONFIG_PATH}'.\n")
                            fobj.seek(0)  # r/w mode
                            fobj.truncate()  # r/w mode
                            json.dump(self._as_json(), fobj)
                except json.JSONDecodeError:
                    sys.stderr.write(f"Malformed configuration file `{CONFIG_PATH}'. Check json syntax.\n")

    def _as_json(self):
        """the config options as they are stored in the file, with hyphenated keys

           this class maps its own __dict__ onto itself, so the run bookkeeping attributes
           (first_run / touch) sit in the same dict as the options and must not be written out
           as if they were settings"""
        return {k.replace('_', '-'): v for k, v in self.items()
                if k not in ('first_run', 'touch')}

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
        return modified

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
