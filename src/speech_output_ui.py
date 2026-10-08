"""On-demand voice bank and reading of logical transcript lines."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from src.jobs import JobCancelled
from src.speech_output import CATALOG, LocalSpeechOutput
from src.system_voices import installed_voices, speak_system
from src.translation_languages import language_label, normalize_language


class SpeechOutputMixin:
    def _build_speech_controls(self, parent):
        if not hasattr(self, "speech_output"):
            self.speech_output = LocalSpeechOutput()
            self.voice_cancel = threading.Event()
            self.speech_thread = None
            self.system_voices = []
            self.voice_choice = "auto"
            self.playback_pause_owned = False
            self.voice_offered = set()
            self.last_audio = None
            self.show_confidence_var = ctk.BooleanVar(value=self.settings.get("show_confidence", True))
            self.overlap_var = ctk.BooleanVar(value=self.settings.get("overlap_separation", False))
            self.slow_voice_var = ctk.BooleanVar(value=False)
            def detect():
                self.system_voices = installed_voices()
            threading.Thread(target=detect, daemon=True, name="InstalledVoices").start()
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        ctk.CTkButton(row, text=self.t("speech_read"), width=155, height=28, fg_color="#16233D",
                      command=self.read_transcript_lines).pack(side="left", padx=(0, 5))
        ctk.CTkButton(row, text=self.t("speech_stop"), width=55, height=28, fg_color="#16233D",
                      command=self.stop_speaking).pack(side="left", padx=3)
        ctk.CTkButton(row, text=self.t("speech_bank"), width=105, height=28, fg_color="#16233D",
                      command=self.open_voice_bank).pack(side="left", padx=3)
        ctk.CTkCheckBox(row, text=self.t("speech_slow"), variable=self.slow_voice_var, width=105,
                        font=("Segoe UI", 11), checkbox_width=18, checkbox_height=18).pack(side="left", padx=8)
        ctk.CTkCheckBox(row, text=self.t("confidence_toggle"), variable=self.show_confidence_var,
                        font=("Segoe UI", 11), checkbox_width=18, checkbox_height=18,
                        command=self._confidence_changed).pack(side="left", padx=8)
        self.voice_prompt = ctk.CTkButton(row, text="", width=210, height=28, fg_color="#1D463A")
        ctk.CTkCheckBox(row, text=self.t("overlap_toggle"), variable=self.overlap_var,
                        font=("Segoe UI", 11), checkbox_width=18, checkbox_height=18,
                        command=self._overlap_changed).pack(side="left", padx=8)
        self.speech_menu = tk.Menu(self, tearoff=False)
        self.speech_menu.add_command(label=self.t("speech_read_selection"), command=self.read_transcript_lines)
        self.speech_menu.add_command(label=self.t("speech_original_audio"), command=self.replay_original_audio)
        self.speech_menu.add_command(label=self.t("speech_bank"), command=self.open_voice_bank)
        self.speech_menu.add_command(label=self.t("speech_stop"), command=self.stop_speaking)

    def _confidence_changed(self):
        self._commit_editor_changes()
        self.persist_settings()
        self.render_transcript()

    def _overlap_changed(self):
        if self.busy or self.recorder.recording:
            self.overlap_var.set(bool(self.settings.get("overlap_separation", False)))
            return
        self.persist_settings()
        self.preload_selected_model()

    def _transcript_context_menu(self, event):
        self.speech_menu.tk_popup(event.x_root, event.y_root)
        self.speech_menu.grab_release()

    def _system_voice(self, language):
        base = normalize_language(language).split("_")[0] if language else ""
        return next((voice for voice in self.system_voices
                     if voice["language"].replace("-", "_").split("_")[0] == base), None)

    def _offer_detected_voice(self):
        for item in reversed(self.transcript_data):
            code = normalize_language(item.get("source_language"))
            if code and code not in self.voice_offered and self.speech_output.supports(code) and not self.speech_output.ready(code):
                self.voice_offered.add(code)
                self.voice_prompt.configure(text=self.t("speech_download_detected", language=language_label(code, self.t.language)),
                                             command=lambda value=code: self.prepare_voice(value))
                self.voice_prompt.pack(side="right", padx=3)
                break

    def open_voice_bank(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title(self.t("speech_bank"))
        dialog.geometry("720x350")
        dialog.transient(self)
        dialog.configure(fg_color="#08101F")
        ctk.CTkLabel(dialog, text=self.t("speech_bank_help"), wraplength=650, justify="left").pack(padx=25, pady=22)
        choices = {self.t("speech_auto"): "auto"}
        for code in sorted(CATALOG["voices"], key=lambda value: language_label(value, self.t.language)):
            backend = "MMS · CC BY-NC" if CATALOG["voices"][code].get("backend") == "mms" else "Piper"
            choices[("✓ " if self.speech_output.ready(code) else "↓ ") + language_label(code, self.t.language) + " · " + backend] = "local:" + code
        for voice in self.system_voices:
            choices[voice["name"] + " · " + voice["language"] + " · " + self.t("speech_system")] = "system:" + voice["id"]
        picker = ctk.CTkOptionMenu(dialog, values=list(choices), width=650, dynamic_resizing=False)
        picker.set(next((label for label, value in choices.items() if value == self.voice_choice), self.t("speech_auto")))
        picker.pack(padx=25, pady=10)
        def choose():
            self.voice_choice = choices[picker.get()]
            dialog.destroy()
            if self.voice_choice.startswith("local:") and not self.speech_output.ready(self.voice_choice[6:]):
                self.prepare_voice(self.voice_choice[6:])
        ctk.CTkButton(dialog, text=self.t("save"), command=choose).pack(pady=20)

    def prepare_voice(self, language):
        if self.speech_thread and self.speech_thread.is_alive():
            return
        if not messagebox.askyesno(self.t("speech_bank"), self._voice_download_message([language]), parent=self):
            return
        self.voice_cancel = threading.Event()
        cancel = self.voice_cancel
        def worker():
            try:
                self._safe_ui(self._set_status, self.t("speech_preparing"))
                self.speech_output.prepare(language, cancel_event=cancel)
                self._safe_ui(self.voice_prompt.pack_forget)
                self._safe_ui(self._set_status, self.t("speech_ready", language=language_label(language, self.t.language)))
            except JobCancelled:
                pass
            except Exception as error:
                self._safe_ui(self._set_status, str(error))
        self.speech_thread = threading.Thread(target=worker, daemon=True, name="VoicePreparation")
        self.speech_thread.start()

    def _voice_download_message(self, languages):
        message = self.t("speech_download_question", language=", ".join(language_label(code, self.t.language) for code in languages))
        if any(CATALOG["voices"].get(code, {}).get("backend") == "mms" for code in languages):
            message += "\n\n" + self.t("speech_mms_license")
        return message

    def selected_speech_lines(self):
        widget = self.textbox._textbox
        selection = widget.tag_ranges("sel")
        mapping = getattr(self.textbox, "_speech_lines", {})
        items = []
        if selection:
            first = int(str(selection[0]).split(".")[0])
            last_index = str(selection[1]).split(".")
            last = int(last_index[0]) - (1 if last_index[1] == "0" else 0)
            items = [mapping[row] for row in range(first, last + 1) if row in mapping]
            if not items:
                code = self.selected_language if self.selected_language != "auto" else self.t.language
                items = [(widget.get(*selection), code)]
        else:
            item = next((item for item in reversed(self.transcript_data) if item.get("text")), None)
            if item:
                items = [(item["text"], item.get("target_language") or item.get("source_language") or self.t.language)]
        return items

    def read_transcript_lines(self):
        items = self.selected_speech_lines()
        if not items:
            return
        mode = self.voice_choice
        if mode.startswith("local:"):
            items = [(text, mode[6:]) for text, _ in items]
        missing = {code for _, code in items if not mode.startswith("system:") and not self.speech_output.ready(code)
                   and (self.speech_output.supports(code) and not (mode == "auto" and self._system_voice(code)))}
        if missing and not messagebox.askyesno(self.t("speech_bank"), self._voice_download_message(sorted(missing)), parent=self):
            return
        for _, code in items:
            if not mode.startswith("system:") and not self.speech_output.supports(code) and not self._system_voice(code):
                self._set_status(self.t("speech_unavailable", language=language_label(code, self.t.language)))
                return
        slow = bool(self.slow_voice_var.get())
        def operation(cancel):
            import sounddevice as sd
            for text, code in items:
                if cancel.is_set():
                    return
                system = self._system_voice(code) if mode == "auto" and not self.speech_output.ready(code) else None
                if mode.startswith("system:") or system:
                    speak_system(text, mode[7:] if mode.startswith("system:") else system["id"], slow, cancel)
                else:
                    audio, rate = self.speech_output.synthesize(text, code, slow, cancel_event=cancel)
                    if cancel.is_set():
                        return
                    sd.play(audio, rate)
                    while sd.get_stream().active:
                        if cancel.wait(0.1):
                            sd.stop()
                            return
        self._start_speech_operation(operation)

    def replay_original_audio(self):
        if self.last_audio is None:
            self._set_status(self.t("speech_audio_unavailable"))
            return
        audio = self.last_audio.copy()
        def operation(cancel):
            import sounddevice as sd
            sd.play(audio, 16000)
            while sd.get_stream().active:
                if cancel.wait(0.1):
                    sd.stop()
                    return
        self._start_speech_operation(operation)

    def _start_speech_operation(self, operation):
        if self.speech_thread and self.speech_thread.is_alive():
            self.stop_speaking()
            return
        self.voice_cancel = threading.Event()
        cancel = self.voice_cancel
        self.playback_pause_owned = self.recorder.recording and not self.recorder.paused
        if self.playback_pause_owned:
            self.recorder.pause()
        self._set_status(self.t("speech_playing"))
        def worker():
            try:
                operation(cancel)
            except JobCancelled:
                pass
            except Exception as error:
                self._safe_ui(self._set_status, self.t("speech_failed", error=str(error)))
            finally:
                self._safe_ui(self._speech_finished, cancel)
        self.speech_thread = threading.Thread(target=worker, daemon=True, name="LocalSpeechOutput")
        self.speech_thread.start()

    def _speech_finished(self, cancel):
        if cancel is not self.voice_cancel:
            return
        if self.playback_pause_owned and self.recorder.recording and not self.closing:
            self.recorder.resume()
        self.playback_pause_owned = False

    def stop_speaking(self, resume=True):
        if hasattr(self, "voice_cancel"):
            self.voice_cancel.set()
            import sounddevice as sd
            sd.stop()
            if not resume:
                self.playback_pause_owned = False
