import json

from src.gui import TranscriberApp


def test_live_recording_writes_progressive_user_visible_files(tmp_path):
    app = object.__new__(TranscriberApp)
    app.transcript_data = [{"start": 0.0, "end": 2.0, "text": "Saved before Stop."}]
    app.backup_file = tmp_path / "recovery.json"
    app.active_recording_base = tmp_path / "Dictation_live"
    app.transcript_layout = "blocks"
    app.show_timestamps = True
    app.show_duration = False

    app._save_backup()

    assert "Saved before Stop." in (tmp_path / "Dictation_live.txt").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "Dictation_live.json").read_text(encoding="utf-8")) == app.transcript_data
    assert app.backup_file.exists()
