import json
import os

from bandcamp_dl import config as config_module


def write_config(tmp_path, contents):
    path = tmp_path / "bandcamp-dl.json"
    path.write_text(contents if isinstance(contents, str) else json.dumps(contents),
                    encoding="utf-8")
    return path


def test_a_read_only_config_file_is_still_read(tmp_path, monkeypatch, capsys):
    path = write_config(tmp_path, {"template": "%{album}"})
    real_access = os.access

    def read_only(target, mode):
        return False if str(target) == str(path) else real_access(target, mode)

    monkeypatch.setattr(config_module, "CONFIG_PATH", path)
    monkeypatch.setattr(config_module.os, "access", read_only)

    conf = config_module.load()

    assert conf.template == "%{album}"
    assert "The config file is not writable." in capsys.readouterr().err
    # the file needs updating and is left exactly as it stands, not truncated
    assert json.loads(path.read_text(encoding="utf-8")) == {"template": "%{album}"}


def test_an_unknown_option_is_dropped_from_the_file(tmp_path, monkeypatch, capsys):
    path = write_config(tmp_path, {"template": "%{album}", "nonsense": 1})
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    config_module.load()

    assert "Dropping unknown config option 'nonsense=1'" in capsys.readouterr().err
    assert "nonsense" not in json.loads(path.read_text(encoding="utf-8"))


def test_a_malformed_config_file_warns_but_keeps_the_defaults(tmp_path, monkeypatch, capsys):
    path = write_config(tmp_path, '{"template": "%{album}",,}')
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    conf = config_module.load()

    assert "Malformed configuration file" in capsys.readouterr().err
    assert conf.template == config_module.TEMPLATE
    assert path.read_text(encoding="utf-8").startswith("{")


def test_a_forward_migration_replaces_the_old_boolean():
    names = config_module.option_names()

    assert config_module.migrate_option("keep_upper", True, names) == (
        "case_mode", config_module.CASE_NONE)
    assert config_module.migrate_option("keep_upper", False, names) == (
        "case_mode", config_module.CASE_LOWER)


def test_a_reverse_migration_answers_in_the_older_vocabulary(capsys):
    # a build that has not gained case_mode yet reads a file written by one that has;
    # the case choice it does not know cannot survive going backwards
    older_build = {"keep_upper"}

    assert config_module.migrate_option("case_mode", "upper", older_build) == ("keep_upper", True)
    assert "lossy reverse migration" in capsys.readouterr().err


def test_a_reverse_migration_of_the_default_case_is_not_lossy(capsys):
    assert config_module.migrate_option("case_mode", "lower", {"keep_upper"}) == ("keep_upper", False)
    assert "lossy" not in capsys.readouterr().err


def test_an_option_that_is_not_a_rename_is_not_migrated():
    assert config_module.migrate_option("nonsense", 1, config_module.option_names()) is None
