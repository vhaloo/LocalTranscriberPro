"""Task-first desktop layout; recognition and session logic stay in their controllers."""

from __future__ import annotations

import customtkinter as ctk

from src.meter import TapeMeter
from src.settings import bounded_int
from src.storage import MINIMUM_INSTALL_FREE, format_bytes
from src.storage_ui import StorageDialog
from src.tooltip import ToolTip
from src.transcript_search import TranscriptSearch
from src.translation_ui import TranslationControls
from src.video_ui import VideoOptionsDialog

BG, PANEL, ALT = "#08101F", "#111C32", "#16233D"
TEXT, MUTED, GREEN, BLUE, RED = "#F5F7FB", "#9AA8BE", "#5EE4B7", "#65A8FF", "#F06878"


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
            widget.destroy()
        for column in range(2):
            self.grid_columnconfigure(column, weight=int(column == 1))
        for row in range(5):
            self.grid_rowconfigure(row, weight=int(row == 2))
        self._build_header()
        self.sidebar = ctk.CTkFrame(self, width=242, fg_color=PANEL, corner_radius=16)
        self.sidebar.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(16, 12), pady=(0, 16))
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(0, weight=1)
        self.sidebar_body = ctk.CTkScrollableFrame(self.sidebar, width=214, fg_color="transparent")
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
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 12))
        self.header_frame.grid_columnconfigure(0, weight=1)
        brand = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            brand, text="Local Transcriber Pro", font=("Segoe UI", 23, "bold"), text_color=TEXT
        ).pack(anchor="w")
        self.workspace_context = ctk.CTkLabel(
            brand, text=self.t("workspace_subtitle"), font=("Segoe UI", 12), text_color=MUTED
        )
        self.workspace_context.pack(anchor="w")
        controls = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        controls.grid(row=0, column=1, sticky="e")
        specs = (
            ("history_button", "history", lambda: HistoryDialog(self), 90),
            ("help_button", "help", lambda: HelpDialog(self), 60),
            ("updates_button", "workspace_updates", self.check_updates, 36),
            ("language_button", "language_name", self.toggle_language, 44),
            ("settings_button", "settings", self.open_workspace_settings, 115),
        )
        for name, key, action, width in specs:
            button = ctk.CTkButton(
                controls,
                text=self.t(key),
                command=action,
                width=width,
                height=34,
                fg_color=ALT,
                hover_color="#233654",
                corner_radius=9,
            )
            button.pack(side="left", padx=3)
            setattr(self, name, button)
            ToolTip(
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

    def _build_tasks(self):
        self.task_frame = ctk.CTkFrame(self.sidebar_body, fg_color="transparent")
        self.task_frame.grid(row=0, column=0, sticky="ew")
        self.task_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.task_frame,
            text=self.t("workspace_step_source"),
            text_color=MUTED,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 8))
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
            button.grid(row=index, column=0, sticky="ew", pady=3, padx=3)
            ToolTip(button, self.t("task_" + task + "_help") + f"   Ctrl+{index}")
            self.task_buttons[task] = button

    def _build_simple_dashboard(self):
        self.simple_panel = ctk.CTkFrame(self.sidebar_body, fg_color="transparent")
        self.simple_panel.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        self.simple_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.simple_panel,
            text=self.t("workspace_step_model"),
            text_color=MUTED,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=6)
        self.simple_choices = ctk.CTkFrame(self.simple_panel, fg_color="transparent")
        self.simple_choices.grid(row=1, column=0, sticky="ew", pady=6)
        self.simple_choices.grid_columnconfigure(0, weight=1)
        self.quality_control = ctk.CTkSegmentedButton(
            self.simple_choices,
            values=[self.t("quality_best"), self.t("quality_fast")],
            height=32,
            selected_color="#2BB98D",
            unselected_color=ALT,
            command=self._simple_quality_changed,
        )
        self.quality_control.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.quality_control.set(self.t("quality_fast" if self.simple_quality == "fast" else "quality_best"))
        ToolTip(self.quality_control, self.t("workspace_openai_policy"))
        ctk.CTkButton(
            self.simple_choices,
            text=self.t("workspace_choose_model"),
            height=30,
            fg_color=ALT,
            command=self.open_model_selector,
        ).grid(row=1, column=0, sticky="ew")
        self.simple_language_map = {
            self.t("language_auto"): "auto",
            self.t("language_fr"): "fr",
            self.t("language_en"): "en",
        }
        ctk.CTkLabel(
            self.simple_choices,
            text=self.t("spoken_language"),
            text_color=MUTED,
            anchor="w",
            font=("Segoe UI", 11),
        ).grid(row=2, column=0, sticky="ew", pady=(10, 3))
        self.simple_language_control = ctk.CTkSegmentedButton(
            self.simple_choices,
            values=list(self.simple_language_map),
            height=30,
            selected_color="#3576B5",
            unselected_color=ALT,
            command=self._simple_language_changed,
        )
        self.simple_language_control.grid(row=3, column=0, sticky="ew")
        self.simple_language_control.set(
            next(
                (key for key, value in self.simple_language_map.items() if value == self.selected_language),
                self.t("language_auto"),
            )
        )
        ToolTip(self.simple_language_control, self.t("workspace_language_help"))
        self.simple_speaker_switch = ctk.CTkSwitch(
            self.simple_choices,
            text=self.t("voices_separate"),
            variable=self.speaker_var,
            command=self.persist_settings,
            font=("Segoe UI", 11),
            progress_color="#2BB98D",
        )
        self.simple_speaker_switch.grid(row=4, column=0, sticky="w", pady=(10, 2))
        ToolTip(self.simple_speaker_switch, self.t("tip_simple_speakers"))
        self.simple_auto_summary_label = ctk.CTkLabel(
            self.simple_panel,
            text="",
            text_color=GREEN,
            wraplength=200,
            justify="left",
            anchor="w",
            font=("Segoe UI", 11),
        )
        self.simple_auto_summary_label.grid(row=2, column=0, sticky="ew", padx=5, pady=(5, 0))

    def _build_workspace_settings(self):
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.withdraw()
        self.settings_window.title(self.t("settings"))
        self.settings_window.geometry(
            f"{min(1080, self.winfo_screenwidth() - 60)}x{min(680, self.winfo_screenheight() - 80)}"
        )
        self.settings_window.minsize(760, 460)
        self.settings_window.configure(fg_color=BG)
        self.settings_window.protocol("WM_DELETE_WINDOW", self.close_workspace_settings)
        self.settings_window.bind("<Escape>", lambda _event: self.close_workspace_settings() or "break")
        self.settings_window.grid_columnconfigure(0, weight=1)
        self.settings_window.grid_rowconfigure(1, weight=1)
        heading = ctk.CTkFrame(self.settings_window, fg_color="transparent")
        heading.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 4))
        ctk.CTkLabel(
            heading, text=self.t("workspace_settings_help"), font=("Segoe UI", 14), wraplength=760
        ).pack(side="left")
        self.mode_button = ctk.CTkButton(
            heading,
            text=self.t("advanced" if self.ui_mode == "simple" else "simple"),
            width=110,
            command=self.toggle_mode,
            fg_color=ALT,
        )
        self.mode_button.pack(side="right", padx=8)
        tabs = ctk.CTkTabview(self.settings_window, fg_color=PANEL)
        tabs.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        for key in ("workspace_recognition", "workspace_voices", "workspace_storage"):
            tabs.add(self.t(key))
        self.settings_body = ctk.CTkScrollableFrame(
            tabs.tab(self.t("workspace_recognition")), fg_color="transparent"
        )
        self.settings_body.pack(fill="both", expand=True)
        self.settings_body.grid_columnconfigure(0, weight=1)
        self._build_advanced_panel()
        self.voice_settings_host = ctk.CTkScrollableFrame(
            tabs.tab(self.t("workspace_voices")), fg_color="transparent"
        )
        self.voice_settings_host.pack(fill="both", expand=True)
        self.voice_settings_host.grid_columnconfigure(0, weight=1)
        storage = tabs.tab(self.t("workspace_storage"))
        self.storage_output = ctk.CTkEntry(storage, height=34)
        self.storage_output.insert(0, str(self.output_folder))
        self.storage_output.configure(state="readonly")
        self.storage_output.pack(fill="x", padx=16, pady=18)
        self.storage_output_tip = ToolTip(
            self.storage_output, self.t("storage_output_tip", path=self.output_folder)
        )
        ctk.CTkButton(storage, text=self.t("output_folder"), command=self.change_output_folder).pack(
            anchor="w", padx=16
        )
        ctk.CTkButton(storage, text=self.t("storage_short"), command=lambda: StorageDialog(self)).pack(
            anchor="w", padx=16, pady=12
        )
        ctk.CTkLabel(
            storage,
            text=self.t("storage_compact", minimum=format_bytes(MINIMUM_INSTALL_FREE, self.t.language)),
            text_color=GREEN,
            wraplength=700,
            justify="left",
        ).pack(anchor="w", padx=16, pady=12)
        ctk.CTkButton(
            self.settings_window, text=self.t("close"), width=140, command=self.close_workspace_settings
        ).grid(row=2, column=0, pady=(4, 16))

    def open_workspace_settings(self):
        self.settings_window.deiconify()
        self.settings_window.lift()
        self.settings_window.focus_set()
        return "break"

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
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
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
        read.grid(row=1, column=0, sticky="ew", padx=16, pady=(6, 2))
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
        self.mode_button.configure(text=self.t("advanced" if self.ui_mode == "simple" else "simple"))
        self._workspace_refresh()

    def _workspace_refresh(self):
        if not hasattr(self, "empty_state"):
            return
        self.workspace_context.configure(
            text=self.t("workspace_task_" + self.preset) + " · " + self.t("workspace_subtitle")
        )
        self.source_title.grid_remove()
        self.source_help.grid_remove()
        live = self.preset in {"universal", "conference", "dictation"}
        if live:
            self.microphone_panel.grid()
        else:
            self.microphone_panel.grid_remove()
        self.simple_speaker_switch.configure(
            state="disabled" if self.preset == "universal" or self.busy else "normal"
        )
        self.simple_language_control.configure(
            state="disabled" if self.preset == "universal" or self.busy else "normal"
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
        for name in ("source_help", "status_label", "pipeline_label", "live_preview_label"):
            label = getattr(self, name, None)
            if label is not None and label.winfo_exists():
                label.configure(wraplength=width)
        if hasattr(self, "conversation_legend"):
            self.conversation_legend.configure(wraplength=width)

    def _escape_action(self):
        if getattr(self, "transcript_search", None) is not None and self.transcript_search.visible:
            self.transcript_search.hide()
        elif self.settings_window.winfo_viewable():
            self.close_workspace_settings()
        else:
            super()._escape_action()
