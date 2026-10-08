"""Open the real desktop interface with isolated QA settings and history."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gui import TranscriberApp  # noqa: E402
from src.hardware import detect_hardware  # noqa: E402
from src.history import HistoryStore  # noqa: E402
from src.settings import SettingsStore  # noqa: E402
from src.utils import setup_logging  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--universal", action="store_true")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--no-preload", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--exit-after-check", action="store_true")
    args = parser.parse_args()
    setup_logging()
    folder = ROOT / "artifacts" / ("gui-qa-3.1" if args.universal else "gui-qa")
    settings = SettingsStore(folder / "settings.json")
    settings.update({"ui_language": "fr", "ui_mode": "advanced" if args.universal else "simple",
                     "preset": "universal" if args.universal else "files",
                     "model": "auto-multilingual" if args.universal else "auto-best",
                     "device": "auto", "spoken_language": "auto", "check_updates": False,
                     "translation_target": "fr", "conversation_partner": "auto", "translation_third": "en",
                     "window_geometry": "1320x990", "output_folder": str(folder / "Transcriptions")}, save=True)
    class PreviewApp(TranscriberApp):
        def preload_selected_model(self):
            if not args.no_preload:
                super().preload_selected_model()

    app = PreviewApp(hardware=detect_hardware(), settings=settings,
                         history=HistoryStore(folder / "history.sqlite3"))
    if args.demo:
        app.title("Local Transcriber Pro 3.1.0 • Démonstration")
        app.transcript_data = [
            {"start": 0, "end": 4, "source_language": "ar", "source_text": "أنا أحتاج إلى مساعدة في العثور على سكن.",
             "target_language": "fr", "text": "J’ai besoin d’aide pour trouver un logement.",
             "recognition_index": 86, "translation_index": 78, "language_probability": 0.97,
             "third_language": "en", "third_text": "I need help finding housing.", "conversation_pair": ["ar", "fr"]},
            {"start": 5, "end": 9, "source_language": "fr",
             "source_text": "Je comprends. Nous allons chercher une solution ensemble.",
             "target_language": "ar", "text": "أفهم. سنبحث عن حل معاً.", "third_language": "en",
             "recognition_index": 90, "translation_index": 82, "language_probability": 0.99,
             "third_text": "I understand. We will look for a solution together.", "conversation_pair": ["ar", "fr"]},
        ]
        app.translation_controls.update_pair(["ar", "fr"])
        app.render_transcript()
        app._set_status("Démonstration · exemples illustratifs · aucune conversation réelle affichée")
    if args.self_check:
        def verify():
            proof = {"demo": args.demo, "initial_height": app.textbox.winfo_height()}
            try:
                original = json.dumps(app.transcript_data, ensure_ascii=False)
                app.textbox._textbox.tag_add("sel", "1.0", "3.0")
                selected = app.selected_speech_lines()
                assert selected[0][0] == app.transcript_data[0]["source_text"]
                assert selected[0][1] == "ar" and selected[1][1] == "fr"
                app.textbox._textbox.tag_remove("sel", "1.0", "end")
                app._commit_editor_changes()
                assert json.dumps(app.transcript_data, ensure_ascii=False) == original
                copied = []
                app.clipboard_clear = lambda: None
                app.clipboard_append = copied.append
                app.copy_transcript()
                assert "أنا أحتاج" in copied[0] and "J’ai besoin" in copied[0]
                app.event_generate("<F11>")
                app.update_idletasks()
                assert app.reading_view
                proof["reading_height"] = app.textbox.winfo_height()
                assert proof["reading_height"] > proof["initial_height"]
                assert app.winfo_width() < app.winfo_screenwidth() or app.winfo_screenwidth() <= 3840
                app.event_generate("<Escape>")
                assert not app.reading_view
                app.change_transcript_font(30)
                assert app.conversation_font_size == 48
                app.change_transcript_font(-100)
                assert app.conversation_font_size == 14
                app.change_transcript_font(8)
                app.show_confidence_var.set(False)
                app.render_transcript()
                assert not app.textbox._textbox.tag_ranges("confidence")
                app.show_confidence_var.set(True)
                app.render_transcript()
                bilingual_data = app.transcript_data
                app.transcript_data = [
                    {"start": 0, "end": 2, "text": "Bonjour.", "recognition_index": 88},
                    {"start": 2, "end": 4, "text": "Comment allez-vous ?", "recognition_index": 81},
                ]
                app.render_transcript()
                plain_data = json.dumps(app.transcript_data)
                assert "88/100" not in app._editor_text()
                app._commit_editor_changes()
                assert json.dumps(app.transcript_data) == plain_data
                app.show_confidence_var.set(False)
                app._confidence_changed()
                assert json.dumps(app.transcript_data) == plain_data
                app.show_confidence_var.set(True)
                app._confidence_changed()
                assert json.dumps(app.transcript_data) == plain_data
                app.transcript_data = bilingual_data
                app.render_transcript()
                proof["plain_editor_confidence"] = True
                proof["passed"] = True
            except Exception as error:
                proof["passed"] = False
                proof["error"] = repr(error)
            (folder / "self-check.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
            app._set_status("Démonstration · exemples illustratifs · aucune conversation réelle affichée")
            app.textbox.yview_moveto(0)
            if args.exit_after_check:
                app.after(100, app.on_close)
        app.after(1100, verify)
    app.mainloop()
