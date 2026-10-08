"""Readable conversation view and honest live pipeline indicators."""
from __future__ import annotations

import time
from tkinter import TclError

import customtkinter as ctk

from src.settings import bounded_int
from src.speech_output_ui import SpeechOutputMixin


class ConversationMixin(SpeechOutputMixin):
    def _build_conversation_toolbar(self, toolbar):
        row = ctk.CTkFrame(toolbar, fg_color="transparent")
        row.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(6, 0))
        row.grid_columnconfigure(0, weight=1)
        self.conversation_legend = ctk.CTkLabel(row, text="", text_color="#5EE4B7", font=("Segoe UI", 12))
        self.conversation_legend.grid(row=0, column=0, sticky="w")
        tools = ctk.CTkFrame(row, fg_color="transparent")
        tools.grid(row=0, column=1, sticky="e")
        for label, delta in (("A−", -2), ("A+", 2)):
            ctk.CTkButton(tools, text=label, width=42, height=29, fg_color="#16233D",
                          command=lambda step=delta: self.change_transcript_font(step)).pack(side="left", padx=2)
        self.font_size_label = ctk.CTkLabel(tools, text=str(self.conversation_font_size), width=26)
        self.font_size_label.pack(side="left", padx=3)
        self.reading_button = ctk.CTkButton(tools, text=self.t("reading_view"), width=170, height=29,
                                           fg_color="#16233D", command=self.toggle_reading_view)
        self.reading_button.pack(side="left", padx=(5, 2))
        self.focus_pause = ctk.CTkButton(tools, text=self.t("pause"), width=85, height=29,
                                        fg_color="#5B4825", command=self.toggle_pause, state="disabled")
        self.focus_pause.pack(side="left", padx=(5, 2))
        self.focus_stop = ctk.CTkButton(tools, text=self.t("stop"), width=85, height=29,
                                       fg_color="#8C3444", command=self.stop_recording, state="disabled")
        self.focus_stop.pack(side="left", padx=2)
        self.pipeline_label = ctk.CTkLabel(row, text=self.t("pipeline_idle"), text_color="#9AA8BE",
                                          font=("Segoe UI", 12), anchor="w")
        self.pipeline_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(3, 0))
        self.sampling_bar = ctk.CTkProgressBar(row, height=4, progress_color="#65A8FF", fg_color="#26344D")
        self.sampling_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 3))
        self.sampling_bar.set(0)
        self._build_speech_controls(row)

    def change_transcript_font(self, delta):
        self._commit_editor_changes()
        self.conversation_font_size = bounded_int(self.conversation_font_size + delta, 22, 14, 48)
        self.font_size_label.configure(text=str(self.conversation_font_size))
        self.persist_settings()
        self.render_transcript()

    def toggle_reading_view(self):
        self.reading_view = not self.reading_view
        # Tk fullscreen can span the entire virtual desktop on Windows. A
        # maximized reading window stays on its current monitor and keeps the
        # normal window controls available.
        if self.reading_view:
            self._reading_geometry = self.geometry()
            self._reading_state = self.state()
            try:
                self.state("zoomed")
            except TclError:
                try:
                    self.attributes("-zoomed", True)
                except TclError:
                    pass
        else:
            try:
                self.attributes("-zoomed", False)
            except TclError:
                pass
            self.state("normal")
            self.geometry(self._reading_geometry)
            if self._reading_state == "zoomed":
                try:
                    self.state("zoomed")
                except TclError:
                    pass
        self._apply_mode_visibility()
        self.reading_button.configure(text=self.t("reading_exit" if self.reading_view else "reading_view"))
        self.render_transcript()

    def _escape_action(self):
        if self.reading_view:
            self.toggle_reading_view()
        else:
            self.cancel_job()

    def _pipeline_activity(self, stage):
        self.pipeline_stage = stage
        self.pipeline_started = time.monotonic()

    def _update_pipeline_display(self):
        now = time.monotonic()
        if now - getattr(self, "pipeline_updated", 0) < 0.15:
            return
        self.pipeline_updated = now
        recording = self.recorder.recording
        self.focus_pause.configure(state="normal" if recording else "disabled",
                                   text=self.t("resume" if self.recorder.paused else "pause"))
        self.focus_stop.configure(state="normal" if recording else "disabled")
        if recording or self.recorder.segmenting or self.pipeline_stage in {"transcribing", "translating", "separating"}:
            state = self.recorder.sampling_state()
            seconds = state.get("seconds", 0)
            maximum = max(1, state.get("maximum_seconds", 12))
            self.sampling_bar.set(min(1, seconds / maximum))
            sampling = self.t("pipeline_paused") if self.recorder.paused else self.t(
                "pipeline_" + state.get("state", "listening"), seconds=seconds)
            stage = self.t("pipeline_" + self.pipeline_stage, seconds=max(0, time.monotonic() - self.pipeline_started))
            self.pipeline_label.configure(text=f"{sampling}   •   {stage}   •   " + self.t("pipeline_queue", count=state.get("pending", 0)))
        elif not self.busy:
            self.pipeline_label.configure(text=self.t("pipeline_idle"))
            self.sampling_bar.set(0)

    def translation_changed(self, field, code):
        if self.busy or self.recorder.recording:
            return
        setattr(self, field, code)
        if field == "conversation_partner" and code not in {"auto", "none"}:
            from src.translation_languages import ASR_LANGUAGES
            if code not in ASR_LANGUAGES and self.hardware.model_compatibility("omnilingual-1b-v2", "auto").supported:
                self.selected_model_id = "omnilingual-1b-v2"
                self.selected_device = "auto"
                self._update_model_indicators()
        self.translation_controls.refresh()
        self.translation_controls.update_pair([])
        self.persist_settings()
        self.preload_selected_model()

    def _translation_toggled(self):
        self._update_source_context()
        self.persist_settings()
        self.preload_selected_model()
