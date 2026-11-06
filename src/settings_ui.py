"""Purpose-based settings with visible explanations and focused controls."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from src.i18n import detect_ui_language, system_ui_locale
from src.models import model_label
from src.storage import MINIMUM_INSTALL_FREE, format_bytes
from src.storage_ui import StorageDialog
from src.tooltip import ToolTip
from src.ui_lifecycle import ManagedToplevel

BG, PANEL, ALT = "#08101F", "#111C32", "#1A2942"
TEXT, MUTED, GREEN = "#F5F7FB", "#B2BFD2", "#5EE4B7"


class SettingsSection(ctk.CTkFrame):
    def __init__(self, master, title, *, row):
        super().__init__(master, fg_color=PANEL, corner_radius=14, border_width=1, border_color="#263750")
        self.grid(row=row, column=0, sticky="ew", padx=5, pady=7)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=title, text_color=TEXT, font=("Segoe UI", 17, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=18, pady=(14, 6))
        self.next_row = 1

    def field(self, title, help_text, *, t):
        field = ctk.CTkFrame(self, fg_color="transparent")
        field.grid(row=self.next_row, column=0, sticky="ew", padx=18, pady=(6, 13))
        field.grid_columnconfigure(0, weight=1)
        self.next_row += 1
        heading = ctk.CTkFrame(field, fg_color="transparent")
        field.heading = heading
        heading.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(heading, text=title, font=("Segoe UI", 14, "bold"), anchor="w").pack(side="left")
        badge = ctk.CTkButton(heading, text="?", width=25, height=25, fg_color=ALT,
                             command=lambda: messagebox.showinfo(title, help_text, parent=self.winfo_toplevel()))
        badge.pack(side="right", padx=(6, 0))
        ToolTip(badge, help_text, title=title)
        ctk.CTkLabel(field, text=help_text, text_color=MUTED, justify="left", anchor="w",
                     wraplength=620, font=("Segoe UI", 12)).grid(row=1, column=0, sticky="ew", pady=(2, 7))
        content = ctk.CTkFrame(field, fg_color="transparent")
        content.grid(row=2, column=0, sticky="ew")
        content.grid_columnconfigure(0, weight=1)
        # Help applies to labels as well as the control and remains keyboard accessible.
        ToolTip(heading, help_text, title=title)
        return content


def option(section, app, label, help_key, values, selected, callback, *, variable=None, editable=False):
    help_text = app.t(help_key)
    host = section.field(app.t(label), help_text, t=app.t)
    combo = ctk.CTkComboBox(host, values=values, variable=variable, command=callback, height=35,
                           state="normal" if editable else "readonly", fg_color=ALT,
                           border_color="#3A506D", dropdown_fg_color=ALT, font=("Segoe UI", 13))
    combo.set(selected)
    combo._ltp_readonly = not editable
    combo.grid(row=0, column=0, sticky="ew")
    ToolTip(combo, help_text, title=app.t(label))
    return combo


def check(section, app, label, help_key, variable, callback):
    help_text = app.t(help_key)
    host = section.field(app.t(label), help_text, t=app.t)
    control = ctk.CTkSwitch(host.master.heading, text="", width=51, variable=variable, command=callback,
                           progress_color="#2AAE87", font=("Segoe UI", 13))
    control.pack(side="right", padx=(8, 12))
    host.grid_remove()
    ToolTip(control, help_text, title=app.t(label))
    return control


def build_settings_window(app):
    window = app.settings_window = ManagedToplevel(app)
    window.withdraw()
    window.t = app.t
    window.title(app.t("settings"))
    window.geometry(f"{min(920, app.winfo_screenwidth()-60)}x{min(760, app.winfo_screenheight()-80)}")
    window.minsize(740, 480)
    window.configure(fg_color=BG)
    window.protocol("WM_DELETE_WINDOW", app.close_workspace_settings)
    window.bind("<Escape>", lambda _event: app.close_workspace_settings() or "break")
    window.grid_columnconfigure(0, weight=1)
    window.grid_rowconfigure(1, weight=1)
    header = ctk.CTkFrame(window, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=24, pady=(19, 8))
    ctk.CTkLabel(header, text=app.t("settings"), font=("Segoe UI", 24, "bold"), anchor="w").pack(anchor="w")
    ctk.CTkLabel(header, text=app.t("settings_intro"), wraplength=820, justify="left", text_color=MUTED,
                 font=("Segoe UI", 12)).pack(anchor="w", pady=(4, 0))
    app.settings_tabs = ctk.CTkTabview(window, fg_color=BG, segmented_button_selected_color="#246C60")
    app.settings_tabs.grid(row=1, column=0, sticky="nsew", padx=14, pady=0)
    app.settings_pages = {}
    for key in ("settings_general", "settings_recognition", "settings_text_voice", "settings_files"):
        tab = app.settings_tabs.add(app.t(key))
        body = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1)
        app.settings_pages[key] = body
    app.settings_body = app.settings_pages["settings_recognition"]
    app._advanced_setting_cards = []
    build_general_settings(app)
    build_recognition_settings(app)
    build_text_settings(app)
    build_file_settings(app)
    close = ctk.CTkButton(window, text=app.t("close"), width=150, height=36, command=app.close_workspace_settings)
    close.grid(row=2, column=0, pady=(8, 16))
    ToolTip(close, app.t("settings_intro"))


def build_general_settings(app):
    body = app.settings_pages["settings_general"]
    section = SettingsSection(body, app.t("settings_group_language"), row=0)
    labels = {app.t("ui_language_auto"): "auto", "Français": "fr", "English": "en"}
    app.ui_language_values = labels
    selected = next(label for label, value in labels.items() if value == app.settings.get("ui_language", "auto"))
    app.ui_language_combo = option(section, app, "ui_language_setting", "ui_language_help", list(labels), selected,
                                   lambda label: app.set_ui_language(labels[label], reopen_settings=True))
    detected = "Français" if detect_ui_language() == "fr" else "English"
    ctk.CTkLabel(section, text=app.t("ui_language_detected", locale=system_ui_locale(), language=detected),
                 text_color=GREEN, anchor="w").grid(row=section.next_row, column=0, sticky="ew", padx=18, pady=(0, 12))
    section.next_row += 1
    host = section.field(app.t("setup_open"), app.t("setup_subtitle"), t=app.t)
    button = ctk.CTkButton(host, text=app.t("setup_short"), command=app.open_guided_setup, height=36, fg_color="#246C60")
    button.grid(row=0, column=0, sticky="w")
    ToolTip(button, app.t("setup_subtitle"), title=app.t("setup_open"))
    host = section.field(app.t("settings_view"), app.t("advanced_help"), t=app.t)
    app.mode_button = ctk.CTkButton(host, text=app.t("advanced_show"), command=app.toggle_mode, height=34, fg_color=ALT)
    app.mode_button.grid(row=0, column=0, sticky="w")
    ToolTip(app.mode_button, app.t("advanced_help"))
    updates = SettingsSection(body, app.t("settings_group_updates"), row=1)
    app.update_var = ctk.BooleanVar(value=app.settings.get("check_updates", True))
    app.auto_update_var = ctk.BooleanVar(value=app.settings.get("auto_install_updates", True))
    check(updates, app, "update_automatic", "tip_update_automatic", app.update_var, app._update_preferences_changed)
    check(updates, app, "update_auto_install", "tip_update_auto_install", app.auto_update_var, app._update_preferences_changed)


def build_recognition_settings(app):
    main = app.advanced_panel = SettingsSection(app.settings_body, app.t("settings_group_model"), row=0)
    model = main.field(app.t("model"), app.t("setting_profile_help"), t=app.t)
    app.model_button = ctk.CTkButton(model, text=model_label(app.selected_model_id, app.t.language),
                                    command=app.open_model_selector, height=36, fg_color=ALT)
    app.model_button.grid(row=0, column=0, sticky="ew")
    ToolTip(app.model_button, app.t("model_help"), title=app.t("model"))
    app.language_display_map = app._language_display_map()
    language_label = next((label for label, code in app.language_display_map.items() if code == app.selected_language),
                          next(iter(app.language_display_map)))
    app.language_combo = option(main, app, "spoken_language", "source_language_help", list(app.language_display_map),
                                 language_label, app._spoken_language_changed)
    device = SettingsSection(app.settings_body, app.t("device"), row=1)
    app._advanced_setting_cards.append(device)
    app.device_display_map = app._device_display_map()
    selected = next(label for label, code in app.device_display_map.items() if code == app.selected_device)
    app.device_combo = option(device, app, "device", "cpu_virtual_help", list(app.device_display_map), selected, app._device_changed)
    capture = SettingsSection(app.settings_body, app.t("settings_group_capture"), row=2)
    if not hasattr(app, "overlap_var"):
        app.overlap_var = ctk.BooleanVar(value=app.settings.get("overlap_separation", False))
    for label, variable, help_key in (("speaker_detection", app.speaker_var, "tip_speakers"),
                                      ("vad", app.vad_var, "tip_vad"), ("cleanup", app.cleanup_var, "tip_cleanup")):
        control = check(capture, app, label, help_key, variable, app.persist_settings)
        if label == "speaker_detection":
            app.speaker_settings_switch = control
    check(capture, app, "overlap_toggle", "tip_overlap", app.overlap_var, app._overlap_changed)
    tuning = SettingsSection(app.settings_body, app.t("settings_group_tuning"), row=3)
    app._advanced_setting_cards.append(tuning)
    app.chunk_combo = option(tuning, app, "chunk", "tip_chunk", ["5", "8", "10", "12", "15", "20", "30", "45", "60"],
                              app.chunk_var.get(), lambda _: app.persist_settings(), variable=app.chunk_var, editable=True)
    app.beam_combo = option(tuning, app, "beam", "setting_beam_help", ["1", "3", "5", "8", "10"],
                             app.beam_var.get(), lambda _: app.persist_settings(), variable=app.beam_var, editable=True)


def build_text_settings(app):
    body = app.settings_pages["settings_text_voice"]
    translation = SettingsSection(body, app.t("translate"), row=0)
    check(translation, app, "translate", "tip_translate", app.translate_var, app._translation_toggled)
    host = translation.field(app.t("translation_preferences"), app.t("translation_model_resources"), t=app.t)
    button = ctk.CTkButton(host, text=app.t("translation_preferences"), command=app.offline_prepare, height=34, fg_color=ALT)
    button.grid(row=0, column=0, sticky="w")
    ToolTip(button, app.t("offline_prepare_help"))
    appearance = SettingsSection(body, app.t("settings_group_format"), row=1)
    sizes = sorted({14, 16, 18, 22, 26, 30, 36, 42, 48, app.conversation_font_size})
    app.transcript_font_combo = option(appearance, app, "setup_large_text", "setting_font_help", list(map(str, sizes)),
                                       str(app.conversation_font_size),
                                       lambda value: app.change_transcript_font(int(value)-app.conversation_font_size))
    app.layout_display_map = {app.t("layout_blocks"): "blocks", app.t("layout_lines"): "lines"}
    selected = next(label for label, value in app.layout_display_map.items() if value == app.transcript_layout)
    app.layout_combo = option(appearance, app, "transcript_layout", "tip_layout", list(app.layout_display_map), selected, app._layout_changed)
    app.timestamps_check = check(appearance, app, "show_timestamps", "tip_timestamps", app.show_timestamps_var, app._format_options_changed)
    app.duration_check = check(appearance, app, "show_duration", "tip_duration", app.show_duration_var, app._format_options_changed)
    if not hasattr(app, "show_confidence_var"):
        app.show_confidence_var = ctk.BooleanVar(value=app.settings.get("show_confidence", True))
    check(appearance, app, "confidence_toggle", "tip_confidence", app.show_confidence_var, app._confidence_changed)
    voice_section = SettingsSection(body, app.t("settings_group_voices"), row=2)
    host = voice_section.field(app.t("speech_bank"), app.t("setting_speech_help"), t=app.t)
    app.voice_settings_host = ctk.CTkFrame(host, fg_color="transparent")
    app.voice_settings_host.grid(row=0, column=0, sticky="ew")
    app.voice_settings_host.grid_columnconfigure(0, weight=1)


def build_file_settings(app):
    body = app.settings_pages["settings_files"]
    folders = SettingsSection(body, app.t("settings_group_storage"), row=0)
    host = folders.field(app.t("output_folder"), app.t("setting_storage_help"), t=app.t)
    app.storage_output = ctk.CTkEntry(host, height=35)
    app.storage_output.insert(0, str(app.output_folder))
    app.storage_output.configure(state="readonly")
    app.storage_output.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    app.storage_output_tip = ToolTip(app.storage_output, app.t("storage_output_tip", path=app.output_folder))
    app.output_folder_button = ctk.CTkButton(host, text=app.t("change"), command=app.change_output_folder, height=34, fg_color=ALT)
    app.output_folder_button.grid(row=1, column=0, sticky="w")
    ToolTip(app.output_folder_button, app.t("setting_storage_help"))
    button = ctk.CTkButton(host, text=app.t("storage_short"), command=lambda: StorageDialog(app), fg_color=ALT, height=34)
    button.grid(row=2, column=0, sticky="w", pady=(8, 0))
    ToolTip(button, app.t("storage_summary_tip"))
    ctk.CTkLabel(folders, text=app.t("storage_compact", minimum=format_bytes(MINIMUM_INSTALL_FREE, app.t.language)),
                 text_color=GREEN, wraplength=620, justify="left").grid(row=folders.next_row, column=0, sticky="ew", padx=18, pady=(0, 16))
    saving = SettingsSection(body, app.t("settings_group_output"), row=1)
    host = saving.field(app.t("privacy_controls"), app.t("privacy_controls_help"), t=app.t)
    privacy = ctk.CTkButton(host, text=app.t("privacy_controls"), command=app.privacy_controls, height=34, fg_color=ALT)
    privacy.grid(row=0, column=0, sticky="w")
    ToolTip(privacy, app.t("privacy_controls_help"))
    app.keep_audio_var = ctk.BooleanVar(value=app.settings.get("keep_recording_audio", True))
    for label, help_key, variable in (("keep_audio", "tip_keep_audio", app.keep_audio_var),
                                       ("open_result", "tip_open", app.open_result_var),
                                       ("smart_subtitles", "tip_subtitles", app.smart_subtitles_var)):
        check(saving, app, label, help_key, variable, app.persist_settings)
    option(saving, app, "video_limit", "setting_video_help", ["512 MB", "1000 MB", "2000 MB", "4000 MB"],
           f'{app.settings.get("video_max_mb", 2000)} MB',
           lambda value: app.settings.set("video_max_mb", int(value.split()[0]), save=True))


def build_voice_options(app, parent):
    buttons = ctk.CTkFrame(parent, fg_color="transparent")
    buttons.grid(row=0, column=0, sticky="ew", pady=5)
    for label, action, help_key in (("speech_read", app.read_transcript_lines, "tip_speech_read"),
                                     ("speech_stop", app.stop_speaking, "tip_speech_stop"),
                                     ("speech_bank", app.open_voice_bank, "speech_bank_help")):
        button = ctk.CTkButton(buttons, text=app.t(label), command=action, fg_color=ALT, height=32, width=135)
        button.pack(side="left", padx=(0, 7))
        ToolTip(button, app.t(help_key))
    app.voice_prompt = ctk.CTkButton(buttons, text="", width=160, height=32, fg_color="#205B50")
    ToolTip(app.voice_prompt, app.t("speech_bank_help"))
    fields = (("speech_slow", "tip_speech_slow", app.slow_voice_var, app.persist_settings),
              ("speech_click", "speech_click_help", app.speech_click_var, app._click_speech_changed))
    for row, (label, help_key, variable, action) in enumerate(fields, 1):
        field = ctk.CTkFrame(parent, fg_color="transparent")
        field.grid(row=row, column=0, sticky="ew", pady=(11, 4))
        field.grid_columnconfigure(0, weight=1)
        checkbox = ctk.CTkSwitch(field, text=app.t(label), variable=variable, command=action,
                                 font=("Segoe UI", 13), progress_color="#2AAE87")
        checkbox.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(field, text=app.t(help_key), text_color=MUTED, wraplength=600,
                     justify="left", anchor="w", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="ew", pady=(3, 0))
        ToolTip(checkbox, app.t(help_key), title=app.t(label))
    app.speech_menu = tk.Menu(app, tearoff=False)
    for label, action in (("speech_read_selection", app.read_transcript_lines),
                            ("speech_original_audio", app.replay_original_audio),
                            ("speech_bank", app.open_voice_bank), ("speech_stop", app.stop_speaking)):
        app.speech_menu.add_command(label=app.t(label), command=action)
