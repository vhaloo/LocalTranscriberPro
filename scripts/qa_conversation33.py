"""Real Tk integration checks against isolated illustrative session data."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gui import TranscriberApp  # noqa: E402
from src.hardware import detect_hardware  # noqa: E402
from src.history import HistoryStore  # noqa: E402
from src.review import correct_segment  # noqa: E402
from src.session import identified  # noqa: E402
from src.settings import SettingsStore  # noqa: E402


class TestApp(TranscriberApp):
    def preload_selected_model(self):
        pass


folder = ROOT / "artifacts/gui-qa-3.3.0/workbench"
settings = SettingsStore(folder / "settings.json")
settings.update({"ui_language": "fr", "preset": "universal", "check_updates": False,
                 "translation_target": "fr", "conversation_partner": "auto", "translation_third": "none",
                 "output_folder": str(folder / "outputs"), "window_geometry": "1320x990"}, save=True)
app = TestApp(hardware=detect_hardware(), settings=settings, history=HistoryStore(folder / "history.sqlite3"))


def verify():
    report = {"success": False}
    try:
        app.transcript_data = identified([{"start": 0, "end": 2, "source_language": "ar", "source_text": "مرحبا بكم",
                                         "target_language": "fr", "text": "Bonjour", "third_language": "en", "third_text": "Hello"}])
        app.render_transcript()
        app.update_idletasks()
        assert app.textbox.winfo_height() >= 150, app.textbox.winfo_height()
        report["normal_transcript_height"] = app.textbox.winfo_height()
        app.open_audience()
        app.update_idletasks()
        assert "Bonjour" in app.audience_window.box.get("1.0", "end-1c")
        app.audience_window.picker.set("Français · fr")
        app._update_audience()
        app.audience_window.destroy()
        item = correct_segment(app.transcript_data[0], "مرحبا بكم", "Bienvenue")
        app._apply_review(item)
        assert app.transcript_data[0]["text"] == "Bienvenue"
        app._replace_segments([dict(item, text="stale worker text", revisions=[])])
        assert app.transcript_data[0]["text"] == "Bienvenue"
        app.recorder.recording = True
        app.translation_changed("conversation_partner", "ar")
        assert app.session_controller.language_command(0)[1] == ("fr", "ar", None)
        app.recorder.recording = False
        app.active_recording_base = folder / "outputs/last-reviewed"
        app._finish_recording(None, "integration-test")
        assert app.active_recording_base is None
        assert "Bienvenue" in (folder / "outputs/last-reviewed.json").read_text("utf-8")
        app.private_mode = True
        app.backup_file = folder / "private-must-not-exist.json"
        app._save_backup()
        assert not app.backup_file.exists()
        assert app.save_result_bundle(app.transcript_data, "private-must-not-exist") is None
        report.update(success=True, audience=True, review_survives_worker=True, live_language_command=True, private_no_autosave=True)
    except Exception as error:
        report["error"] = repr(error)
    finally:
        app.recorder.recording = False
        (folder / "report.json").write_text(json.dumps(report, indent=2), "utf-8")
        app.on_close()


app.after(900, verify)
app.mainloop()
