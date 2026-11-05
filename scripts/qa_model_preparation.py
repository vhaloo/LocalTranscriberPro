"""Real Tk regression checks and isolated release demonstration scenes."""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import __version__  # noqa: E402
from src.gui import ModelSelectorDialog, TranscriberApp  # noqa: E402
from src.hardware import HardwareProfile  # noqa: E402
from src.history import HistoryStore  # noqa: E402
from src.settings import SettingsStore  # noqa: E402
from src.transcriber import TranscriberEngine  # noqa: E402


class QuietApp(TranscriberApp):
    def _start_microphone_monitor(self):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", choices=("files", "universal", "models", "memory", "audience", "settings"))
    args = parser.parse_args()
    folder = ROOT / "artifacts" / ("gui-qa-" + __version__) / ("models-" + (args.demo or "checks"))
    store = SettingsStore(folder / "settings.json")
    store.update(dict(ui_language="fr", preset="files", model="auto-best", device="auto", ui_mode="simple",
        check_updates=False, show_confidence=False, output_folder=str(folder / "outputs"),
        translation_target="fr", translation_third="en", window_geometry="1320x990"), save=True)
    hardware = HardwareProfile("Windows", "11", "AMD64", "CPU de démonstration", 4,
                               4 if args.demo == "memory" else 32,
                               available_ram_gb=0.8 if args.demo == "memory" else 16)
    hardware.refresh_resources = lambda: None
    engine = TranscriberEngine(hardware)
    if not args.demo:
        engine.model_cache = folder / "models"
        engine.cache_roots = lambda: [engine.model_cache]
        engine.omnilingual_cache_root = folder / "omnilingual"
    loads = []
    def forbidden_load(*values, **_kwargs):
        loads.append(values)
        raise AssertionError("Navigation must not start a download")
    engine.load_model = forbidden_load
    app = QuietApp(hardware=hardware, engine=engine, settings=store,
                   history=HistoryStore(folder / "history.sqlite3"))
    errors, layouts = [], []
    app.report_callback_exception = lambda *values: errors.append("".join(traceback.format_exception(*values)))

    def pump(seconds=0.12):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            app.update()
            time.sleep(0.01)

    if args.demo:
        app.title(f"Local Transcriber Pro {__version__} · Démonstration {args.demo}")
        app.select_preset("files" if args.demo in {"files", "models", "memory", "settings"} else "universal")
        if args.demo in {"universal", "audience"}:
            app.transcript_data = [dict(start=0, end=4, text="Bonjour, comment puis-je vous aider ?",
                source_text="مرحباً، كيف يمكنني مساعدتك؟", source_language="ar", target_language="fr",
                third_text="Hello, how can I help you?", third_language="en"),
                dict(start=4, end=8, text="أحتاج إلى معلومات حول موعدي.",
                source_text="J’ai besoin d’informations concernant mon rendez-vous.", source_language="fr", target_language="ar",
                third_text="I need information about my appointment.", third_language="en")]
            app.render_transcript()
        if args.demo in {"models", "memory"}:
            app.demo_dialog = ModelSelectorDialog(app)
            app.demo_dialog.title(f"Modèles · {__version__} · {args.demo}")
            if args.demo == "models":
                def show_selected_checkpoint():
                    canvas = app.demo_dialog.scroll._parent_canvas
                    region = canvas.bbox("all")
                    row = app.demo_dialog.model_rows["large-v3"]
                    if region:
                        canvas.yview_moveto(max(0, row.winfo_y() - 150) / region[3])
                app.after(450, show_selected_checkpoint)
        elif args.demo == "settings":
            app.open_workspace_settings()
        elif args.demo == "audience":
            app.open_audience()
        app.after(120000, app.on_close)
        print(json.dumps({"demo_ready": args.demo, "version": __version__, "hardware_simulation": True}), flush=True)
        app.mainloop()
        return

    try:
        pump(1.0)
        assert not loads and not app.model_preloading
        assert app.prepare_model_button.winfo_ismapped()
        for width, height in ((1320, 990), (1024, 768)):
            app.geometry(f"{width}x{height}")
            for preset in ("files", "universal", "conference", "dictation", "link"):
                app.select_preset(preset)
                pump()
                assert not loads and not app.model_preloading
                assert app.prepare_model_button.winfo_ismapped()
                assert app.textbox.winfo_height() >= (200 if height == 768 else 400)
                layouts.append(dict(width=width, height=height, preset=preset,
                                    transcript_height=app.textbox.winfo_height()))
        app._select_model("tiny")
        app._select_model("auto-best")
        app.hardware.ram_gb, app.hardware.available_ram_gb = 4, 0.8
        app.preload_selected_model()
        pump()
        assert "large-v3" in app.simple_auto_summary_label.cget("text")
        assert "virtuelle" in app.simple_auto_summary_label.cget("text")
        dialog = ModelSelectorDialog(app)
        pump()
        import src.cpu_worker as workers
        import src.gui as gui
        original_worker, original_question = workers.CPUWorkerClient, gui.messagebox.askyesno
        downloads = []
        class DownloadFixture:
            def call(self, operation, payload, **_kwargs):
                downloads.append((operation, payload["model"]))
                model = engine.model_cache / "models--Systran--faster-whisper-tiny" / "snapshots" / "test"
                model.mkdir(parents=True, exist_ok=True)
                for name in ("model.bin", "config.json", "tokenizer.json"):
                    (model / name).write_text("test fixture, not inference weights")
                return {"model": "tiny", "path": str(model)}
            def close(self):
                pass
        try:
            workers.CPUWorkerClient = DownloadFixture
            gui.messagebox.askyesno = lambda *_args, **_kwargs: True
            dialog.download("tiny")
            deadline = time.monotonic() + 10
            while app.__dict__.get("model_download_cancel") is not None:
                assert time.monotonic() < deadline
                pump()
            pump()
            assert "tiny" in engine.cached_model_ids()
            assert downloads == [("download_model", "tiny")]
            dialog.delete_model("tiny")
            assert "tiny" not in engine.cached_model_ids()
            assert not (engine.model_cache / "models--Systran--faster-whisper-tiny").exists()
            dialog.download("tiny")
            deadline = time.monotonic() + 10
            while app.__dict__.get("model_download_cancel") is not None:
                assert time.monotonic() < deadline
                pump()
            pump()
            assert "tiny" in engine.cached_model_ids() and len(downloads) == 2
            dialog.delete_model("tiny")
            assert "tiny" not in engine.cached_model_ids()
            assert not loads
        finally:
            workers.CPUWorkerClient, gui.messagebox.askyesno = original_worker, original_question
        dialog.destroy()
        assert not loads and not errors
        proof = dict(success=True, version=__version__, startup_and_navigation_loads=len(loads),
                     low_memory_summary="large-v3 · CPU — mémoire virtuelle", layouts=layouts,
                     catalogue_download_delete_cycle=downloads, callback_errors=errors)
        (folder / "proof.json").write_text(json.dumps(proof, indent=2), "utf-8")
        print(json.dumps(proof), flush=True)
    finally:
        app.on_close()


if __name__ == "__main__":
    main()
