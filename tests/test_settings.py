import json

from src.settings import SettingsStore, ensure_output_folder


def test_output_folder_is_created_inside_user_owned_location(tmp_path):
    target = tmp_path / "Documents" / "Transcriptions"
    assert ensure_output_folder(target) == target
    assert target.is_dir()


def test_settings_migrate_old_window_and_keep_new_format_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"schema_version": 3, "window_geometry": "1180x860"}),
        encoding="utf-8",
    )

    settings = SettingsStore(path)

    assert settings.get("schema_version") == 4
    assert settings.get("window_geometry") == "1220x940"
    assert settings.get("transcript_layout") == "blocks"
