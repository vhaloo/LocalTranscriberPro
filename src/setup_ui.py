"""A cancellable, local-only questionnaire with a review-before-apply step."""
from __future__ import annotations

import time
from tkinter import messagebox

import customtkinter as ctk

from src.audio import AudioRecorder
from src.guided_setup import PROFILES, TASKS, SetupAnswers, setup_plan
from src.i18n import Translator
from src.tooltip import ToolTip
from src.translation_languages import language_label
from src.translation_ui import LanguagePickerDialog
from src.ui_lifecycle import ManagedToplevel, cancel_widget_timers

BG, PANEL, ALT = "#08101F", "#122039", "#1C304C"
TEXT, MUTED, GREEN = "#F5F7FB", "#B2BFD2", "#5EE4B7"


class SetupWizard(ManagedToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.t = app, Translator(app.settings.get("ui_language", "auto"))
        self.answers = SetupAnswers.from_settings(app.settings)
        self.answers.preset = app.preset
        self.answers.font_size = app.conversation_font_size
        self.answers.spoken_language = app.selected_language
        self.step = 0
        self.variables = {}
        self.microphone_test = None
        self.meter_timer = None
        self.microphones, _default = app.recorder.get_devices()
        app.recorder.stop_monitor()
        self.title(self.t("setup_title"))
        self.configure(fg_color=BG)
        self.geometry(f"{min(850, self.winfo_screenwidth()-60)}x{min(740, self.winfo_screenheight()-80)}")
        self.minsize(680, 500)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=26, pady=(22, 10))
        self.progress = ctk.CTkLabel(self.header, text="", text_color=GREEN, font=("Segoe UI", 12, "bold"))
        self.progress.pack(anchor="w")
        self.heading = ctk.CTkLabel(self.header, text="", font=("Segoe UI", 23, "bold"), anchor="w")
        self.heading.pack(anchor="w", pady=(7, 2))
        self.intro = ctk.CTkLabel(self.header, text=self.t("setup_subtitle"), text_color=MUTED,
                                 font=("Segoe UI", 12), wraplength=710, justify="left")
        self.intro.pack(anchor="w")
        self.body = ctk.CTkScrollableFrame(self, fg_color=BG)
        self.body.grid(row=1, column=0, sticky="nsew", padx=20, pady=4)
        self.body.grid_columnconfigure(0, weight=1)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=26, pady=(10, 18))
        footer.grid_columnconfigure(0, weight=1)
        self.cancel_button = ctk.CTkButton(footer, text=self.t("setup_cancel"), command=self.destroy, fg_color=ALT, height=37)
        self.cancel_button.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.back_button = ctk.CTkButton(footer, text=self.t("setup_back"), command=lambda: self.navigate(-1),
                                        width=95, height=37, fg_color=ALT)
        self.back_button.grid(row=0, column=1, padx=5)
        self.next_button = ctk.CTkButton(footer, text=self.t("setup_next"), command=self.advance, height=37,
                                        fg_color="#26745F", hover_color="#338C73")
        self.next_button.grid(row=0, column=2, padx=(5, 0))
        for control in (self.cancel_button, self.back_button, self.next_button):
            ToolTip(control, self.t("setup_review_help"))
        self.render_step()
        self.after_idle(self.grab_set)

    def card(self, row, title, explanation):
        frame = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=13, border_width=1, border_color="#293E5A")
        frame.grid(row=row, column=0, sticky="ew", padx=4, pady=6)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=title, font=("Segoe UI", 15, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(12, 3))
        ctk.CTkLabel(frame, text=explanation, wraplength=570, justify="left", anchor="w", text_color=MUTED,
                     font=("Segoe UI", 12)).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 9))
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1)
        return content

    def radio(self, host, field, value, label, help_text, row, callback=None):
        if field not in self.variables:
            self.variables[field] = ctk.StringVar(value=getattr(self.answers, field))
        variable = self.variables[field]
        def changed():
            setattr(self.answers, field, value)
            if callback:
                callback(value)
        button = ctk.CTkRadioButton(host, text=label, variable=variable, value=value,
                                    command=changed, font=("Segoe UI", 14), fg_color="#3DC99E")
        button.grid(row=row, column=0, sticky="w", pady=(5, 2))
        ctk.CTkLabel(host, text=help_text, justify="left", anchor="w", text_color=MUTED,
                     wraplength=550, font=("Segoe UI", 12)).grid(row=row+1, column=0, sticky="ew", padx=(28, 0), pady=(0, 7))
        ToolTip(button, help_text, title=label)
        return button

    def checkbox(self, host, field, label, help_text, row):
        variable = ctk.BooleanVar(value=getattr(self.answers, field))
        self.variables[field] = variable
        button = ctk.CTkCheckBox(host, text=label, variable=variable, font=("Segoe UI", 13),
                                command=lambda: setattr(self.answers, field, bool(variable.get())))
        button.grid(row=row, column=0, sticky="w", pady=(6, 2))
        ctk.CTkLabel(host, text=help_text, text_color=MUTED, wraplength=550, justify="left", anchor="w",
                     font=("Segoe UI", 12)).grid(row=row+1, column=0, sticky="ew", padx=(28, 0), pady=(0, 7))
        ToolTip(button, help_text, title=label)
        return button

    def render_step(self):
        self.stop_microphone_test()
        self.variables = {}
        for child in self.body.winfo_children():
            cancel_widget_timers(child)
            child.destroy()
        names = ("use", "languages", "preferences", "review")
        self.progress.configure(text=self.t("setup_progress", step=self.step+1, total=4))
        self.heading.configure(text=self.t("setup_step_"+names[self.step]))
        self.intro.configure(text=self.t("setup_subtitle"))
        self.back_button.configure(text=self.t("setup_back"), state="normal" if self.step else "disabled")
        self.cancel_button.configure(text=self.t("setup_cancel"))
        self.next_button.configure(text=self.t("setup_apply" if self.step == 3 else "setup_next"))
        for control in (self.cancel_button, self.back_button, self.next_button):
            ToolTip(control, self.t("setup_review_help"))
        (self.show_use, self.show_languages, self.show_preferences, self.show_review)[self.step]()
        self.body._parent_canvas.yview_moveto(0)

    def show_use(self):
        language = self.card(0, self.t("ui_language_setting"), self.t("ui_language_help"))
        values = {self.t("ui_language_auto"): "auto", "Français": "fr", "English": "en"}
        def change(label):
            self.answers.ui_language = values[label]
            self.t.set_language(values[label])
            self.title(self.t("setup_title"))
            self.render_step()
        picker = ctk.CTkComboBox(language, values=list(values), state="readonly", command=change, height=35)
        picker.set(next(label for label, value in values.items() if value == self.answers.ui_language))
        picker.grid(row=0, column=0, sticky="ew")
        ToolTip(picker, self.t("ui_language_help"))
        uses = self.card(1, self.t("setup_step_use"), self.t("setup_use_help"))
        for index, task in enumerate(TASKS):
            self.radio(uses, "preset", task, self.t("workspace_task_"+task), self.t("task_"+task+"_help"), index*2,
                       callback=self.use_changed)

    def use_changed(self, task):
        self.answers.translate = task == "universal"
        self.answers.speakers = task == "conference"
        self.answers.click_speech = self.app.settings.get("speech_click_live" if task == "universal" else "speech_click", task == "universal")
        self.answers.chunk_seconds = 12 if task == "universal" else 10 if task == "dictation" else 30

    def language_button(self, host, field, label, help_key, row, *, optional=None, speech_only=False):
        ctk.CTkLabel(host, text=self.t(label), anchor="w", font=("Segoe UI", 13, "bold")).grid(
            row=row, column=0, sticky="ew", pady=(8, 3))
        value = getattr(self.answers, field)
        text = optional[1] if optional and value == optional[0] else language_label(value, self.t.language)
        def chosen(code):
            setattr(self.answers, field, code)
            self.render_step()
            self.grab_set()
        button = ctk.CTkButton(host, text=text+" ▾", fg_color=ALT, height=35,
                              command=lambda: LanguagePickerDialog(self, value, chosen, optional, speech_only))
        button.grid(row=row+1, column=0, sticky="ew")
        ToolTip(button, self.t(help_key), title=self.t(label))

    def show_languages(self):
        host = self.card(0, self.t("setup_step_languages"), self.t("setup_languages_help"))
        if self.answers.preset != "universal":
            self.language_button(host, "spoken_language", "spoken_language", "source_language_help", 0,
                                 optional=("auto", self.t("language_auto")), speech_only=True)
            self.checkbox(host, "translate", self.t("setup_translate"), self.t("tip_translate"), 2)
        self.language_button(host, "target", "translation_target", "tip_translation_target", 4)
        if self.answers.preset == "universal":
            self.language_button(host, "partner", "translation_partner", "tip_conversation_partner", 6,
                                 optional=("auto", self.t("translation_auto_partner")))
            self.language_button(host, "third", "translation_third", "tip_translation_third", 8,
                                 optional=("none", self.t("translation_no_third")))
        if self.answers.preset in {"universal", "conference", "dictation"}:
            mic = self.card(1, self.t("microphone"), self.t("tip_microphone"))
            choices = {self.t("default_microphone"): "auto"}
            choices.update({label: label.split(":", 1)[-1].strip() for label in self.microphones})
            def microphone_changed(label):
                self.stop_microphone_test()
                self.answers.microphone = choices[label]
                self.mic_status.configure(text=self.t("setup_mic_idle"))
            picker = ctk.CTkComboBox(mic, values=list(choices), state="readonly", height=35,
                                    command=microphone_changed)
            picker.set(next((label for label, value in choices.items() if value == self.answers.microphone), next(iter(choices))))
            picker.grid(row=0, column=0, sticky="ew")
            ToolTip(picker, self.t("tip_microphone"))
            self.mic_test_button = ctk.CTkButton(mic, text=self.t("setup_test_mic"), command=self.toggle_microphone_test, fg_color=ALT)
            self.mic_test_button.grid(row=1, column=0, sticky="w", pady=8)
            ToolTip(self.mic_test_button, self.t("setup_test_mic_help"))
            self.mic_level = ctk.CTkProgressBar(mic, progress_color=GREEN)
            self.mic_level.grid(row=2, column=0, sticky="ew", pady=4)
            self.mic_level.set(0)
            ToolTip(self.mic_level, self.t("setup_test_mic_help"))
            self.mic_status = ctk.CTkLabel(mic, text=self.t("setup_test_mic_help"), text_color=MUTED,
                                          wraplength=560, justify="left", anchor="w")
            self.mic_status.grid(row=3, column=0, sticky="ew")

    def show_preferences(self):
        host = self.card(0, self.t("profile_label"), self.t("setup_preferences_help"))
        profiles = [("best", "quality_best", "profile_best_help"), ("fast", "quality_fast", "profile_fast_help"),
                    ("coverage", "quality_coverage", "profile_coverage_help")]
        if self.answers.profile == "keep" or self.app.selected_model_id not in PROFILES.values() or self.app.selected_device != "auto":
            profiles.insert(0, ("keep", "setup_keep_model", "setup_keep_model_help"))
        for index, (value, label, help_key) in enumerate(profiles):
            self.radio(host, "profile", value, self.t(label), self.t(help_key), index*2,
                       callback=lambda profile: setattr(self.answers, "effort", self.answers.effort if profile == "keep" else
                                                         3 if profile == "fast" else self.app.maximum_quality_beam))
        preferences = self.card(1, self.t("settings_group_format"), self.t("setting_font_help"))
        sizes = ["14", "18", "22", "26", "30", "36", "42", "48"]
        picker = ctk.CTkComboBox(preferences, values=sizes, state="readonly", height=35,
                                command=lambda value: setattr(self.answers, "font_size", int(value)))
        picker.set(str(self.answers.font_size))
        picker.grid(row=0, column=0, sticky="ew")
        ToolTip(picker, self.t("setting_font_help"))
        for index, (field, label, help_key) in enumerate((
            ("keep_audio", "keep_audio", "tip_keep_audio"), ("speakers", "speaker_detection", "tip_speakers"),
            ("click_speech", "speech_click", "speech_click_help"), ("advanced", "advanced_show", "advanced_help"),
        )):
            if field != "speakers" or self.answers.preset != "universal":
                self.checkbox(preferences, field, self.t(label), self.t(help_key), index*2+1)

    def show_review(self):
        plan = setup_plan(self.answers)
        model = plan.get("model", self.app.selected_model_id)
        device = plan.get("device", self.app.selected_device)
        route = self.app.hardware.selection_compatibility(model, device, self.app.engine.cached_model_ids())
        host = self.card(0, self.t("setup_step_review"), self.t("setup_review_help"))
        rows = [(self.t("task_title"), self.t("workspace_task_"+self.answers.preset)),
                (self.t("ui_language_setting"), self.t("ui_language_auto") if self.answers.ui_language == "auto" else self.answers.ui_language.upper()),
                (self.t("model"), model+" → "+route.model_id if model != route.model_id else model),
                (self.t("device"), self.t("device_cpu_virtual") if route.reason_code == "cpu_virtual" else (route.device or "cpu").upper()),
                (self.t("spoken_language"), self.t("language_auto") if plan["spoken_language"] == "auto" else language_label(plan["spoken_language"], self.t.language)),
                (self.t("setup_large_text"), str(plan["conversation_font_size"])),
                (self.t("chunk"), str(plan["chunk_seconds"])), (self.t("beam"), str(plan["beam_size"]))]
        if plan["translate"]:
            rows.append((self.t("translation_target"), language_label(plan["translation_target"], self.t.language)))
        if self.answers.preset == "universal":
            rows.extend([(self.t("translation_partner"), self.t("translation_auto_partner") if self.answers.partner == "auto" else language_label(self.answers.partner, self.t.language)),
                         (self.t("translation_third"), self.t("translation_no_third") if self.answers.third == "none" else language_label(self.answers.third, self.t.language))])
        rows.extend([(self.t("keep_audio"), self.t("setup_enabled" if self.answers.keep_audio else "setup_disabled")),
                     (self.t("speaker_detection"), self.t("setup_enabled" if plan["speaker_detection"] else "setup_disabled")),
                     (self.t("speech_click"), self.t("setup_enabled" if self.answers.click_speech else "setup_disabled")),
                     (self.t("advanced_show"), self.t("setup_enabled" if self.answers.advanced else "setup_disabled"))])
        for row, (name, value) in enumerate(rows):
            ctk.CTkLabel(host, text=self.t("setup_review_line", name=name, value=value), wraplength=570, justify="left",
                         anchor="w", font=("Segoe UI", 13)).grid(row=row, column=0, sticky="ew", pady=4)
        self.card(1, self.t("privacy_controls"), self.t("setup_review_privacy"))

    def navigate(self, direction):
        try:
            if direction > 0 and self.step >= 1:
                setup_plan(self.answers)
        except ValueError as error:
            messagebox.showinfo(self.t("setup_title"), self.t(str(error)), parent=self)
            return
        self.step = max(0, min(3, self.step+direction))
        self.render_step()

    def advance(self):
        if self.step < 3:
            self.navigate(1)
        else:
            self.apply()

    def apply(self):
        try:
            plan = setup_plan(self.answers)
        except ValueError as error:
            messagebox.showinfo(self.t("setup_title"), self.t(str(error)), parent=self)
            return False
        self.stop_microphone_test()
        return self.app.apply_guided_setup(plan)

    def toggle_microphone_test(self):
        if self.microphone_test is not None:
            self.stop_microphone_test()
            self.mic_status.configure(text=self.t("setup_mic_idle"))
            return
        index = next((int(label.split(":", 1)[0]) for label in self.microphones
                      if label.split(":", 1)[-1].strip() == self.answers.microphone), None)
        self.microphone_test = AudioRecorder()
        if not self.microphone_test.start_monitor(index):
            self.microphone_test = None
            self.mic_status.configure(text=self.t("setup_mic_error"))
            return
        self.mic_test_button.configure(text=self.t("setup_mic_stop"))
        self.mic_status.configure(text=self.t("setup_mic_running"))
        self._meter_deadline = time.monotonic()+12
        self.tick_meter()

    def tick_meter(self):
        self.meter_timer = None
        if self.microphone_test is None:
            return
        self.mic_level.set(min(1, self.microphone_test.current_amplitude*5))
        if time.monotonic() >= self._meter_deadline:
            self.stop_microphone_test()
            self.mic_status.configure(text=self.t("setup_mic_idle"))
        else:
            self.meter_timer = self.after(80, self.tick_meter)

    def stop_microphone_test(self):
        if self.meter_timer is not None:
            self.after_cancel(self.meter_timer)
            self.meter_timer = None
        if self.microphone_test is not None:
            self.microphone_test.stop_monitor()
            self.microphone_test = None
        if getattr(self, "mic_test_button", None) is not None and self.mic_test_button.winfo_exists():
            self.mic_test_button.configure(text=self.t("setup_test_mic"))
            self.mic_level.set(0)

    def destroy(self):
        self.stop_microphone_test()
        cancel_widget_timers(self)
        try:
            self.grab_release()
        except Exception:
            pass
        super().destroy()
        if self.app.running and not self.app.closing:
            self.app.after_idle(self.app._start_microphone_monitor)
