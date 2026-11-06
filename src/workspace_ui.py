"""Task-first desktop layout; recognition and session logic stay in their controllers."""

from __future__ import annotations

import customtkinter as ctk

from src.meter import TapeMeter
from src.settings import bounded_int
from src.storage_ui import StorageDialog
from src.tooltip import ToolTip
from src.transcript_search import TranscriptSearch
from src.translation_ui import TranslationControls
from src.ui_lifecycle import cancel_widget_timers
from src.video_ui import VideoOptionsDialog

BG, PANEL, ALT = "#08101F", "#111C32", "#16233D"
TEXT, MUTED, GREEN, BLUE, RED = "#F5F7FB", "#B2BFD2", "#5EE4B7", "#65A8FF", "#F06878"


class WorkspaceMixin:
    """A stable sidebar, source controls, large document and separate settings."""

    def build_ui(self):
        self.workspace_layout = True
        old_search = getattr(self, "transcript_search", None)
        if old_search is not None:
            old_search.dispose()
        audience = getattr(self, "audience_window", None)
        reopen_audience = bool(audience and audience.winfo_exists())
        self.audience_window = None
        for widget in self.winfo_children():
            cancel_widget_timers(widget)
            widget.destroy()
        for column in range(2):
            self.grid_columnconfigure(column, weight=int(column == 1))
        for row in range(5):
            self.grid_rowconfigure(row, weight=int(row == 2))
        self._build_header()
        self.sidebar = ctk.CTkFrame(self, width=236, fg_color=PANEL, corner_radius=16, border_width=1, border_color="#21334B")
        self.sidebar.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(16, 12), pady=(0, 16))
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(0, weight=1)
        self.sidebar_body = ctk.CTkScrollableFrame(self.sidebar, width=208, fg_color="transparent")
        self.sidebar_body.grid(row=0, column=0, sticky="nsew", padx=5, pady=8)
        self.sidebar_body.grid_columnconfigure(0, weight=1)
        self.controls_container = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_container.grid(row=1, column=1, sticky="ew", padx=(0, 16))
        self.controls_container.grid_columnconfigure(0, weight=1)
        self._build_tasks()
        self._build_simple_dashboard()
        self.tools_host = ctk.CTkFrame(self.sidebar_body, fg_color="transparent")
        self.tools_host.grid(row=3, column=0, sticky="ew", pady=(12, 4))
        self.tools_host.grid_columnconfigure(0, weight=1)
        self._build_workspace_settings()
        self._build_source_card()
        self._build_output()
        self._apply_mode_visibility()
        self._refresh_task_styles()
        self._update_source_context()
        self._update_hardware_chip()
        self._update_model_indicators()
        self._setup_dnd_target()
        self._build_blocking_overlay()
        self.bind("<Control-f>", lambda _event: self.transcript_search.show(), add=False)
        self.bind("<Control-comma>", lambda _event: self.open_workspace_settings(), add=False)
        for number, task in enumerate(("files", "universal", "conference", "dictation", "link"), 1):
            self.bind(f"<Control-Key-{number}>", lambda _event, value=task: self.select_preset(value))
        if not getattr(self, "_workspace_resize_bound", False):
            self.bind("<Configure>", self._workspace_resize, add="+")
            self._workspace_resize_bound = True
        if reopen_audience:
            self.after_idle(self.open_audience)

    def _build_header(self):
        from src.gui import HelpDialog, HistoryDialog

        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 8))
        self.header_frame.grid_columnconfigure(0, weight=1)
        brand = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            brand, text="Local Transcriber Pro", font=("Segoe UI", 21, "bold"), text_color=TEXT
        ).pack(anchor="w")
        self.workspace_context = ctk.CTkLabel(
            brand, text=self.t("workspace_subtitle"), font=("Segoe UI", 13), text_color=GREEN
        )
        self.workspace_context.pack(anchor="w")
        controls = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        controls.grid(row=0, column=1, sticky="e")
        specs = (
            ("history_button", "history", lambda: HistoryDialog(self), 90),
            ("help_button", "help", lambda: HelpDialog(self), 60),
            ("updates_button", "workspace_updates", self.open_update_or_check, 36),
            ("language_button", "language_name", lambda: self.open_workspace_settings("settings_general"), 44),
            ("settings_button", "settings", self.open_workspace_settings, 115),
        )
        for name, key, action, width in specs:
            button = ctk.CTkButton(
                controls,
                text=self.t.language.upper()+" ▾" if key == "language_name" else self.t(key),
                command=action,
                width=width,
                height=34,
                fg_color=ALT,
                hover_color="#233654",
                corner_radius=9,
            )
            button.pack(side="left", padx=3)
            setattr(self, name, button)
            tip = ToolTip(
                button,
                self.t(
                    "workspace_settings_help"
                    if key == "settings"
                    else "tip_history"
                    if key == "history"
                    else "tip_help"
                    if key == "help"
                    else "updates"
                    if key == "workspace_updates"
                    else "tip_language"
                ),
            )
            if key == "workspace_updates":
                self.update_tooltip = tip
        self._refresh_update_badge()

    def _build_tasks(self):
        self.task_frame = ctk.CTkFrame(self.sidebar_body, fg_color="transparent")
        self.task_frame.grid(row=0, column=0, sticky="ew")
        self.task_frame.grid_columnconfigure(0, weight=1)
        wizard = ctk.CTkButton(self.task_frame, text=self.t("setup_short") + "  →", height=37,
                              fg_color="#205B50", hover_color="#2A7564", anchor="w", command=self.open_guided_setup)
        wizard.grid(row=0, column=0, sticky="ew", padx=3, pady=(2, 12))
        ToolTip(wizard, self.t("setup_subtitle"), title=self.t("setup_open"))
        self.setup_button = wizard
        ctk.CTkLabel(
            self.task_frame,
            text=self.t("workspace_step_source"),
            text_color=MUTED,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=6, pady=(4, 8))
        self.task_buttons = {}
        self.simple_task_buttons = {}
        for index, task in enumerate(("files", "universal", "conference", "dictation", "link"), 1):
            button = ctk.CTkButton(
                self.task_frame,
                text=self.t("workspace_task_" + task),
                anchor="w",
                command=lambda value=task: self.select_preset(value),
                height=38,
                corner_radius=9,
                font=("Segoe UI", 13, "bold"),
            )
            button.grid(row=index+1, column=0, sticky="ew", pady=3, padx=3)
            ToolTip(button, self.t("task_" + task + "_help") + f"   Ctrl+{index}")
            self.task_buttons[task] = button

    def _build_simple_dashboard(self):
        self.simple_panel = ctk.CTkFrame(self.sidebar_body, fg_color="transparent")
        self.simple_panel.grid(row=1, column=0, sticky="ew", pady=(15, 0))
        self.simple_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.simple_panel, text=self.t("profile_label"), text_color=MUTED,
                     font=("Segoe UI", 11, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=6)
        self.simple_choices = ctk.CTkFrame(self.simple_panel, fg_color="transparent")
        self.simple_choices.grid(row=1, column=0, sticky="ew", pady=6)
        self.simple_choices.grid_columnconfigure(0, weight=1)
        self.quality_control = ctk.CTkOptionMenu(self.simple_choices,
            values=[self.t("quality_best"), self.t("quality_fast"), self.t("quality_coverage")], height=34,
            fg_color="#214C45", button_color="#276B58", command=self._simple_quality_changed)
        self.quality_control.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        self.quality_control.set(self.t("quality_best"))
        ToolTip(self.quality_control, self.t("setting_profile_help"), title=self.t("profile_label"))
        choose = ctk.CTkButton(self.simple_choices, text=self.t("workspace_choose_model"), height=30,
                               fg_color=ALT, command=self.open_model_selector)
        choose.grid(row=1, column=0, sticky="ew")
        ToolTip(choose, self.t("model_manage_help"))
        self.prepare_model_button = ctk.CTkButton(self.simple_choices, text=self.t("model_prepare"), height=30,
                                                fg_color=ALT, command=self.prepare_selected_model)
        self.prepare_model_button.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ToolTip(self.prepare_model_button, self.t("model_prepare_help"))
        self.simple_auto_summary_label = ctk.CTkLabel(self.simple_panel, text="", text_color=GREEN,
            wraplength=196, justify="left", anchor="w", font=("Segoe UI", 11))
        self.simple_auto_summary_label.grid(row=2, column=0, sticky="ew", padx=5, pady=(6, 0))

    def _build_workspace_settings(self):
        from src.settings_ui import build_settings_window

        build_settings_window(self)

    def open_workspace_settings(self, section=None):
        if section in getattr(self, "settings_pages", {}):
            self.settings_tabs.set(self.t(section))
        self.settings_window.deiconify()
        self.settings_window.lift()
        self.settings_window.focus_set()
        return "break"

    def _configuration_idle(self):
        return not (self.busy or self.recorder.recording or self.recorder.segmenting or self.model_preloading
                    or getattr(self, "model_download_cancel", None) is not None
                    or any(thread.is_alive() for thread in getattr(self, "tool_threads", []))
                    or (getattr(self, "speech_thread", None) is not None and self.speech_thread.is_alive()))

    def maybe_show_guided_setup(self):
        if self.running and self._configuration_idle() and not self.transcript_data:
            self.open_guided_setup()

    def open_guided_setup(self):
        from tkinter import messagebox

        from src.setup_ui import SetupWizard

        if not self._configuration_idle():
            messagebox.showinfo(self.t("setup_title"), self.t("setup_busy"), parent=self)
            return
        existing = getattr(self, "_setup_wizard", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            return existing
        self._commit_editor_changes()
        if self.settings_window.winfo_viewable():
            self.close_workspace_settings()
        self._setup_wizard = SetupWizard(self)
        return self._setup_wizard

    def set_ui_language(self, preference, *, reopen_settings=False):
        from tkinter import messagebox

        if preference not in {"auto", "en", "fr"}:
            return False
        if not self._configuration_idle():
            if hasattr(self, "ui_language_combo"):
                self.ui_language_combo.set(next(label for label, code in self.ui_language_values.items()
                                                if code == self.settings.get("ui_language", "auto")))
            messagebox.showinfo(self.t("ui_language_setting"), self.t("setup_busy"), parent=self)
            return False
        self._commit_editor_changes()
        self.persist_settings()
        self.settings.set("ui_language", preference, save=True)
        self.t.set_language(preference)
        self.build_ui()
        self.render_transcript()
        if reopen_settings:
            self.open_workspace_settings("settings_general")
        return True

    def apply_guided_setup(self, plan):
        import copy
        from tkinter import messagebox

        if not self._configuration_idle():
            messagebox.showinfo(self.t("setup_title"), self.t("setup_busy"), parent=self)
            return False
        self._commit_editor_changes()
        previous = copy.deepcopy(self.settings.data)
        try:
            self.settings.update(plan, save=True)
        except OSError as error:
            self.settings.data = previous
            messagebox.showerror(self.t("settings"), self.t("job_error", error=str(error)), parent=self)
            return False
        self.preset = plan["preset"]
        self.selected_model_id = plan.get("model", self.selected_model_id)
        self.selected_device = plan.get("device", self.selected_device)
        self.simple_quality = plan.get("simple_quality", self.simple_quality)
        self.selected_language = plan["spoken_language"]
        self.ui_mode = plan["ui_mode"]
        self.translation_target, self.conversation_partner, self.translation_third = (
            plan["translation_target"], plan["conversation_partner"], plan["translation_third"])
        self.saved_microphone = plan["microphone"]
        self.conversation_font_size = plan["conversation_font_size"]
        self.translate_var.set(plan["translate"])
        self.speaker_var.set(plan["speaker_detection"])
        self.keep_audio_var.set(plan["keep_recording_audio"])
        self.speech_click_var.set(plan[self._click_speech_setting()])
        self.chunk_var.set(str(plan["chunk_seconds"]))
        self.beam_var.set(str(plan["beam_size"]))
        self.t.set_language(plan["ui_language"])
        self.build_ui()
        self.render_transcript()
        self.preload_selected_model()
        self._set_status(self.t("setup_applied"))
        return True

    def close_workspace_settings(self):
        self.chunk_var.set(
            str(bounded_int(self.chunk_var.get(), self.settings.get("chunk_seconds", 30), 5, 60))
        )
        self.beam_var.set(str(bounded_int(self.beam_var.get(), self.settings.get("beam_size", 8), 1, 10)))
        self.persist_settings()
        self.settings_window.withdraw()

    def _build_source_card(self):
        self.source_card = ctk.CTkFrame(self.controls_container, fg_color=PANEL, corner_radius=16)
        self.source_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.source_card.grid_columnconfigure(0, weight=1)
        self.source_title = ctk.CTkLabel(self.source_card, text="", font=("Segoe UI", 18, "bold"), anchor="w")
        self.source_title.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 1))
        self.source_help = ctk.CTkLabel(
            self.source_card,
            text="",
            text_color=MUTED,
            font=("Segoe UI", 12),
            justify="left",
            anchor="w",
            wraplength=750,
        )
        self.source_help.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))
        self.source_quick_settings = ctk.CTkFrame(self.source_card, fg_color="transparent")
        self.source_quick_settings.grid(row=1, column=0, sticky="ew", padx=18, pady=(5, 10))
        self.source_quick_settings.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.source_quick_settings, text=self.t("spoken_language"), text_color=MUTED,
                     font=("Segoe UI", 12)).grid(row=0, column=0, padx=(0, 10))
        self.simple_language_map = self.language_display_map
        self.simple_language_control = ctk.CTkComboBox(self.source_quick_settings,
            values=list(self.simple_language_map), state="readonly", height=32, fg_color=ALT,
            command=self._simple_language_changed)
        self.simple_language_control.set(next((label for label, code in self.simple_language_map.items()
                                               if code == self.selected_language), next(iter(self.simple_language_map))))
        self.simple_language_control.grid(row=0, column=1, sticky="ew")
        ToolTip(self.simple_language_control, self.t("source_language_help"), title=self.t("spoken_language"))
        self.simple_speaker_switch = ctk.CTkSwitch(self.source_quick_settings, text=self.t("voices_separate"),
            variable=self.speaker_var, command=self.persist_settings, font=("Segoe UI", 11), width=150)
        self.simple_speaker_switch.grid(row=0, column=2, padx=(14, 0))
        ToolTip(self.simple_speaker_switch, self.t("tip_speakers"))
        self.file_controls = ctk.CTkFrame(self.source_card, fg_color="transparent")
        self.file_controls.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.file_controls.grid_columnconfigure(0, weight=1)
        self.file_hint = ctk.CTkLabel(
            self.file_controls, text=self.t("drop_help"), text_color=MUTED, wraplength=410, anchor="w"
        )
        self.file_hint.grid(row=0, column=0, sticky="w")
        self.choose_button = ctk.CTkButton(
            self.file_controls,
            text=self.t("choose_files"),
            height=38,
            width=180,
            fg_color="#3478BA",
            command=self.choose_files,
        )
        self.choose_button.grid(row=0, column=1, padx=(8, 0))
        ToolTip(self.choose_button, self.t("tip_choose"))
        self.record_controls = ctk.CTkFrame(self.source_card, fg_color="transparent")
        self.record_controls.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))
        self.record_controls.grid_columnconfigure(0, weight=1)
        self.microphone_combo = ctk.CTkComboBox(
            self.record_controls,
            values=[],
            state="readonly",
            height=34,
            fg_color=ALT,
            command=self._microphone_changed,
            dropdown_fg_color=ALT,
        )
        self.microphone_combo.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ToolTip(self.microphone_combo, self.t("tip_microphone"))
        for name, key, command, color, state in (
            ("record_button", "record", self.start_recording, "#B13B53", "normal"),
            ("pause_button", "pause", self.toggle_pause, "#675128", "disabled"),
            ("stop_button", "stop", self.stop_recording, "#5A2939", "disabled"),
        ):
            index = {"record_button": 1, "pause_button": 2, "stop_button": 3}[name]
            button = ctk.CTkButton(
                self.record_controls,
                text=self.t(key),
                command=command,
                state=state,
                height=36,
                width=105,
                fg_color=color,
            )
            button.grid(row=0, column=index, padx=3)
            setattr(self, name, button)
            ToolTip(button, self.t("tip_" + key))
        self.microphone_panel = ctk.CTkFrame(self.source_card, fg_color=BG, corner_radius=8)
        self.microphone_panel.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 8))
        self.microphone_panel.grid_columnconfigure(1, weight=1)
        info = ctk.CTkFrame(self.microphone_panel, fg_color="transparent")
        info.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.microphone_status_label = ctk.CTkLabel(
            info, text=self.t("microphone_ready"), text_color=GREEN, font=("Segoe UI", 11)
        )
        self.microphone_status_label.pack(anchor="w")
        self.microphone_selection_label = ctk.CTkLabel(
            info, text="", font=("Segoe UI", 10), wraplength=230, justify="left"
        )
        self.microphone_privacy_label = ctk.CTkLabel(info, text="", height=0)
        self.microphone_meter = TapeMeter(self.microphone_panel, height=48)
        self.microphone_meter.grid(row=0, column=1, sticky="ew", padx=10, pady=4)
        ToolTip(self.microphone_panel, self.t("microphone_level_only"))
        self.link_controls = ctk.CTkFrame(self.source_card, fg_color="transparent")
        self.link_controls.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.link_controls.grid_columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(
            self.link_controls, placeholder_text=self.t("url_placeholder"), height=38, fg_color=ALT
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.url_entry.bind("<Return>", lambda _event: self.start_link())
        self.link_button = ctk.CTkButton(
            self.link_controls, text=self.t("download_start"), width=190, height=38, command=self.start_link
        )
        self.link_button.grid(row=0, column=1)
        for column, key, command in (
            (0, "video_options", lambda: VideoOptionsDialog(self)),
            (1, "video_local_file", self.choose_files),
        ):
            ctk.CTkButton(
                self.link_controls, text=self.t(key), command=command, height=27, fg_color=ALT, width=190
            ).grid(row=1, column=column, sticky="w", pady=(7, 0))
        ToolTip(self.url_entry, self.t("video_url_tip"))
        ToolTip(self.link_button, self.t("tip_link"))
        self.translation_controls = TranslationControls(self, self.source_card)
        self.translation_controls.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.translation_controls.guide.grid_remove()
        self.translation_controls.pair_label.configure(wraplength=420, justify="left")
        self._populate_microphones()

    def _build_output(self):
        self.output_card = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=16)
        self.output_card.grid(row=2, column=1, sticky="nsew", padx=(0, 16), pady=(0, 16))
        self.output_card.grid_columnconfigure(0, weight=1)
        self.output_card.grid_rowconfigure(3, weight=1)
        toolbar = ctk.CTkFrame(self.output_card, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(8, 0))
        toolbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(toolbar, text=self.t("transcript"), font=("Segoe UI", 17, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        for index, name, key, command in (
            (1, "copy_button", "copy", self.copy_transcript),
            (2, "clear_button", "clear", self.clear_transcript),
            (4, "vocabulary_button", "vocabulary", self.edit_vocabulary),
        ):
            button = ctk.CTkButton(
                toolbar, text=self.t(key), command=command, width=85, height=29, fg_color=ALT
            )
            button.grid(row=0, column=index, padx=3)
            setattr(self, name, button)
            ToolTip(
                button,
                self.t("tip_copy" if key == "copy" else "tip_clear" if key == "clear" else "vocabulary"),
            )
        self.export_menu = ctk.CTkOptionMenu(
            toolbar,
            values=[self.t("export_" + value) for value in ("txt", "srt", "vtt", "json", "csv")],
            command=self.export_selected,
            width=140,
            height=29,
            fg_color="#238765",
            button_color="#238765",
        )
        self.export_menu.set(self.t("export"))
        self.export_menu.grid(row=0, column=3, padx=3)
        self._build_conversation_toolbar(toolbar)
        read = ctk.CTkFrame(self.output_card, fg_color="transparent")
        read.grid(row=1, column=0, sticky="ew", padx=16, pady=(3, 1))
        self._click_speech_checkbox(read).pack(side="left", padx=(0, 10))
        for key, command in (
            ("speech_read", self.read_transcript_lines),
            ("speech_stop", self.stop_speaking),
        ):
            ctk.CTkButton(
                read,
                text=self.t(key),
                command=command,
                height=27,
                width=120 if key == "speech_read" else 65,
                fg_color=ALT,
            ).pack(side="left", padx=3)
        ctk.CTkButton(
            read,
            text=self.t("workspace_find"),
            command=lambda: self.transcript_search.show(),
            width=100,
            height=27,
            fg_color=ALT,
        ).pack(side="right")
        self.preview_host = ctk.CTkFrame(self.output_card, fg_color="transparent", height=1)
        self.preview_host.grid(row=2, column=0, sticky="ew", padx=16)
        self.preview_host.grid_columnconfigure(0, weight=1)
        self.search_host = ctk.CTkFrame(self.preview_host, fg_color="transparent")
        self.search_host.grid(row=0, column=0, sticky="ew")
        self.textbox = ctk.CTkTextbox(
            self.output_card,
            height=300,
            fg_color="#0B1425",
            text_color=TEXT,
            corner_radius=10,
            border_width=1,
            border_color="#243653",
            font=("Segoe UI", 15),
            wrap="word",
        )
        self.textbox.grid(row=3, column=0, sticky="nsew", padx=14, pady=(7, 8))
        self._bind_click_speech(self.textbox)
        self.transcript_search = TranscriptSearch(self, self.textbox, self.search_host)
        self.empty_state = ctk.CTkFrame(self.textbox, fg_color="#0B1425")
        self.empty_title = ctk.CTkLabel(
            self.empty_state, text=self.t("workspace_empty_title"), font=("Segoe UI", 22, "bold")
        )
        self.empty_title.pack(pady=(0, 8))
        self.empty_help = ctk.CTkLabel(
            self.empty_state,
            text="",
            wraplength=410,
            justify="center",
            text_color=MUTED,
            font=("Segoe UI", 13),
        )
        self.empty_help.pack(pady=(0, 16))
        self.empty_action = ctk.CTkButton(self.empty_state, text="", command=self.choose_files, height=38)
        self.empty_action.pack()
        progress = ctk.CTkFrame(self.output_card, fg_color="transparent")
        progress.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 5))
        progress.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(
            progress,
            text=self.t("progress_ready"),
            anchor="w",
            justify="left",
            wraplength=650,
            text_color=MUTED,
            font=("Segoe UI", 11),
        )
        self.status_label.grid(row=0, column=0, sticky="ew")
        self.eta_label = ctk.CTkLabel(progress, text="", font=("Segoe UI", 11), text_color=MUTED)
        self.eta_label.grid(row=0, column=1, padx=8)
        self.cancel_button = ctk.CTkButton(
            progress,
            text=self.t("cancel_job"),
            width=85,
            height=27,
            state="disabled",
            command=self.cancel_job,
            fg_color="#5A2430",
        )
        self.cancel_button.grid(row=0, column=2)
        self.progress_bar = ctk.CTkProgressBar(self.output_card, height=4, progress_color=GREEN, fg_color=ALT)
        self.progress_bar.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.progress_bar.set(0)
        self._workbench_controls(self.tools_host)
        self.preview_host.grid_remove()
        services = ctk.CTkFrame(self.sidebar_body, fg_color="transparent")
        services.grid(row=4, column=0, sticky="ew", pady=(12, 6))
        services.grid_columnconfigure(0, weight=1)
        from src.gui import HardwareDialog, ModelManagerDialog

        for index, name, key, command in (
            (0, "models_button", "model_manager", lambda: ModelManagerDialog(self)),
            (1, "storage_button", "storage_short", lambda: StorageDialog(self)),
            (2, "hardware_btn", "hardware_details", lambda: HardwareDialog(self)),
        ):
            button = ctk.CTkButton(services, text=self.t(key), command=command, height=29, fg_color=ALT)
            button.grid(row=index, column=0, sticky="ew", pady=3)
            setattr(self, name, button)
        ToolTip(self.storage_button, self.t("storage_summary_tip"))
        self.workspace_badge = ctk.CTkLabel(
            services,
            text=self.t("workspace_local"),
            text_color=GREEN,
            font=("Segoe UI", 10),
            wraplength=200,
            justify="left",
        )
        self.workspace_badge.grid(row=3, column=0, pady=8, sticky="w")

    def _apply_mode_visibility(self):
        if self.reading_view:
            self.sidebar.grid_remove()
            self.controls_container.grid_remove()
            self.header_frame.grid_remove()
            self.output_card.grid(row=0, column=0, rowspan=3, columnspan=2, sticky="nsew", padx=12, pady=12)
        else:
            self.sidebar.grid()
            self.controls_container.grid()
            self.header_frame.grid()
            self.output_card.grid(
                row=2, column=1, rowspan=1, columnspan=1, sticky="nsew", padx=(0, 16), pady=(0, 16)
            )
        self.mode_button.configure(text=self.t("advanced_show" if self.ui_mode == "simple" else "advanced_hide"))
        for card in getattr(self, "_advanced_setting_cards", []):
            card.grid() if self.ui_mode == "advanced" else card.grid_remove()
        self._workspace_refresh()

    def _workspace_refresh(self):
        if not hasattr(self, "empty_state"):
            return
        self.workspace_context.configure(
            text=self.t("workspace_task_" + self.preset) + " · " + self.t("workspace_subtitle")
        )
        self.source_title.grid_remove()
        ToolTip(self.source_card, self.t("action_"+self.preset), title=self.t("workspace_task_"+self.preset))
        self.source_help.grid_remove()
        self.source_quick_settings.grid_remove() if self.preset == "universal" else self.source_quick_settings.grid()
        live = self.preset in {"universal", "conference", "dictation"}
        if live:
            self.microphone_panel.grid()
        else:
            self.microphone_panel.grid_remove()
        self.simple_speaker_switch.configure(
            state="disabled" if self.preset == "universal" or self.busy or self.recorder.recording else "normal"
        )
        self._refresh_session_tools()
        self.simple_language_control.configure(
            state="disabled" if self.preset == "universal" or self.busy or self.recorder.recording else "readonly"
        )
        empty = not self.textbox.get("1.0", "end-1c").strip()
        if empty and not self.busy and not self.recorder.recording:
            self.empty_help.configure(text=self.t("action_" + self.preset))
            key = "choose_files" if self.preset == "files" else "record" if live else "workspace_enter_url"
            action = (
                self.choose_files
                if self.preset == "files"
                else self.start_recording
                if live
                else self.url_entry.focus_set
            )
            self.empty_action.configure(text=self.t(key), command=action)
            self.empty_state.place(relx=0.5, rely=0.48, anchor="center")
        else:
            self.empty_state.place_forget()
        if hasattr(self, "transcript_search"):
            self.transcript_search.refresh()

    def _workspace_resize(self, event):
        if event.widget is not self or not hasattr(self, "source_help"):
            return
        width = max(320, event.width - (70 if self.reading_view else 320))
        for name in ("source_help", "status_label", "pipeline_label", "live_preview_label", "conversation_legend"):
            label = getattr(self, name, None)
            if label is not None and label.winfo_exists():
                label.configure(wraplength=width)

    def _escape_action(self):
        if getattr(self, "transcript_search", None) is not None and self.transcript_search.visible:
            self.transcript_search.hide()
        elif self.settings_window.winfo_viewable():
            self.close_workspace_settings()
        else:
            super()._escape_action()

    def _toggle_session_tools(self):
        self.settings.set("tools_expanded", not self.settings.get("tools_expanded", False), save=True)
        self._refresh_session_tools()

    def _refresh_session_tools(self):
        buttons = getattr(self, "session_tool_buttons", {})
        expanded = self.settings.get("tools_expanded", False)
        primary = {"audience", "typed_reply"} if self.preset == "universal" else {"review_turns"}
        for key, button in buttons.items():
            button.pack_forget()
            if expanded or key in primary:
                button.pack(fill="x", pady=3)
        if hasattr(self, "session_tools_toggle"):
            self.session_tools_toggle.configure(text=self.t("workspace_tools_less" if expanded else "workspace_tools_more"))
