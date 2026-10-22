"""Exercise real Tk line clicks with isolated data and silent speech dispatch."""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import __version__  # noqa: E402
from src.gui import TranscriberApp  # noqa: E402
from src.hardware import detect_hardware  # noqa: E402
from src.history import HistoryStore  # noqa: E402
from src.settings import SettingsStore  # noqa: E402


class TestApp(TranscriberApp):
    def preload_selected_model(self):
        pass


def main():
    folder = ROOT / "artifacts" / ("gui-qa-" + __version__) / "click-speech"
    settings = SettingsStore(folder / "settings.json")
    settings.update({"ui_language": "fr", "preset": "universal", "check_updates": False,
        "speech_click": False, "speech_click_live": True, "translation_target": "fr",
        "translation_third": "en", "output_folder": str(folder / "outputs"),
        "window_geometry": "1320x990"}, save=True)
    app = TestApp(hardware=detect_hardware(), settings=settings, history=HistoryStore(folder / "history.sqlite3"))
    spoken, proof = [], {"success": False, "cases": []}
    app.speak_items = lambda items, **kwargs: spoken.append((items, kwargs))
    clock = [10000]

    def pump(seconds=.65):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            app.update()
            time.sleep(.01)

    def press(box, row, *, x_offset=0):
        widget = box._textbox
        widget.see(f"{row}.0")
        app.update_idletasks()
        bounds = widget.dlineinfo(f"{row}.0")
        assert bounds, (row, box.get("1.0", "end-1c"))
        x, y = max(8, bounds[0] + 10) + x_offset, bounds[1] + bounds[3] // 2
        clock[0] += 1000
        widget.event_generate("<ButtonPress-1>", x=x, y=y, time=clock[0], state=8 if sys.platform == "win32" else 16)
        return widget, x, y

    def click(box, row):
        widget, x, y = press(box, row)
        widget.event_generate("<ButtonRelease-1>", x=x, y=y, time=clock[0] + 20)
        pump()

    def verify():
        try:
            app.transcript_data = [{"start": 0, "end": 4, "source_text": "مرحبا بكم\nكيف حالكم؟",
                "source_language": "ar", "text": "Bonjour. " * 22, "target_language": "fr",
                "third_text": "Hello everyone.", "third_language": "en", "recognition_index": 85}]
            app.render_transcript()
            pump(.1)
            assert app.speech_click_var.get() and app.textbox._textbox.cget("state") == "disabled"
            assert app.textbox.winfo_height() >= 140
            proof["transcript_height"] = app.textbox.winfo_height()
            for code in ("ar", "fr", "en"):
                row, item = next((row, item) for row, item in app.textbox._speech_lines.items() if item[1] == code)
                # Embedded newlines and soft-wrap continuations resolve to the same utterance.
                click(app.textbox, row + (1 if code == "ar" else 0))
                assert spoken[-1] == ([item], {"follow_language": True, "replace": True})
            proof["cases"].append("main-original-translation-third-logical-unicode")
            app.open_audience()
            pump(.2)
            audience = app.audience_window
            assert audience.box._click_speech.enabled()
            for code in ("ar", "fr", "en"):
                label = next(label for label, value in audience.languages.items() if value == code)
                audience.picker.set(label)
                app._update_audience()
                click(audience.box, 1)
                assert spoken[-1][0][0][1] == code
            proof["cases"].append("audience-language-filter-and-logical-unicode")
            app.transcript_data.append({"start": 4, "end": 5, "text": "Hola", "language": "es"})
            app._update_audience()
            assert "es" in audience.languages.values()
            assert audience.languages[audience.picker.get()] == "en", "Keep the active filter when a new language arrives"
            app.transcript_data.pop()
            proof["cases"].append("audience-new-language-discovery-retains-active-filter")
            audience.destroy()
            app.lift()
            widget = app.textbox._textbox
            row = next(iter(app.textbox._speech_lines))
            for gesture in ("drag", "double", "scroll", "disable"):
                before = len(spoken)
                widget, x, y = press(app.textbox, row)
                if gesture == "drag":
                    widget.event_generate("<Motion>", x=x + 60, y=y, state=256)
                widget.event_generate("<ButtonRelease-1>", x=x + (60 if gesture == "drag" else 0), y=y, time=clock[0] + 20)
                if gesture == "double":
                    widget.event_generate("<ButtonPress-1>", x=x, y=y, time=clock[0] + 100)
                    widget.event_generate("<ButtonRelease-1>", x=x, y=y, time=clock[0] + 120)
                elif gesture == "scroll":
                    widget.event_generate("<MouseWheel>", x=x, y=y, delta=-120)
                elif gesture == "disable":
                    app.speech_click_var.set(False)
                pump()
                assert len(spoken) == before, gesture
                app.speech_click_var.set(True)
                widget.tag_remove("sel", "1.0", "end")
            proof["cases"].append("drag-double-click-scroll-and-disabled-cancel-speech")
            app.speech_click_var.set(False)
            app._click_speech_changed()
            for preset in ("files", "conference", "dictation", "link"):
                app.select_preset(preset)
                app.transcript_data = [{"start": 0, "end": 2, "text": "Bonjour.", "language": "fr"},
                    {"start": 2, "end": 4, "text": "Hello.", "language": "en"}]
                app.speech_click_var.set(True)
                app._click_speech_changed()
                for confidence in (False, True):
                    app.show_confidence_var.set(confidence)
                    for layout in ("blocks", "lines"):
                        app.transcript_layout = layout
                        app.render_transcript()
                        row, item = next((r, item) for r, item in app.textbox._speech_lines.items() if item[1] == "en")
                        click(app.textbox, row)
                        assert spoken[-1][0] == [item]
                        ranges = app.textbox._textbox.tag_ranges("confidence")
                        if ranges:
                            before = len(spoken)
                            click(app.textbox, int(str(ranges[0]).split(".")[0]))
                            assert len(spoken) == before
                proof["cases"].append(preset + "-confidence-and-layouts")
            app.speech_click_var.set(False)
            app._click_speech_changed()
            assert app.textbox._textbox.cget("state") == "normal"
            widget.delete("1.0", "1.end")
            widget.insert("1.0", "Texte corrigé.")
            app.speech_click_var.set(True)
            app._click_speech_changed()
            assert "Texte corrigé" in app.transcript_data[0]["text"]
            click(app.textbox, 1)
            assert "Texte corrigé" in spoken[-1][0][0][0]
            proof["cases"].append("editable-off-and-corrected-text-readback")
            proof.update(success=True, silent_dispatches=len(spoken))
        except Exception as error:
            proof["error"] = repr(error)
            proof["traceback"] = traceback.format_exc()
        finally:
            (folder / "report.json").write_text(json.dumps(proof, indent=2), "utf-8")
            app.on_close()

    app.after(1200, verify)
    app.mainloop()
    print(json.dumps(proof, indent=2))
    return 0 if proof["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
