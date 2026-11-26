import json

from bandcamp_dl import config as config_module


def write_config(tmp_path, contents):
    path = tmp_path / "bandcamp-dl.json"
    path.write_text(json.dumps(contents), encoding="utf-8")
    return path


def test_an_old_file_gains_the_options_it_is_missing(tmp_path, monkeypatch, capsys):
    path = write_config(tmp_path, {"template": "%{album}"})
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    conf = config_module.Config()

    assert conf.template == "%{album}"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["truncate-album"] == 0
    assert written["limit-req-per-minute"] == 0
    assert "Modifying config file." in capsys.readouterr().err


def test_the_run_bookkeeping_attributes_never_reach_the_file(tmp_path, monkeypatch):
    path = write_config(tmp_path, {"template": "%{album}"})
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    config_module.Config()

    written = json.loads(path.read_text(encoding="utf-8"))
    assert "first-run" not in written and "touch" not in written


def test_a_config_that_needs_nothing_is_left_alone(tmp_path, monkeypatch, capsys):
    defaults = {key.replace('_', '-'): value
                for key, value in config_module.Config._defaults.items()}
    path = write_config(tmp_path, defaults)
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    config_module.Config()

    assert "Modifying config file." not in capsys.readouterr().err
    assert json.loads(path.read_text(encoding="utf-8")) == defaults


def test_a_legacy_option_is_migrated_into_the_file(tmp_path, monkeypatch):
    path = write_config(tmp_path, {"keep_upper": True})
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    conf = config_module.Config()

    assert conf.case_mode == config_module.CASE_NONE
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["case-mode"] == config_module.CASE_NONE
    assert "keep-upper" not in written
