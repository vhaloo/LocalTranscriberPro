"""Exercise the real workspace with isolated data and no microphone or model load."""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import __version__  # noqa: E402
from src.gui import TranscriberApp  # noqa: E402
from src.hardware import HardwareProfile  # noqa: E402
from src.history import HistoryStore  # noqa: E402
from src.settings import SettingsStore  # noqa: E402


class WorkspaceApp(TranscriberApp):
    def preload_selected_model(self):
        pass

    def _start_microphone_monitor(self):
        pass


def main():
    folder = ROOT / "artifacts" / ("gui-qa-" + __version__) / "workspace"
    store = SettingsStore(folder / "settings.json")
    store.update(
        {
            "preset": "files",
            "model": "auto-best",
            "ui_language": "fr",
            "ui_mode": "simple",
            "check_updates": False,
            "window_geometry": "1320x990",
            "show_confidence": False,
            "output_folder": str(folder / "outputs"),
            "translation_target": "fr",
            "translation_third": "en",
        },
        save=True,
    )
    hardware = HardwareProfile("Test", "", "", "CPU", 8, 32, available_ram_gb=16)
    app = WorkspaceApp(hardware=hardware, settings=store, history=HistoryStore(folder / "history.sqlite3"))
    errors, proof = [], {"success": False, "layouts": [], "cases": []}
    app.report_callback_exception = lambda *values: errors.append(
        "".join(traceback.format_exception(*values))
    )

    def pump(seconds=0.12):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            app.update()
            time.sleep(0.01)

    try:
        app.transcript_data = []
        app.render_transcript()
        pump(0.4)
        assert app.empty_state.winfo_ismapped() and not app._editor_text().strip()
        assert app.settings_window.state() == "withdrawn"
        proof["cases"].append("empty-guide-is-not-transcript-and-settings-start-closed")
        for width, height in ((1320, 990), (1024, 768)):
            app.geometry(f"{width}x{height}")
            for task in ("files", "universal", "conference", "dictation", "link"):
                app.select_preset(task)
                pump()
                active = (
                    app.file_controls
                    if task == "files"
                    else app.link_controls
                    if task == "link"
                    else app.record_controls
                )
                assert active.winfo_ismapped()
                assert bool(app.microphone_panel.winfo_ismapped()) == (
                    task in {"universal", "conference", "dictation"}
                )
                metrics = {
                    "width": app.winfo_width(),
                    "height": app.winfo_height(),
                    "task": task,
                    "transcript_height": app.textbox.winfo_height(),
                    "source_height": app.source_card.winfo_height(),
                    "output_height": app.output_card.winfo_height(),
                    "header_height": app.header_frame.winfo_height(),
                }
                if metrics["transcript_height"] < 120:

                    def collect(widget, level=0):
                        values = []
                        if level < 4:
                            for child in widget.winfo_children():
                                if child.winfo_class() == "Frame":
                                    values.append(
                                        {
                                            "widget": str(child),
                                            "h": child.winfo_height(),
                                            "rh": child.winfo_reqheight(),
                                            "mapped": child.winfo_ismapped(),
                                            "grid": str(child.grid_info()),
                                            "children": collect(child, level + 1),
                                        }
                                    )
                        return values

                    proof["layout_details"] = collect(app.output_card)
                    raise AssertionError(metrics)
                assert (
                    app.export_menu.winfo_rootx() + app.export_menu.winfo_width()
                    <= app.winfo_rootx() + app.winfo_width()
                ), metrics
                proof["layouts"].append(metrics)
                if task == "universal":
                    assert app.selected_model_id == "auto-best"
        proof["cases"].append("all-tasks-and-compact-screens-retain-transcript-and-actions")
        app.geometry("1320x990")
        app.open_workspace_settings()
        pump()
        assert app.settings_window.winfo_viewable() and app.model_button.winfo_exists()
        assert app.device_combo.winfo_exists() and app.layout_combo.winfo_exists()
        app.chunk_var.set('invalid')
        app.beam_var.set('999')
        app.close_workspace_settings()
        assert app.chunk_var.get().isdigit() and app.beam_var.get() == '10'
        app.beam_var.set('8')
        proof["cases"].append("recognition-voice-and-storage-settings-retained")
        app.transcript_data = [{"start": 0, "end": 2, "text": "Bonjour a.b. Bonjour aXb.", "language": "fr"}]
        app.show_confidence_var.set(False)
        app.render_transcript()
        pump()
        assert not app.empty_state.winfo_ismapped()
        search = app.transcript_search
        search.show()
        search.query.insert(0, "bonjour")
        search.refresh()
        assert len(search.matches) == 2
        search.move(1)
        selected = search.current
        search.schedule(SimpleNamespace(keysym="Return"))
        search.refresh()
        assert search.current == selected
        search.query.delete(0, "end")
        search.query.insert(0, "a.b")
        search.refresh()
        assert len(search.matches) == 1
        assert app.transcript_data[0]["text"] == "Bonjour a.b. Bonjour aXb."
        search.hide()
        proof["cases"].append("literal-search-navigation-and-refresh-preserve-text-and-current-match")
        app.transcript_data[0]["text"] = "Bonjour " * 1200
        app.render_transcript()
        search.show()
        search.query.delete(0, "end")
        search.query.insert(0, "Bonjour")
        search.refresh()
        assert len(search.matches) == 1000 and search.count.cget("text").endswith("1000+")
        search.hide()
        proof["cases"].append("large-transcript-search-is-bounded")
        app.transcript_data = [
            {
                "start": 0,
                "end": 4,
                "source_text": "أنا أحتاج إلى مساعدة في العثور على سكن.",
                "source_language": "ar",
                "text": "J’ai besoin d’aide pour trouver un logement.",
                "target_language": "fr",
                "third_text": "I need help finding housing.",
                "third_language": "en",
            }
        ]
        app.render_transcript()
        search.show()
        search.query.delete(0, "end")
        search.query.insert(0, "سكن")
        search.refresh()
        assert search.matches
        app._escape_action()
        assert not search.visible and not app.reading_view
        proof["cases"].append("logical-arabic-search-and-escape")
        old_height = app.textbox.winfo_height()
        app.toggle_reading_view()
        pump()
        assert app.reading_view and app.textbox.winfo_height() > old_height
        app._escape_action()
        pump()
        assert not app.reading_view and app.sidebar.winfo_ismapped()
        proof["cases"].append("reading-view-restores-sidebar-and-controls")
        app.open_audience()
        pump()
        original = json.dumps(app.transcript_data)
        app.toggle_language()
        pump(0.4)
        assert app.audience_window and app.audience_window.winfo_exists()
        assert json.dumps(app.transcript_data) == original
        assert app.settings_window.state() == "withdrawn"
        proof["cases"].append("language-rebuild-retains-conversation-and-audience")
        assert not errors, errors
        proof["success"] = True
    except Exception:
        proof["error"] = traceback.format_exc()
        raise
    finally:
        proof["callback_errors"] = errors
        (folder / "report.json").write_text(json.dumps(proof, indent=2), "utf-8")
        app.stop_speaking()
        app.running, app.closing = False, True
        app.recorder.stop_monitor()
        app.destroy()
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
