import json
import os

from bandcamp_dl import config as config_module


def write_config(tmp_path, contents):
    path = tmp_path / "bandcamp-dl.json"
    path.write_text(contents if isinstance(contents, str) else json.dumps(contents),
                    encoding="utf-8")
    return path


def test_a_partial_config_is_a_partial_config(tmp_path, monkeypatch):
    # Config(dict_) skips the defaults entirely: only the given options exist, and they are
    # what gets written out on a first run
    path = tmp_path / "bandcamp-dl.json"
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    conf = config_module.Config({"template": "%{album}"})

    assert conf.template == "%{album}"
    assert "case_mode" not in conf
    assert json.loads(path.read_text(encoding="utf-8")) == {"template": "%{album}"}


def test_a_read_only_config_file_is_still_read(tmp_path, monkeypatch, capsys):
    path = write_config(tmp_path, {"template": "%{album}"})
    real_access = os.access

    def read_only(target, mode):
        return False if str(target) == str(path) else real_access(target, mode)

    monkeypatch.setattr(config_module, "CONFIG_PATH", path)
    monkeypatch.setattr(config_module.os, "access", read_only)

    conf = config_module.Config()

    assert conf.touch is False
    assert conf.template == "%{album}"
    assert "The config file is not writable." in capsys.readouterr().err
    assert json.loads(path.read_text(encoding="utf-8")) == {"template": "%{album}"}


def test_an_unknown_option_is_dropped_from_the_file(tmp_path, monkeypatch, capsys):
    path = write_config(tmp_path, {"template": "%{album}", "nonsense": 1})
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    config_module.Config()

    assert "Dropping unknown config option 'nonsense=1'" in capsys.readouterr().err
    assert "nonsense" not in json.loads(path.read_text(encoding="utf-8"))


def test_a_malformed_config_file_warns_but_keeps_the_defaults(tmp_path, monkeypatch, capsys):
    path = write_config(tmp_path, '{"template": "%{album}",,}')
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    conf = config_module.Config()

    assert "Malformed configuration file" in capsys.readouterr().err
    assert conf.template == config_module.TEMPLATE
    assert path.read_text(encoding="utf-8").startswith("{")


def test_a_legacy_case_mode_migrates_back_to_keep_upper(tmp_path, monkeypatch, capsys):
    # Someone who used a newer build wrote case_mode into a file an older build reads; the
    # lossy warning tells them the case choice they made does not survive going backwards
    path = write_config(tmp_path, {"case-mode": "upper"})
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    conf = config_module.Config({"template": "%{album}"})

    assert conf.keep_upper is True
    assert "lossy reverse migration" in capsys.readouterr().err
    assert json.loads(path.read_text(encoding="utf-8")) == {"template": "%{album}",
                                                           "keep-upper": True}


def test_a_reverse_migration_of_the_default_case_is_not_lossy(tmp_path, monkeypatch, capsys):
    path = write_config(tmp_path, {"case-mode": "lower"})
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    conf = config_module.Config({"template": "%{album}"})

    assert conf.keep_upper is False
    assert "lossy" not in capsys.readouterr().err
    assert json.loads(path.read_text(encoding="utf-8"))["keep-upper"] is False
