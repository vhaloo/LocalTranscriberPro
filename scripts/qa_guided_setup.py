"""Real Tk setup/settings regressions, isolated files and a simulated microphone."""
from __future__ import annotations

import copy
import json
import sys
import time
import traceback
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import customtkinter as ctk  # noqa: E402

from src import __version__  # noqa: E402
from src.audio import AudioRecorder  # noqa: E402
from src.gui import TranscriberApp  # noqa: E402
from src.hardware import HardwareProfile  # noqa: E402
from src.history import HistoryStore  # noqa: E402
from src.settings import SettingsStore  # noqa: E402
from src.speech_output import LocalSpeechOutput  # noqa: E402
from src.tooltip import ToolTip  # noqa: E402
from src.transcriber import TranscriberEngine  # noqa: E402


class QuietApp(TranscriberApp):
    def _start_microphone_monitor(self):
        pass


def walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from walk(child)


def main():
    folder = ROOT / "artifacts" / ("gui-qa-" + __version__) / "guided-setup"
    folder.mkdir(parents=True, exist_ok=True)
    settings = SettingsStore(folder / "settings.json")
    settings.update(dict(ui_language="fr", ui_mode="advanced", preset="files", model="small", device="cpu-virtual",
        beam_size=3, chunk_seconds=45, check_updates=False, output_folder=str(folder / "outputs"),
        conversation_partner="auto", translation_target="fr", window_geometry="1320x990"), save=True)
    hardware = HardwareProfile("Windows", "11", "AMD64", "Validation CPU", 8, 32, available_ram_gb=16)
    hardware.refresh_resources = lambda: None
    calls, errors, checks = [], [], []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("A setup/settings operation attempted inference or recording")
    def monitor(recorder, index=None):
        recorder.monitoring, recorder.current_amplitude = True, 0.12
        calls.append(("explicit-level-test", index))
        return True

    with patch("src.transcriber.user_cache_dir", lambda *_: str(folder / "cache")), \
         patch("src.speech_output_ui.LocalSpeechOutput", lambda: LocalSpeechOutput(folder / "voices")), \
         patch.object(AudioRecorder, "get_devices", lambda *_: (["2: Simulated microphone"], "2: Simulated microphone")), \
         patch.object(AudioRecorder, "start", forbidden), patch.object(AudioRecorder, "start_monitor", monitor):
        engine = TranscriberEngine(hardware)
        engine.cache_roots = lambda: [engine.model_cache]
        engine.load_model = forbidden
        app = QuietApp(hardware=hardware, engine=engine, settings=settings, history=HistoryStore(folder / "history.sqlite3"),
                       show_onboarding=False)
        app.report_callback_exception = lambda *values: errors.append("".join(traceback.format_exception(*values)))
        app.tk.createcommand("bgerror", lambda message: errors.append("Tcl: "+message))
        def pump(seconds=0.15):
            end = time.monotonic()+seconds
            while time.monotonic() < end:
                app.update()
                time.sleep(0.01)
        proof = {"success": False, "version": __version__}
        try:
            app.transcript_data = [dict(start=0, end=3, text="Bonjour, bienvenue.", source_text="مرحباً",
                                       source_language="ar", target_language="fr")]
            original = copy.deepcopy(app.transcript_data)
            app.render_transcript()
            pump(0.4)
            before = (app.selected_model_id, app.selected_device, app.chunk_var.get(), app.beam_var.get())
            app.toggle_mode()
            pump()
            assert before == (app.selected_model_id, app.selected_device, app.chunk_var.get(), app.beam_var.get())
            checks.append("presentation-switch-keeps-model-processor-and-tuning")
            app.open_workspace_settings()
            help_count = 0
            for key in app.settings_pages:
                app.settings_tabs.set(app.t(key))
                pump()
                fields = [widget for widget in walk(app.settings_pages[key]) if isinstance(widget,
                          (ctk.CTkSwitch, ctk.CTkCheckBox, ctk.CTkButton, ctk.CTkComboBox, ctk.CTkEntry, ctk.CTkOptionMenu))]
                missing = [str(widget) for widget in fields if not getattr(widget, "_ltp_tooltip", None)]
                assert not missing, (key, missing)
                help_count += len(fields)
            app.close_workspace_settings()
            checks.append("all-core-settings-controls-have-contextual-help")
            app.offline_prepare()
            pump()
            translation = next(window for window in app.winfo_children() if isinstance(window, ctk.CTkToplevel)
                               and window.title() == app.t("offline_prepare"))
            controls = list(walk(translation))
            picker = next(widget for widget in controls if isinstance(widget, ctk.CTkOptionMenu))
            picker.set(next(value for value in picker.cget("values") if "7B" in value))
            save = next(widget for widget in controls if isinstance(widget, ctk.CTkButton)
                        and widget.cget("text") == app.t("translation_save"))
            save._clicked()
            pump()
            assert settings.get("translation_model") == "madlad400-7b" and not calls
            translation.destroy()
            pump()
            checks.append("translation-preferences-save-without-loading-or-downloading")
            app.setup_button._ltp_tooltip.help_key()
            pump()
            first = ToolTip.active
            assert first and first.tooltip_window.winfo_exists()
            app.quality_control._ltp_tooltip.help_key()
            pump()
            assert ToolTip.active is app.quality_control._ltp_tooltip and first.tooltip_window is None
            assert ToolTip.active.escape() == "break" and ToolTip.active is None
            checks.append("context-help-single-popup-and-keyboard-dismissal")
            app.persist_settings()
            snapshot = settings.path.read_bytes()
            wizard = app.open_guided_setup()
            pump()
            wizard.answers.preset = "universal"
            wizard.answers.partner, wizard.answers.target, wizard.answers.third = "ar", "fr", "en"
            wizard.navigate(1)
            pump()
            assert not calls, calls
            wizard.toggle_microphone_test()
            pump()
            assert wizard.microphone_test.monitoring and not wizard.microphone_test.recording
            wizard.navigate(1)
            pump()
            assert wizard.microphone_test is None
            wizard.answers.profile = "fast"
            wizard.navigate(1)
            pump()
            wizard.navigate(-1)
            assert wizard.answers.profile == "fast" and wizard.answers.partner == "ar"
            wizard.destroy()
            pump()
            assert settings.path.read_bytes() == snapshot and app.transcript_data == original
            checks.append("wizard-back-and-cancel-preserve-settings-and-text")
            checks.append("microphone-level-test-is-explicit-and-releases-on-navigation")
            calls.clear()
            wizard = app.open_guided_setup()
            pump()
            wizard.answers.preset = "universal"
            wizard.answers.profile = "coverage"
            wizard.answers.ui_language = "en"
            wizard.answers.target, wizard.answers.partner, wizard.answers.third = "fr", "ar", "en"
            wizard.answers.spoken_language = "auto"
            wizard.answers.click_speech = True
            wizard.answers.chunk_seconds = 12
            wizard.answers.font_size = 30
            wizard.step = 3
            wizard.render_step()
            pump()
            app.busy = True
            with patch("tkinter.messagebox.showinfo"):
                assert wizard.apply() is False
            app.busy = False
            assert settings.path.read_bytes() == snapshot
            wizard.next_button._clicked()
            pump(0.5)
            assert app.selected_model_id == "auto-multilingual" and app.selected_device == "auto"
            assert app.preset == "universal" and app.translation_target == "fr" and app.conversation_partner == "ar"
            assert app.translation_third == "en" and app.conversation_font_size == 30
            assert app.t.language == "en" and app.transcript_data == original
            assert not calls, calls
            checks.append("reviewed-apply-retains-conversation-and-makes-no-download-or-recording")
            app.set_ui_language("fr", reopen_settings=True)
            pump()
            assert app.transcript_data == original and app.t.language == "fr"
            app.close_workspace_settings()
            app.change_transcript_font(2)
            assert app.transcript_font_combo.get() == "32"
            checks.append("language-and-font-controls-stay-synchronized")
            assert settings.get("model") == "auto-multilingual"
            app.running, app.closing = False, True
            app.destroy()
            store2 = SettingsStore(settings.path)
            app = QuietApp(hardware=hardware, engine=engine, settings=store2, history=HistoryStore(folder / "history.sqlite3"),
                           show_onboarding=False)
            app.report_callback_exception = lambda *values: errors.append("".join(traceback.format_exception(*values)))
            app.tk.createcommand("bgerror", lambda message: errors.append("Tcl: "+message))
            pump(0.4)
            assert app.selected_model_id == "auto-multilingual" and app.conversation_font_size == 32
            assert app.conversation_partner == "ar" and app.translation_third == "en"
            checks.append("restart-keeps-chosen-profile-languages-and-accessibility")
            assert not errors, errors
            proof.update(success=True, checks=checks, explained_controls=help_count, callback_errors=errors,
                         inference_or_recording_calls=len(calls))
        except Exception:
            proof["error"] = traceback.format_exc()
            raise
        finally:
            (folder / "proof.json").write_text(json.dumps(proof, indent=2), "utf-8")
            if app.winfo_exists():
                app.running, app.closing = False, True
                app.recorder.stop_monitor()
                app.destroy()
        print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
