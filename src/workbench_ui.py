"""Conversation review, audience display, typed replies and private sessions."""
from __future__ import annotations

import json
import threading
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from src.click_speech import insert_speech_line, selected_lines
from src.exports import write_bundle
from src.private_session import decrypt_segments, save_private
from src.review import audience_lines, retranslate_segment, review_values
from src.session import SessionController, identified
from src.tooltip import ToolTip
from src.translation_languages import language_label, normalize_language
from src.translation_ui import LanguagePickerDialog, display_line

PANEL = "#16233D"


class WorkbenchMixin:
    def _tool_dialog(self, title, width, height):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        x = self.winfo_rootx() + max(0, (self.winfo_width() - width) // 2)
        y = self.winfo_rooty() + max(0, min(60, (self.winfo_height() - height) // 2))
        dialog.geometry(f"{width}x{height}{x:+d}{y:+d}")
        dialog.transient(self)
        dialog.t = self.t
        dialog.configure(fg_color="#08101F")
        dialog.bind("<Escape>", lambda _: dialog.destroy())
        return dialog

    def _workbench_controls(self, master):
        if not hasattr(self, "session_controller"):
            self.session_controller = SessionController()
            self.private_mode = False
            self.audience_window = None
            self.current_session_base = None
            self.tool_threads = []
        workspace = getattr(self, "workspace_layout", False)
        if workspace:
            ctk.CTkLabel(master, text=self.t("workspace_step_tools"), text_color="#9AA8BE",
                         font=("Segoe UI", 11, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=5)
        tools = ctk.CTkFrame(master, fg_color="transparent")
        tools.grid(row=1 if workspace else 5, column=0, columnspan=2, sticky="ew", pady=(5, 2))
        for key, command in (("review_turns", self.review_turns), ("audience", self.open_audience),
                             ("typed_reply", self.compose_reply), ("offline_prepare", self.offline_prepare),
                             ("privacy_controls", self.privacy_controls)):
            button = ctk.CTkButton(tools, text=self.t(key), height=28, width=145,
                                   fg_color=PANEL, command=command)
            if workspace:
                button.pack(fill="x", pady=3)
            else:
                button.pack(side="left", padx=(0, 5))
            ToolTip(button, self.t(key + "_help"))
        self.live_preview_label = ctk.CTkLabel(self.preview_host if workspace else master, text="", font=("Segoe UI", 17),
                                              text_color="#F3C969", anchor="w", justify="left",
                                              wraplength=1060)
        self.live_preview_label.grid(row=1 if workspace else 6, column=0, columnspan=2, sticky="ew", pady=(3, 1))
        if workspace:
            self.live_preview_label.grid_remove()

    def _show_live_preview(self, text, language=""):
        if hasattr(self, "live_preview_label"):
            self.live_preview_label.configure(text=self.t("provisional", text=text[:1000], language=language) if text else "")
            if getattr(self, "workspace_layout", False):
                if text:
                    self.preview_host.grid()
                    self.live_preview_label.grid()
                else:
                    self.live_preview_label.grid_remove()
                    if not self.transcript_search.visible:
                        self.preview_host.grid_remove()

    def _update_audience(self):
        window = getattr(self, "audience_window", None)
        if window is None or not window.winfo_exists():
            return
        box = window.box
        selected = window.languages.get(window.picker.get(), "all")
        languages = self._audience_languages()
        if languages != window.languages:
            window.languages = languages
            window.picker.configure(values=list(languages))
            window.picker.set(next((label for label, code in languages.items() if code == selected), next(iter(languages))))
            selected = window.languages[window.picker.get()]
        box.configure(state="normal", font=("Segoe UI", window.font_size))
        box.delete("1.0", "end")
        for tag, color in (("original", "#F5F7FB"), ("translated", "#5EE4B7")):
            box._textbox.tag_configure(tag, foreground=color, spacing3=15)
            box._textbox.tag_configure(tag + "_rtl", foreground=color, justify="right", spacing3=15)
        window.speech_lines = box._speech_lines = {}
        for code, text, tag in audience_lines(self.transcript_data, selected):
            shaped, rtl = display_line(text)
            insert_speech_line(box, shaped, text, code or self._default_speech_language(), tag + ("_rtl" if rtl else ""))
            box.insert("end", "\n")
        box.configure(state="disabled")
        self._click_speech_state(box)
        box.see("end")

    def _audience_languages(self):
        codes = {self.translation_target, self.conversation_partner, self.translation_third}
        codes.update(item.get(field) for item in self.transcript_data
                     for field in ("language", "source_language", "target_language", "third_language"))
        languages = {self.t("audience_both"): "all"}
        languages.update({language_label(code, self.t.language): code for code in
                          sorted(code for code in codes if code and code not in {"auto", "none", "und"})})
        return languages

    def open_audience(self):
        if self.audience_window is not None and self.audience_window.winfo_exists():
            self.audience_window.lift()
            return
        window = self.audience_window = ctk.CTkToplevel(self)
        window.title(self.t("audience"))
        window.geometry("1050x720")
        window.configure(fg_color="#08101F")
        window.font_size = 32
        ctk.CTkLabel(window, text=self.t("audience_help"), wraplength=950).pack(padx=20, pady=10)
        controls = ctk.CTkFrame(window, fg_color="transparent")
        controls.pack(fill="x", padx=20)
        window.languages = self._audience_languages()
        window.picker = ctk.CTkOptionMenu(controls, values=list(window.languages), command=lambda _: self._update_audience())
        window.picker.pack(side="left", padx=5)
        def resize(delta):
            window.font_size = max(18, min(72, window.font_size + delta))
            self._update_audience()
        for label, delta in (("A−", -4), ("A+", 4)):
            ctk.CTkButton(controls, text=label, width=50, command=lambda value=delta: resize(value)).pack(side="left", padx=4)
        def read_visible():
            selection = window.box._textbox.tag_ranges("sel")
            if selection:
                first = int(str(selection[0]).split(".")[0])
                end_row, end_column = str(selection[1]).split(".")
                last = int(end_row) - (1 if end_column == "0" else 0)
                items = selected_lines(window.speech_lines, first, last)
            else:
                items = list(window.speech_lines.values())[-1:]
            self.speak_items(items)
        ctk.CTkButton(controls, text=self.t("speech_read_selection"), command=read_visible).pack(side="right", padx=5)
        click_row = ctk.CTkFrame(window, fg_color="transparent")
        click_row.pack(fill="x", padx=25, pady=(8, 0))
        self._click_speech_checkbox(click_row).pack(side="left")
        ctk.CTkButton(click_row, text=self.t("speech_stop"), command=self.stop_speaking,
                      width=90, fg_color=PANEL).pack(side="right", padx=5)
        ToolTip(click_row, self.t("speech_click_help"))
        window.box = ctk.CTkTextbox(window, wrap="word", fg_color="#111C32")
        window.box.pack(fill="both", expand=True, padx=20, pady=20)
        self._bind_click_speech(window.box)
        self._update_audience()

    def review_turns(self):
        if not self.transcript_data:
            return
        self.transcript_data = identified(self.transcript_data)
        dialog = self._tool_dialog(self.t("review_turns"), 900, 780)
        dialog.t = self.t
        dialog.configure(fg_color="#08101F")
        ctk.CTkLabel(dialog, text=self.t("review_turns_help"), wraplength=830, justify="left").pack(padx=20, pady=12)
        choices = {f"{index + 1} · {item.get('source_text', item.get('text', ''))[:85]}": item["segment_id"]
                   for index, item in enumerate(self.transcript_data)}
        selected = {"id": next(iter(choices.values()))}
        history = ctk.CTkLabel(dialog, text="", text_color="#9AA8BE")
        source = ctk.CTkTextbox(dialog, height=150, font=("Segoe UI", 20), wrap="word")
        source_preview = ctk.CTkLabel(dialog, text="", font=("Segoe UI", 18), wraplength=830,
                                     anchor="e", justify="right", text_color="#9AA8BE")
        translated = ctk.CTkTextbox(dialog, height=150, font=("Segoe UI", 20), wrap="word")
        speaker = ctk.CTkEntry(dialog, placeholder_text=self.t("review_speaker"))
        language_row = ctk.CTkFrame(dialog, fg_color="transparent")
        language_row.grid_columnconfigure((0, 1), weight=1)
        code = ctk.CTkButton(language_row, text="", width=350)
        destination = ctk.CTkButton(language_row, text="", width=350)
        code.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        destination.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        def choose_source_language(value):
            selected["language"] = value
            code.configure(text=language_label(value, self.t.language))
        code.configure(command=lambda: LanguagePickerDialog(dialog, selected.get("language"), choose_source_language))
        def choose_destination(value):
            selected["target"] = value
            destination.configure(text=language_label(value, self.t.language) if value else "—")
        destination.configure(command=lambda: LanguagePickerDialog(dialog, selected.get("target"), choose_destination))
        def current():
            return next((item for item in self.transcript_data if item.get("segment_id") == selected["id"]), None)
        def load(label):
            selected["id"] = choices[label]
            item = current()
            for widget, text in ((source, item.get("source_text", item.get("text", ""))), (translated, item.get("text", "") if "source_text" in item else "")):
                widget.delete("1.0", "end")
                widget.insert("1.0", text)
            speaker.delete(0, "end")
            speaker.insert(0, item.get("speaker", ""))
            choose_source_language(item.get("source_language", item.get("language", "und")))
            choose_destination(item.get("target_language"))
            history.configure(text=self.t("review_history", count=len(item.get("revisions", []))))
            source_preview.configure(text=display_line(source.get("1.0", "end-1c"))[0])
        picker = ctk.CTkOptionMenu(dialog, values=list(choices), command=load, width=840)
        picker.pack(fill="x", padx=20, pady=7)
        ctk.CTkLabel(dialog, text=self.t("review_source")).pack(anchor="w", padx=20)
        source.pack(fill="x", padx=20, pady=4)
        source_preview.pack(fill="x", padx=20, pady=4)
        source.bind("<KeyRelease>", lambda _: source_preview.configure(text=display_line(source.get("1.0", "end-1c"))[0]))
        ctk.CTkLabel(dialog, text=self.t("review_translation")).pack(anchor="w", padx=20)
        translated.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(dialog, text=self.t("review_speaker")).pack(anchor="w", padx=20)
        speaker.pack(fill="x", padx=20, pady=5)
        language_row.pack(fill="x", padx=20, pady=5)
        history.pack(pady=5)
        def commit(retranslate=False):
            item = current()
            if item is None:
                return
            source_value = source.get("1.0", "end-1c")
            translated_value = translated.get("1.0", "end-1c")
            try:
                corrected = review_values(item, source_value, translated_value, normalize_language(selected.get("language")),
                                          speaker.get(), selected.get("target"), retranslate)
            except ValueError as error:
                messagebox.showerror(self.t("error"), str(error), parent=dialog)
                return
            self._apply_review(corrected)
            translated.delete("1.0", "end")
            translated.insert("1.0", corrected.get("text", "") if "source_text" in corrected else "")
            if retranslate:
                def operation():
                    with self.engine._load_lock:
                        self.engine.translator.load(self.hardware, allow_download=False,
                            allow_cpu_virtual_memory=self.selected_device == "cpu-virtual")
                        return retranslate_segment(corrected, self.engine.translator)
                def finished(result):
                    self._apply_retranslation(result)
                    if (dialog.winfo_exists() and selected["id"] == result.get("segment_id")
                            and source.get("1.0", "end-1c").strip() == source_value.strip()
                            and translated.get("1.0", "end-1c") == corrected.get("text", "")):
                        load(picker.get())
                self._workbench_job(operation, finished)
            history.configure(text=self.t("review_history", count=len(corrected.get("revisions", []))))
        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(buttons, text=self.t("save"), command=commit).pack(side="left", padx=5)
        ctk.CTkButton(buttons, text=self.t("review_retranslate"), command=lambda: commit(True)).pack(side="left", padx=5)
        ctk.CTkButton(buttons, text=self.t("review_audio"), command=lambda: self.replay_segment(current())).pack(side="left", padx=5)
        ctk.CTkButton(buttons, text=self.t("review_show_history"), command=lambda: messagebox.showinfo(self.t("review_show_history"), json.dumps(current().get("revisions", []), ensure_ascii=False, indent=2), parent=dialog)).pack(side="left", padx=5)
        load(next(iter(choices)))

    def _apply_review(self, item):
        self.session_controller.correct(item)
        self.transcript_data = self.session_controller.snapshot(self.transcript_data)
        self.render_transcript()
        self._save_backup()
        if self.current_session_base and not self.private_mode and not self.recorder.recording and not self.busy:
            write_bundle(self.current_session_base, self.transcript_data, self.transcript_format_options())

    def _apply_retranslation(self, item):
        current = next((value for value in self.transcript_data if value.get("segment_id") == item.get("segment_id")), None)
        if (current is None or current.get("source_text") != item.get("source_text")
                or len(current.get("revisions", [])) != item.get("retranslated_from_revision")):
            self._set_status(self.t("review_stale"))
            return
        self._apply_review(item)

    def replay_segment(self, item):
        if item is None:
            return
        path = item.get("audio_path")
        if not path or not Path(path).is_file():
            self._set_status(self.t("speech_audio_unavailable"))
            return
        start, end = float(item.get("audio_start", item.get("start", 0))), float(item.get("audio_end", item.get("end", 0)))
        def operation(cancel):
            import numpy as np
            import sounddevice as sd

            from src.media import iter_audio_chunks
            chunks, offset = [], 0.0
            for offset, chunk in iter_audio_chunks(path, 10):
                if cancel.is_set():
                    return
                finish = offset + len(chunk) / 16000
                if finish > start and offset < end:
                    chunks.append(chunk[max(0, round((start - offset) * 16000)):min(len(chunk), round((end - offset) * 16000))])
                offset = finish
                if offset >= end:
                    break
            if chunks:
                sd.play(np.concatenate(chunks), 16000)
                while sd.get_stream().active:
                    if cancel.wait(0.1):
                        sd.stop()
                        return
        self._start_speech_operation(operation)

    def _workbench_job(self, operation, completed):
        def worker():
            try:
                result = operation()
                self._safe_ui(completed, result)
            except Exception as error:
                self._safe_ui(self._set_status, self.t("workbench_failed", error=str(error)))
        thread = threading.Thread(target=worker, daemon=True, name="conversation-tools")
        self.tool_threads = [value for value in self.tool_threads if value.is_alive()]
        self.tool_threads.append(thread)
        thread.start()

    def compose_reply(self):
        dialog = self._tool_dialog(self.t("typed_reply"), 760, 430)
        ctk.CTkLabel(dialog, text=self.t("typed_reply_help"), wraplength=700).pack(padx=20, pady=15)
        text = ctk.CTkTextbox(dialog, height=220, font=("Segoe UI", 21))
        text.pack(fill="both", expand=True, padx=20)
        def submit():
            value = text.get("1.0", "end-1c").strip()
            if not value:
                return
            target = self.conversation_partner if self.conversation_partner != "auto" else None
            if target is None and self.engine.translator.router:
                target = next((code for code in self.engine.translator.router.pair if code != self.translation_target), None)
            if not target:
                self._set_status(self.t("reply_choose_language"))
                return
            source_language = self.translation_target
            controller = self.session_controller
            position = self.recording_offset if self.recorder.recording else max((item.get("end", 0) for item in self.transcript_data), default=0)
            dialog.destroy()
            def operation():
                with self.engine._load_lock:
                    self.engine.translator.load(self.hardware, allow_download=False,
                        allow_cpu_virtual_memory=self.selected_device == "cpu-virtual")
                    result = identified([{"start": position, "end": position, "source_text": value,
                                          "source_language": source_language, "target_language": target,
                                          "text": "", "input_mode": "typed", "words": []}])[0]
                    return retranslate_segment(result, self.engine.translator)
            def done(item):
                self._accept_reply(item, controller)
            self._workbench_job(operation, done)
        ctk.CTkButton(dialog, text=self.t("reply_translate_speak"), command=submit).pack(pady=15)

    def _accept_reply(self, item, controller):
        if controller is not self.session_controller:
            return
        self.session_controller.add_reply(item)
        self._apply_review(item)
        self.speak_items([(item["text"], item["target_language"])])

    def offline_prepare(self):
        if self.busy or self.recorder.recording:
            self._set_status(self.t("tools_idle"))
            return
        dialog = self._tool_dialog(self.t("offline_prepare"), 800, 730)
        ctk.CTkLabel(dialog, text=self.t("offline_prepare_help"), wraplength=710, justify="left").pack(padx=25, pady=20)
        codes = [self.translation_target, self.conversation_partner, self.translation_third]
        codes += [item.get(field) for item in self.transcript_data[-20:] for field in ("source_language", "target_language", "third_language")]
        codes = list(dict.fromkeys(code for code in codes if code and code not in {"auto", "none", "und"}))
        ctk.CTkLabel(dialog, text=" · ".join(language_label(code, self.t.language) for code in codes), wraplength=700).pack(pady=10)
        model_choices = {"MADLAD 3B · 452 · standard": "madlad400-3b", "MADLAD 7B · 452 · expérimental / experimental · 8.3 GB": "madlad400-7b"}
        model_picker = ctk.CTkOptionMenu(dialog, values=list(model_choices), width=700)
        model_picker.set(next(label for label, code in model_choices.items() if code == self.settings.get("translation_model", "madlad400-3b")))
        model_picker.pack(pady=8)
        ctk.CTkLabel(dialog, text=self.t("translation_model_resources"), wraplength=710, justify="left").pack(padx=25, pady=3)
        context = ctk.BooleanVar(value=bool(self.settings.get("translation_context", False)))
        ctk.CTkCheckBox(dialog, text=self.t("context_translation"), variable=context).pack(pady=7)
        ctk.CTkLabel(dialog, text=self.t("glossary_label")).pack(anchor="w", padx=25, pady=(6, 0))
        glossary = ctk.CTkTextbox(dialog, height=90)
        glossary.insert("1.0", self.settings.get("translation_glossary", ""))
        glossary.pack(fill="x", padx=25, pady=7)
        ToolTip(glossary, self.t("glossary_help"))
        cache_label = ctk.CTkLabel(dialog, text=self.settings.get("translation_cache", "") or self.t("default_cache"), wraplength=700)
        cache_label.pack()
        def choose_cache():
            folder = filedialog.askdirectory(parent=dialog, title=self.t("translation_cache_choose"))
            if folder:
                self.settings.set("translation_cache", folder, save=True)
                cache_label.configure(text=folder)
        ctk.CTkButton(dialog, text=self.t("translation_cache_choose"), command=choose_cache, width=330).pack(pady=7)
        report = ctk.CTkLabel(dialog, text="", wraplength=700, justify="left")
        report.pack(padx=25, pady=20)
        buttons = []
        def prepare(download):
            if download and not messagebox.askyesno(self.t("offline_prepare"), self._voice_download_message(codes), parent=dialog):
                return
            for button in buttons:
                button.configure(state="disabled")
            config = self.job_config()
            self.settings.update({"translation_model": model_choices[model_picker.get()],
                                  "translation_context": bool(context.get()),
                                  "translation_glossary": glossary.get("1.0", "end-1c")[:6000]}, save=True)
            config = self.job_config()
            options = replace(self.transcribe_options(config), offline=not download, original_callback=None, activity_callback=None)
            self._set_source_buttons_state("disabled")
            self.busy = True
            def operation():
                from src.offline_profile import prepare_profile
                return prepare_profile(self.engine, self.speech_output, options, config["model"], config["device"], codes, download)
            def finished(value):
                self.busy = False
                self._set_source_buttons_state("normal")
                if dialog.winfo_exists():
                    report.configure(text=value)
                    for button in buttons:
                        button.configure(state="normal")
                self._set_status(self.t("offline_complete"))
            def run():
                try:
                    value = operation()
                except Exception as error:
                    value = str(error)
                self._safe_ui(finished, value)
            thread = threading.Thread(target=run, daemon=True, name="offline-preparation")
            self.tool_threads.append(thread)
            thread.start()
        for key, download in (("offline_verify", False), ("offline_download", True)):
            button = ctk.CTkButton(dialog, text=self.t(key), command=lambda value=download: prepare(value), width=330)
            button.pack(pady=7)
            buttons.append(button)

    def privacy_controls(self):
        if self.busy or self.recorder.recording:
            self._set_status(self.t("tools_idle"))
            return
        dialog = self._tool_dialog(self.t("privacy_controls"), 780, 440)
        ctk.CTkLabel(dialog, text=self.t("privacy_controls_help"), wraplength=710, justify="left").pack(padx=25, pady=25)
        active = ctk.BooleanVar(value=self.private_mode)
        def change():
            self.private_mode = bool(active.get())
            self._set_status(self.t("private_active" if self.private_mode else "private_inactive"))
        ctk.CTkCheckBox(dialog, text=self.t("private_toggle"), variable=active, command=change).pack(pady=12)
        ctk.CTkButton(dialog, text=self.t("private_save"), command=lambda: self.private_file(False)).pack(pady=10)
        ctk.CTkButton(dialog, text=self.t("private_open"), command=lambda: self.private_file(True)).pack(pady=10)

    def private_file(self, opening=False):
        if self.busy or self.recorder.recording:
            return
        chooser = filedialog.askopenfilename if opening else filedialog.asksaveasfilename
        chosen = chooser(parent=self, defaultextension=".ltps", filetypes=[("Local Transcriber private", "*.ltps")])
        if not chosen:
            return
        password = simpledialog.askstring(self.t("privacy_controls"), self.t("private_password"), show="*", parent=self)
        if password is None:
            return
        try:
            if opening:
                path = Path(chosen)
                if path.stat().st_size > 33 * 1024 * 1024:
                    raise ValueError("Private session exceeds 32 MB")
                self.transcript_data = identified(decrypt_segments(path.read_bytes(), password))
                self.session_controller = SessionController()
                self.private_mode = True
                self.current_session_base = None
                self.render_transcript()
            else:
                confirmation = simpledialog.askstring(self.t("privacy_controls"), self.t("private_confirm"), show="*", parent=self)
                if confirmation != password:
                    raise ValueError(self.t("private_mismatch"))
                save_private(Path(chosen), self.transcript_data, password)
            self._set_status(self.t("private_active" if opening else "private_saved"))
        except Exception:
            messagebox.showerror(self.t("error"), self.t("private_error"), parent=self)
