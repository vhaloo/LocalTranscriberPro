"""Local Transcriber Pro 2.1 desktop interface."""

from __future__ import annotations

import csv
import json
import logging
import os
import platform
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
import numpy as np
import soundfile as sf
from platformdirs import user_cache_dir, user_data_dir

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAS_DND = True
except ImportError:
    HAS_DND = False
    DND_FILES = ""

    class TkinterDnD:
        class DnDWrapper:
            pass


from src.audio import SAMPLE_RATE, AudioRecorder
from src.diarizer import Diarizer
from src.estimator import TimeEstimator, format_duration
from src.hardware import HardwareProfile, detect_hardware
from src.i18n import Translator
from src.meter import TapeMeter
from src.models import (
    AUTO_MODEL_ID,
    model_choices,
    model_id_from_label,
    model_label,
)
from src.settings import SettingsStore
from src.tooltip import ToolTip
from src.transcriber import TranscriberEngine, TranscriptionOptions
from src.utils import (
    atomic_write_text,
    create_srt_content,
    create_vtt_content,
    format_timestamp,
    timestamped_name,
)
from src.youtube_utils import download_youtube_audio, is_supported_url

APP_VERSION = "2.1.0"
DEV_CREDIT = "Vhaloo"

BACKGROUND = "#08101F"
PANEL = "#111C32"
PANEL_ALT = "#16233D"
TEXT = "#F5F7FB"
MUTED = "#9AA8BE"
ACCENT = "#5EE4B7"
ACCENT_DARK = "#2BB98D"
BLUE = "#65A8FF"
RED = "#F06878"
AMBER = "#F3C969"

AUDIO_VIDEO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".opus",
    ".wma",
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".mpeg",
    ".mpg",
}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".mpeg", ".mpg"}

LANGUAGE_OPTIONS = {
    "auto": ("Detect automatically", "Détection automatique"),
    "fr": ("French", "Français"),
    "en": ("English", "Anglais"),
    "es": ("Spanish", "Espagnol"),
    "de": ("German", "Allemand"),
    "it": ("Italian", "Italien"),
    "pt": ("Portuguese", "Portugais"),
    "nl": ("Dutch", "Néerlandais"),
    "pl": ("Polish", "Polonais"),
    "ru": ("Russian", "Russe"),
    "uk": ("Ukrainian", "Ukrainien"),
    "ar": ("Arabic", "Arabe"),
    "zh": ("Chinese", "Chinois"),
    "ja": ("Japanese", "Japonais"),
    "ko": ("Korean", "Coréen"),
    "hi": ("Hindi", "Hindi"),
    "tr": ("Turkish", "Turc"),
    "sv": ("Swedish", "Suédois"),
}


class HelpDialog(ctk.CTkToplevel):
    def __init__(self, parent: TranscriberApp):
        super().__init__(parent)
        self.t = parent.t
        self.title(self.t("help"))
        self.geometry("720x560")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=BACKGROUND)

        ctk.CTkLabel(
            self,
            text=f"Local Transcriber Pro {APP_VERSION}",
            font=("Segoe UI", 25, "bold"),
            text_color=TEXT,
        ).pack(anchor="w", padx=28, pady=(26, 8))
        ctk.CTkLabel(
            self,
            text=self.t("about_help"),
            justify="left",
            wraplength=650,
            font=("Segoe UI", 14),
            text_color=MUTED,
        ).pack(anchor="w", padx=28, pady=(0, 18))

        guide = ctk.CTkScrollableFrame(self, fg_color=PANEL, corner_radius=18)
        guide.pack(fill="both", expand=True, padx=28, pady=(0, 18))
        items = [
            ("task_files", "task_files_help"),
            ("task_conference", "task_conference_help"),
            ("task_dictation", "task_dictation_help"),
            ("task_link", "task_link_help"),
            ("model", "model_help"),
            ("first_run", "first_run"),
        ]
        for title_key, body_key in items:
            ctk.CTkLabel(
                guide,
                text=self.t(title_key),
                font=("Segoe UI", 15, "bold"),
                text_color=TEXT,
                anchor="w",
            ).pack(fill="x", padx=18, pady=(14, 2))
            ctk.CTkLabel(
                guide,
                text=self.t(body_key),
                font=("Segoe UI", 13),
                text_color=MUTED,
                justify="left",
                wraplength=620,
                anchor="w",
            ).pack(fill="x", padx=18, pady=(0, 8))
        ctk.CTkButton(
            self,
            text=self.t("close"),
            command=self.destroy,
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
        ).pack(pady=(0, 22))


class HardwareDialog(ctk.CTkToplevel):
    def __init__(self, parent: TranscriberApp):
        super().__init__(parent)
        self.t = parent.t
        profile = parent.hardware
        self.title(self.t("hardware_title"))
        self.geometry("680x470")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=BACKGROUND)

        ctk.CTkLabel(
            self,
            text=self.t("hardware_title"),
            font=("Segoe UI", 25, "bold"),
            text_color=TEXT,
        ).pack(anchor="w", padx=28, pady=(26, 10))
        summary = self.t(
            "hardware_summary",
            os=f"{profile.os_name} {profile.os_version} ({profile.architecture})",
            cpu=profile.cpu_name,
            ram=profile.ram_gb,
            gpu=profile.gpu_name or "CPU",
        )
        ctk.CTkLabel(
            self,
            text=summary,
            font=("Segoe UI", 14),
            text_color=MUTED,
            justify="left",
            wraplength=620,
        ).pack(anchor="w", padx=28, pady=(0, 18))

        status_key = (
            "hardware_gpu_ok"
            if profile.gpu_available
            else ("hardware_gpu_missing" if profile.nvidia_detected else "hardware_cpu_ok")
        )
        status = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=16)
        status.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(
            status,
            text=self.t(status_key),
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT if profile.gpu_available else AMBER,
            wraplength=580,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(16, 8))
        ctk.CTkLabel(
            status,
            text=self.t("recommended_model", model=profile.recommended_model()),
            font=("Segoe UI", 13),
            text_color=TEXT,
        ).pack(anchor="w", padx=18, pady=3)
        details = (
            f"CTranslate2 CUDA: {'yes' if profile.ctranslate_cuda else 'no'}   •   "
            f"PyTorch CUDA: {'yes' if profile.torch_cuda else 'no'}\n"
            f"MLX: {'yes' if profile.mlx_available else 'no'}   •   "
            f"PyTorch MPS: {'yes' if profile.torch_mps else 'no'}"
        )
        ctk.CTkLabel(
            status,
            text=details,
            font=("Consolas", 12),
            text_color=MUTED,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(8, 16))
        ctk.CTkButton(
            self,
            text=self.t("close"),
            command=self.destroy,
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
        ).pack(pady=22)


class ModelManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent: TranscriberApp):
        super().__init__(parent)
        self.parent_app = parent
        self.t = parent.t
        self.title(self.t("model_manager"))
        self.geometry("680x500")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=BACKGROUND)
        ctk.CTkLabel(
            self,
            text=self.t("model_manager"),
            font=("Segoe UI", 23, "bold"),
            text_color=TEXT,
        ).pack(anchor="w", padx=26, pady=(24, 10))
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=PANEL, corner_radius=16)
        self.scroll.pack(fill="both", expand=True, padx=26, pady=8)
        self.refresh()
        ctk.CTkButton(
            self,
            text=self.t("close"),
            command=self.destroy,
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
        ).pack(pady=(8, 22))

    def refresh(self) -> None:
        for widget in self.scroll.winfo_children():
            widget.destroy()
        models = self.parent_app.engine.get_downloaded_models()
        if not models:
            ctk.CTkLabel(
                self.scroll,
                text=self.t("empty_models"),
                text_color=MUTED,
                font=("Segoe UI", 14),
            ).pack(pady=30)
            return
        for item in models:
            row = ctk.CTkFrame(self.scroll, fg_color=PANEL_ALT, corner_radius=12)
            row.pack(fill="x", padx=8, pady=6)
            ctk.CTkLabel(
                row,
                text=f"{item['name']}\n{item['size']}",
                font=("Segoe UI", 13),
                text_color=TEXT,
                justify="left",
            ).pack(side="left", padx=14, pady=12)
            ctk.CTkButton(
                row,
                text=self.t("delete"),
                width=90,
                fg_color=RED,
                hover_color="#D94F60",
                command=lambda path=item["path"]: self.delete(path),
            ).pack(side="right", padx=12)

    def delete(self, path: str) -> None:
        if not messagebox.askyesno(self.t("model_manager"), self.t("confirm_delete"), parent=self):
            return
        if self.parent_app.engine.delete_model_file(path):
            self.refresh()
        else:
            messagebox.showerror(self.t("error"), self.t("job_error", error=path), parent=self)


class TranscriberApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=BACKGROUND)

        self.settings = SettingsStore()
        self.t = Translator(self.settings.get("ui_language"))
        self.hardware: HardwareProfile = detect_hardware()
        self.engine = TranscriberEngine(self.hardware)
        self.estimator = TimeEstimator(self.settings.get("benchmarks", {}))
        self.recorder = AudioRecorder()
        self.diarizer = Diarizer()

        self.ui_mode = self.settings.get("ui_mode", "simple")
        self.simple_quality = self.settings.get("simple_quality", "best")
        self.saved_microphone = self.settings.get("microphone", "auto")
        self.preset = self.settings.get("preset", "files")
        self.selected_model_id = self.settings.get("model", AUTO_MODEL_ID)
        self.selected_device = self.settings.get("device", "auto")
        self.selected_language = self.settings.get("spoken_language", "auto")
        self.pending_files: list[str] = []
        self.transcript_data: list[dict[str, Any]] = []
        self.full_audio_buffer: list[np.ndarray] = []
        self.recording_offset = 0.0
        self.running = True
        self.busy = False
        self.job_started = 0.0
        self.estimated_job_seconds = 0.0
        self._last_progress = 0.0
        self.microphone_auto_selected = False
        self.selected_microphone_name = ""

        data_dir = Path(user_data_dir("LocalTranscriberPro", "Vhaloo"))
        data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_file = data_dir / "unsaved_session.json"

        self.translate_var = ctk.BooleanVar(value=bool(self.settings.get("translate")))
        self.speaker_var = ctk.BooleanVar(value=bool(self.settings.get("speaker_detection")))
        self.vad_var = ctk.BooleanVar(value=bool(self.settings.get("vad", True)))
        self.cleanup_var = ctk.BooleanVar(value=bool(self.settings.get("cleanup", True)))
        self.open_result_var = ctk.BooleanVar(value=bool(self.settings.get("open_result")))
        self.smart_subtitles_var = ctk.BooleanVar(value=bool(self.settings.get("smart_subtitles", True)))
        self.chunk_var = ctk.StringVar(value=str(self.settings.get("chunk_seconds", 30)))
        self.beam_var = ctk.StringVar(value=str(self.settings.get("beam_size", 5)))

        self._load_recovery()
        self.title(f"Local Transcriber Pro {APP_VERSION}")
        self.geometry(self.settings.get("window_geometry", "1180x860"))
        self.minsize(980, 720)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._init_drag_and_drop()
        self.build_ui()
        self.render_transcript()
        self.after(500, self._tick_clock)
        self.after(350, self._start_microphone_monitor)
        self.after(80, self._update_microphone_meter)

    def _init_drag_and_drop(self) -> None:
        self.TkdndVersion = None
        if not HAS_DND:
            return
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except Exception:
            logging.exception("Drag-and-drop initialization failed")

    def build_ui(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self._build_header()
        self._build_simple_dashboard()
        self._build_tasks()
        self._build_source_card()
        self._build_advanced_panel()
        self._build_output()
        self._apply_mode_visibility()
        self._refresh_task_styles()
        self._update_source_context()
        self._update_hardware_chip()
        self._setup_dnd_target()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 12))
        header.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_box,
            text="Local Transcriber Pro",
            font=("Segoe UI", 27, "bold"),
            text_color=TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_box,
            text=self.t("app_subtitle"),
            font=("Segoe UI", 13),
            text_color=MUTED,
        ).pack(anchor="w", pady=(2, 0))

        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.grid(row=0, column=1, sticky="e")
        self.hardware_btn = ctk.CTkButton(
            controls,
            text="",
            width=180,
            height=36,
            fg_color=PANEL,
            hover_color=PANEL_ALT,
            text_color=ACCENT,
            command=lambda: HardwareDialog(self),
        )
        self.hardware_btn.pack(side="left", padx=5)
        ToolTip(self.hardware_btn, self.t("hardware_details"))
        self.models_button = ctk.CTkButton(
            controls,
            text=self.t("model_manager"),
            width=128,
            height=36,
            fg_color=PANEL,
            hover_color=PANEL_ALT,
            command=lambda: ModelManagerDialog(self),
        )
        self.models_button.pack(side="left", padx=5)
        ToolTip(self.models_button, self.t("tip_model_manager"))
        self.help_button = ctk.CTkButton(
            controls,
            text=self.t("help"),
            width=68,
            height=36,
            fg_color=PANEL,
            hover_color=PANEL_ALT,
            command=lambda: HelpDialog(self),
        )
        self.help_button.pack(side="left", padx=5)
        ToolTip(self.help_button, self.t("tip_help"))
        self.language_button = ctk.CTkButton(
            controls,
            text=self.t("language_name"),
            width=52,
            height=36,
            fg_color=PANEL,
            hover_color=PANEL_ALT,
            command=self.toggle_language,
        )
        self.language_button.pack(side="left", padx=5)
        ToolTip(self.language_button, self.t("tip_language"))
        self.mode_button = ctk.CTkButton(
            controls,
            text=self.t("advanced" if self.ui_mode == "simple" else "simple"),
            width=88,
            height=36,
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
            text_color="#06140F",
            command=self.toggle_mode,
        )
        self.mode_button.pack(side="left", padx=(5, 0))
        ToolTip(self.mode_button, self.t("tip_mode"))

    def _build_simple_dashboard(self) -> None:
        self.simple_panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=28)
        self.simple_panel.grid(row=1, column=0, sticky="ew", padx=28, pady=(4, 8))
        self.simple_panel.grid_columnconfigure(0, weight=1)

        heading = ctk.CTkFrame(self.simple_panel, fg_color="transparent")
        heading.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 8))
        heading.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            heading,
            text=self.t("step_one"),
            font=("Segoe UI", 17, "bold"),
            text_color=TEXT,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            heading,
            text=self.t("simple_tagline"),
            font=("Segoe UI", 12),
            text_color=MUTED,
        ).grid(row=0, column=1, sticky="e")

        task_row = ctk.CTkFrame(self.simple_panel, fg_color="transparent")
        task_row.grid(row=1, column=0, sticky="ew", padx=16)
        self.simple_task_buttons: dict[str, ctk.CTkButton] = {}
        simple_tasks = [
            ("files", "simple_task_files", "task_files_help"),
            ("conference", "simple_task_conference", "task_conference_help"),
            ("dictation", "simple_task_dictation", "task_dictation_help"),
            ("link", "simple_task_link", "task_link_help"),
        ]
        for index, (task_id, title_key, help_key) in enumerate(simple_tasks):
            task_row.grid_columnconfigure(index, weight=1)
            button = ctk.CTkButton(
                task_row,
                text=self.t(title_key),
                height=76,
                corner_radius=25,
                border_width=1,
                border_color="#2A4760",
                font=("Segoe UI", 13, "bold"),
                command=lambda value=task_id: self.select_preset(value),
            )
            button.grid(row=0, column=index, sticky="ew", padx=4)
            ToolTip(button, self.t(help_key))
            self.simple_task_buttons[task_id] = button

        choices = ctk.CTkFrame(self.simple_panel, fg_color="transparent")
        choices.grid(row=2, column=0, sticky="ew", padx=20, pady=(11, 6))
        for column in range(3):
            choices.grid_columnconfigure(column, weight=1)

        quality_box = ctk.CTkFrame(choices, fg_color="transparent")
        quality_box.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(quality_box, text=self.t("simple_quality"), text_color=MUTED).pack(anchor="w")
        self.quality_display_map = {
            self.t("quality_best"): "best",
            self.t("quality_fast"): "fast",
            self.t("quality_light"): "light",
        }
        self.simple_quality_control = ctk.CTkSegmentedButton(
            quality_box,
            values=list(self.quality_display_map),
            height=38,
            corner_radius=19,
            selected_color=ACCENT_DARK,
            selected_hover_color=ACCENT,
            unselected_color=PANEL_ALT,
            unselected_hover_color="#233654",
            command=self._simple_quality_changed,
        )
        self.simple_quality_control.pack(fill="x", pady=(4, 0))
        selected_quality = next(
            (label for label, value in self.quality_display_map.items() if value == self.simple_quality),
            self.t("quality_best"),
        )
        self.simple_quality_control.set(selected_quality)
        ToolTip(self.simple_quality_control, self.t("tip_quality"))

        language_box = ctk.CTkFrame(choices, fg_color="transparent")
        language_box.grid(row=0, column=1, sticky="ew", padx=6)
        ctk.CTkLabel(language_box, text=self.t("simple_language"), text_color=MUTED).pack(anchor="w")
        self.simple_language_map = {
            self.t("language_auto"): "auto",
            self.t("language_fr"): "fr",
            self.t("language_en"): "en",
        }
        self.simple_language_control = ctk.CTkSegmentedButton(
            language_box,
            values=list(self.simple_language_map),
            height=38,
            corner_radius=19,
            selected_color=BLUE,
            selected_hover_color="#86BBFF",
            unselected_color=PANEL_ALT,
            unselected_hover_color="#233654",
            command=self._simple_language_changed,
        )
        self.simple_language_control.pack(fill="x", pady=(4, 0))
        selected_language = next(
            (label for label, value in self.simple_language_map.items() if value == self.selected_language),
            self.t("language_auto"),
        )
        self.simple_language_control.set(selected_language)
        ToolTip(self.simple_language_control, self.t("tip_simple_language"))

        voices_box = ctk.CTkFrame(choices, fg_color="transparent")
        voices_box.grid(row=0, column=2, sticky="ew", padx=(12, 0))
        ctk.CTkLabel(voices_box, text=self.t("simple_voices"), text_color=MUTED).pack(anchor="w")
        self.simple_speaker_switch = ctk.CTkSwitch(
            voices_box,
            text=self.t("voices_separate"),
            variable=self.speaker_var,
            height=38,
            corner_radius=19,
            progress_color=ACCENT_DARK,
            command=self.persist_settings,
        )
        self.simple_speaker_switch.pack(anchor="w", pady=(4, 0))
        ToolTip(self.simple_speaker_switch, self.t("tip_simple_speakers"))

        ctk.CTkLabel(
            self.simple_panel,
            text=self.t("simple_automatic_summary"),
            font=("Segoe UI", 11),
            text_color=ACCENT,
        ).grid(row=3, column=0, sticky="w", padx=22, pady=(3, 13))

    def _build_tasks(self) -> None:
        self.task_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.task_frame.grid(row=1, column=0, sticky="ew", padx=28, pady=(4, 10))
        ctk.CTkLabel(
            self.task_frame,
            text=self.t("task_title"),
            font=("Segoe UI", 17, "bold"),
            text_color=TEXT,
        ).pack(anchor="w", pady=(0, 8))
        row = ctk.CTkFrame(self.task_frame, fg_color="transparent")
        row.pack(fill="x")
        self.task_buttons: dict[str, ctk.CTkButton] = {}
        tasks = [
            ("files", "task_files", "task_files_help"),
            ("conference", "task_conference", "task_conference_help"),
            ("dictation", "task_dictation", "task_dictation_help"),
            ("link", "task_link", "task_link_help"),
        ]
        for index, (task_id, title_key, help_key) in enumerate(tasks):
            row.grid_columnconfigure(index, weight=1)
            button = ctk.CTkButton(
                row,
                text=self.t(title_key),
                height=48,
                corner_radius=14,
                font=("Segoe UI", 13, "bold"),
                command=lambda value=task_id: self.select_preset(value),
            )
            button.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 5, 0))
            ToolTip(button, self.t(help_key))
            self.task_buttons[task_id] = button

    def _build_source_card(self) -> None:
        self.source_card = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=28)
        self.source_card.grid(row=2, column=0, sticky="ew", padx=28, pady=6)
        self.source_card.grid_columnconfigure(0, weight=1)
        self.source_title = ctk.CTkLabel(
            self.source_card,
            text="",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT,
        )
        self.source_title.grid(row=0, column=0, sticky="w", padx=22, pady=(18, 2))
        self.source_help = ctk.CTkLabel(
            self.source_card,
            text="",
            font=("Segoe UI", 13),
            text_color=MUTED,
            wraplength=1040,
            justify="left",
        )
        self.source_help.grid(row=1, column=0, sticky="w", padx=22, pady=(0, 10))

        self.microphone_panel = ctk.CTkFrame(
            self.source_card,
            fg_color="#0B1724",
            corner_radius=20,
            border_width=1,
            border_color="#29445A",
        )
        self.microphone_panel.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.microphone_panel.grid_columnconfigure(1, weight=1)
        microphone_info = ctk.CTkFrame(self.microphone_panel, fg_color="transparent", width=300)
        microphone_info.grid(row=0, column=0, sticky="nsew", padx=(16, 12), pady=12)
        self.microphone_status_label = ctk.CTkLabel(
            microphone_info,
            text=self.t("microphone_ready"),
            font=("Segoe UI", 12, "bold"),
            text_color=ACCENT,
            fg_color="#12392F",
            corner_radius=13,
            padx=10,
            pady=4,
        )
        self.microphone_status_label.pack(anchor="w")
        self.microphone_selection_label = ctk.CTkLabel(
            microphone_info,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT,
            justify="left",
            wraplength=285,
        )
        self.microphone_selection_label.pack(anchor="w", pady=(7, 2))
        self.microphone_privacy_label = ctk.CTkLabel(
            microphone_info,
            text=self.t("microphone_level_only"),
            font=("Segoe UI", 10),
            text_color=MUTED,
            justify="left",
            wraplength=285,
        )
        self.microphone_privacy_label.pack(anchor="w")
        self.microphone_meter = TapeMeter(self.microphone_panel, height=104)
        self.microphone_meter.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=10)

        self.file_controls = ctk.CTkFrame(self.source_card, fg_color="transparent")
        self.file_controls.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 18))
        self.file_controls.grid_columnconfigure(0, weight=1)
        self.file_hint = ctk.CTkLabel(
            self.file_controls,
            text=self.t("drop_help"),
            text_color=MUTED,
            font=("Segoe UI", 12),
        )
        self.file_hint.grid(row=0, column=0, sticky="w")
        self.choose_button = ctk.CTkButton(
            self.file_controls,
            text=self.t("choose_files"),
            width=170,
            height=46,
            corner_radius=23,
            fg_color=BLUE,
            hover_color="#86BBFF",
            text_color="#07111F",
            font=("Segoe UI", 13, "bold"),
            command=self.choose_files,
        )
        self.choose_button.grid(row=0, column=1, padx=(12, 0))
        ToolTip(self.choose_button, self.t("tip_choose"))

        self.record_controls = ctk.CTkFrame(self.source_card, fg_color="transparent")
        self.record_controls.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 18))
        self.record_controls.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            self.record_controls,
            text=self.t("microphone"),
            text_color=MUTED,
            font=("Segoe UI", 12),
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.microphone_combo = ctk.CTkComboBox(
            self.record_controls,
            values=[],
            height=38,
            fg_color=PANEL_ALT,
            border_color="#2A3C5E",
            dropdown_fg_color=PANEL_ALT,
            command=self._microphone_changed,
        )
        self.microphone_combo.grid(row=0, column=1, sticky="ew", padx=(0, 14))
        self._populate_microphones()
        ToolTip(self.microphone_combo, self.t("tip_microphone"))
        self.record_button = ctk.CTkButton(
            self.record_controls,
            text=self.t("record"),
            width=112,
            height=46,
            corner_radius=23,
            fg_color=RED,
            hover_color="#FF8290",
            font=("Segoe UI", 13, "bold"),
            command=self.start_recording,
        )
        self.record_button.grid(row=0, column=2, padx=4)
        ToolTip(self.record_button, self.t("tip_record"))
        self.pause_button = ctk.CTkButton(
            self.record_controls,
            text=self.t("pause"),
            width=96,
            height=46,
            corner_radius=23,
            state="disabled",
            fg_color=AMBER,
            hover_color="#FFDE8A",
            text_color="#181207",
            command=self.toggle_pause,
        )
        self.pause_button.grid(row=0, column=3, padx=4)
        ToolTip(self.pause_button, self.t("tip_pause"))
        self.stop_button = ctk.CTkButton(
            self.record_controls,
            text=self.t("stop"),
            width=96,
            height=46,
            corner_radius=23,
            state="disabled",
            fg_color="#60708A",
            hover_color="#7989A4",
            command=self.stop_recording,
        )
        self.stop_button.grid(row=0, column=4, padx=(4, 0))
        ToolTip(self.stop_button, self.t("tip_stop"))

        self.link_controls = ctk.CTkFrame(self.source_card, fg_color="transparent")
        self.link_controls.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 18))
        self.link_controls.grid_columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(
            self.link_controls,
            placeholder_text=self.t("url_placeholder"),
            height=46,
            corner_radius=23,
            fg_color=PANEL_ALT,
            border_color="#2A3C5E",
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.link_button = ctk.CTkButton(
            self.link_controls,
            text=self.t("download_start"),
            width=190,
            height=46,
            corner_radius=23,
            fg_color=BLUE,
            hover_color="#86BBFF",
            text_color="#07111F",
            font=("Segoe UI", 13, "bold"),
            command=self.start_link,
        )
        self.link_button.grid(row=0, column=1)
        ToolTip(self.link_button, self.t("tip_link"))

    def _build_advanced_panel(self) -> None:
        self.advanced_panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=20)
        self.advanced_panel.grid(row=3, column=0, sticky="ew", padx=28, pady=6)
        for column in range(4):
            self.advanced_panel.grid_columnconfigure(column, weight=1)
        ctk.CTkLabel(
            self.advanced_panel,
            text=self.t("settings"),
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT,
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=20, pady=(16, 10))

        self.model_combo = self._labeled_combo(
            1,
            0,
            self.t("model"),
            model_choices(self.t.language),
            model_label(self.selected_model_id, self.t.language),
            self._model_changed,
        )
        ToolTip(self.model_combo, self.t("model_help"))

        self.device_display_map = self._device_display_map()
        device_values = list(self.device_display_map)
        selected_device_label = next(
            (label for label, value in self.device_display_map.items() if value == self.selected_device),
            device_values[0],
        )
        self.device_combo = self._labeled_combo(
            1, 1, self.t("device"), device_values, selected_device_label, self._device_changed
        )
        ToolTip(self.device_combo, self.t("tip_device"))

        self.language_display_map = self._language_display_map()
        selected_language_label = next(
            (label for label, value in self.language_display_map.items() if value == self.selected_language),
            next(iter(self.language_display_map)),
        )
        self.language_combo = self._labeled_combo(
            1,
            2,
            self.t("spoken_language"),
            list(self.language_display_map),
            selected_language_label,
            self._spoken_language_changed,
        )
        ToolTip(self.language_combo, self.t("tip_language_setting"))

        output_box = ctk.CTkFrame(self.advanced_panel, fg_color="transparent")
        output_box.grid(row=1, column=3, sticky="ew", padx=10, pady=4)
        ctk.CTkLabel(
            output_box,
            text=self.t("output_folder"),
            font=("Segoe UI", 11),
            text_color=MUTED,
        ).pack(anchor="w")
        self.output_folder_button = ctk.CTkButton(
            output_box,
            text=self.t("change"),
            height=34,
            fg_color=PANEL_ALT,
            hover_color="#233654",
            command=self.change_output_folder,
        )
        self.output_folder_button.pack(fill="x", pady=(4, 0))
        ToolTip(self.output_folder_button, self.t("tip_output"))

        checks = ctk.CTkFrame(self.advanced_panel, fg_color="transparent")
        checks.grid(row=2, column=0, columnspan=4, sticky="ew", padx=14, pady=(8, 6))
        for column in range(4):
            checks.grid_columnconfigure(column, weight=1)
        check_specs = [
            ("translate", self.translate_var, "tip_translate"),
            ("speaker_detection", self.speaker_var, "tip_speakers"),
            ("vad", self.vad_var, "tip_vad"),
            ("cleanup", self.cleanup_var, "tip_cleanup"),
            ("open_result", self.open_result_var, "tip_open"),
            ("smart_subtitles", self.smart_subtitles_var, "tip_subtitles"),
        ]
        for index, (key, variable, tip_key) in enumerate(check_specs):
            widget = ctk.CTkCheckBox(
                checks,
                text=self.t(key),
                variable=variable,
                checkbox_width=20,
                checkbox_height=20,
                fg_color=ACCENT_DARK,
                hover_color=ACCENT,
                font=("Segoe UI", 12),
                command=self.persist_settings,
            )
            widget.grid(row=index // 4, column=index % 4, sticky="w", padx=6, pady=7)
            ToolTip(widget, self.t(tip_key))

        tuning = ctk.CTkFrame(self.advanced_panel, fg_color="transparent")
        tuning.grid(row=3, column=0, columnspan=4, sticky="ew", padx=20, pady=(2, 14))
        ctk.CTkLabel(tuning, text=self.t("chunk"), text_color=MUTED).pack(side="left")
        self.chunk_combo = ctk.CTkComboBox(
            tuning,
            values=["5", "10", "15", "20", "30"],
            variable=self.chunk_var,
            width=76,
            height=32,
            command=lambda _: self.persist_settings(),
            fg_color=PANEL_ALT,
            border_color="#2A3C5E",
        )
        self.chunk_combo.pack(side="left", padx=(7, 20))
        ToolTip(self.chunk_combo, self.t("tip_chunk"))
        ctk.CTkLabel(tuning, text=self.t("beam"), text_color=MUTED).pack(side="left")
        self.beam_combo = ctk.CTkComboBox(
            tuning,
            values=["1", "3", "5", "8"],
            variable=self.beam_var,
            width=76,
            height=32,
            command=lambda _: self.persist_settings(),
            fg_color=PANEL_ALT,
            border_color="#2A3C5E",
        )
        self.beam_combo.pack(side="left", padx=7)
        ToolTip(self.beam_combo, self.t("tip_beam"))
        ctk.CTkLabel(
            tuning,
            text=self.t("model_help"),
            text_color=MUTED,
            font=("Segoe UI", 11),
            wraplength=610,
            justify="left",
        ).pack(side="left", padx=(16, 0))

    def _labeled_combo(
        self,
        row: int,
        column: int,
        title: str,
        values: list[str],
        selected: str,
        command: Callable[[str], None],
    ) -> ctk.CTkComboBox:
        box = ctk.CTkFrame(self.advanced_panel, fg_color="transparent")
        box.grid(row=row, column=column, sticky="ew", padx=10, pady=4)
        ctk.CTkLabel(
            box,
            text=title,
            font=("Segoe UI", 11),
            text_color=MUTED,
        ).pack(anchor="w")
        combo = ctk.CTkComboBox(
            box,
            values=values,
            height=34,
            command=command,
            fg_color=PANEL_ALT,
            border_color="#2A3C5E",
            dropdown_fg_color=PANEL_ALT,
        )
        combo.set(selected)
        combo.pack(fill="x", pady=(4, 0))
        return combo

    def _build_output(self) -> None:
        output = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=20)
        output.grid(row=4, column=0, sticky="nsew", padx=28, pady=(6, 22))
        output.grid_columnconfigure(0, weight=1)
        output.grid_rowconfigure(3, weight=1)

        progress_row = ctk.CTkFrame(output, fg_color="transparent")
        progress_row.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 6))
        progress_row.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(
            progress_row,
            text=self.t("progress_ready"),
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT,
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        self.eta_label = ctk.CTkLabel(
            progress_row,
            text="",
            font=("Segoe UI", 12),
            text_color=MUTED,
        )
        self.eta_label.grid(row=0, column=1, sticky="e")
        self.progress_bar = ctk.CTkProgressBar(
            output,
            height=8,
            progress_color=ACCENT,
            fg_color="#26344D",
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.progress_bar.set(0)

        toolbar = ctk.CTkFrame(output, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", padx=20)
        toolbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            toolbar,
            text=self.t("transcript"),
            font=("Segoe UI", 15, "bold"),
            text_color=TEXT,
        ).grid(row=0, column=0, sticky="w")
        self.copy_button = ctk.CTkButton(
            toolbar,
            text=self.t("copy"),
            width=78,
            height=31,
            fg_color=PANEL_ALT,
            hover_color="#233654",
            command=self.copy_transcript,
        )
        self.copy_button.grid(row=0, column=1, padx=4)
        ToolTip(self.copy_button, self.t("tip_copy"))
        self.clear_button = ctk.CTkButton(
            toolbar,
            text=self.t("clear"),
            width=78,
            height=31,
            fg_color=PANEL_ALT,
            hover_color="#233654",
            command=self.clear_transcript,
        )
        self.clear_button.grid(row=0, column=2, padx=4)
        ToolTip(self.clear_button, self.t("tip_clear"))
        export_values = [
            self.t("export_txt"),
            self.t("export_srt"),
            self.t("export_vtt"),
            self.t("export_json"),
            self.t("export_csv"),
        ]
        self.export_menu = ctk.CTkOptionMenu(
            toolbar,
            values=export_values,
            command=self.export_selected,
            width=155,
            height=31,
            fg_color=ACCENT_DARK,
            button_color=ACCENT_DARK,
            button_hover_color=ACCENT,
        )
        self.export_menu.set(self.t("export"))
        self.export_menu.grid(row=0, column=3, padx=(4, 0))
        ToolTip(self.export_menu, self.t("tip_export"))

        self.textbox = ctk.CTkTextbox(
            output,
            fg_color="#0B1425",
            border_width=1,
            border_color="#243653",
            corner_radius=13,
            font=("Segoe UI", 14),
            text_color=TEXT,
            wrap="word",
        )
        self.textbox.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 18))

    def _device_display_map(self) -> dict[str, str]:
        values = {self.t("device_auto"): "auto", self.t("device_cpu"): "cpu"}
        if self.hardware.nvidia_detected:
            values[self.t("device_cuda")] = "cuda"
        if self.hardware.apple_silicon:
            values[self.t("device_metal")] = "metal"
        return values

    def _language_display_map(self) -> dict[str, str]:
        language_index = 1 if self.t.language == "fr" else 0
        return {
            f"{labels[language_index]} ({code})" if code != "auto" else labels[language_index]: code
            for code, labels in LANGUAGE_OPTIONS.items()
        }

    def _update_hardware_chip(self) -> None:
        self.hardware_btn.configure(text=self.t("hardware_ready", device=self.hardware.display_device))

    def _apply_mode_visibility(self) -> None:
        if self.ui_mode == "advanced":
            self.simple_panel.grid_remove()
            self.task_frame.grid()
            self.advanced_panel.grid()
            self.source_title.grid_remove()
            self.source_help.grid_remove()
            self.microphone_meter.configure(height=74)
            self.microphone_privacy_label.pack_forget()
        else:
            self.task_frame.grid_remove()
            self.simple_panel.grid()
            self.advanced_panel.grid_remove()
            self.source_title.grid()
            self.source_help.grid()
            self.microphone_meter.configure(height=104)
            self.microphone_privacy_label.pack(anchor="w")
        self.mode_button.configure(text=self.t("advanced" if self.ui_mode == "simple" else "simple"))

    def _refresh_task_styles(self) -> None:
        for task_id, button in self.task_buttons.items():
            selected = task_id == self.preset
            button.configure(
                fg_color=ACCENT_DARK if selected else PANEL,
                hover_color=ACCENT if selected else PANEL_ALT,
                text_color="#07140F" if selected else TEXT,
            )
        for task_id, button in getattr(self, "simple_task_buttons", {}).items():
            selected = task_id == self.preset
            button.configure(
                fg_color=ACCENT_DARK if selected else PANEL_ALT,
                hover_color=ACCENT if selected else "#233654",
                text_color="#07140F" if selected else TEXT,
                border_color=ACCENT if selected else "#2A4760",
                border_width=2 if selected else 1,
            )

    def _update_source_context(self) -> None:
        mapping = {
            "files": ("task_files", "task_files_help"),
            "conference": ("task_conference", "task_conference_help"),
            "dictation": ("task_dictation", "task_dictation_help"),
            "link": ("task_link", "task_link_help"),
        }
        title_key, help_key = mapping.get(self.preset, mapping["files"])
        if self.ui_mode == "simple":
            action_key = {
                "files": "action_files",
                "conference": "action_conference",
                "dictation": "action_dictation",
                "link": "action_link",
            }.get(self.preset, "action_files")
            self.source_title.configure(text=self.t("step_two"))
            self.source_help.configure(text=self.t(action_key))
        else:
            self.source_title.configure(text=self.t(title_key))
            self.source_help.configure(text=self.t(help_key))
        self.file_controls.grid_remove()
        self.record_controls.grid_remove()
        self.link_controls.grid_remove()
        if self.preset == "files":
            self.file_controls.grid()
        elif self.preset in {"conference", "dictation"}:
            self.record_controls.grid()
        else:
            self.link_controls.grid()

    def _setup_dnd_target(self) -> None:
        if not HAS_DND or not self.TkdndVersion:
            return
        try:
            self.source_card.drop_target_register(DND_FILES)
            self.source_card.dnd_bind("<<Drop>>", self.drop_files)
        except Exception:
            logging.exception("Could not bind drag-and-drop")

    def _populate_microphones(self) -> None:
        devices, selected = self.recorder.get_devices()
        values = devices or [self.t("default_microphone")]
        manual = None
        if self.saved_microphone != "auto":
            manual = next((value for value in values if value.split(":", 1)[-1].strip() == self.saved_microphone), None)
        chosen = manual or selected or values[0]
        self.microphone_auto_selected = manual is None
        self.selected_microphone_name = chosen.split(":", 1)[-1].strip()
        self.microphone_combo.configure(values=values)
        self.microphone_combo.set(chosen)
        self._refresh_microphone_labels()

    def _microphone_changed(self, selection: str) -> None:
        self.microphone_auto_selected = False
        self.selected_microphone_name = selection.split(":", 1)[-1].strip()
        self.saved_microphone = self.selected_microphone_name
        self.settings.set("microphone", self.saved_microphone, save=True)
        self._refresh_microphone_labels()
        self.after(80, self._start_microphone_monitor)

    def _refresh_microphone_labels(self) -> None:
        label = self.t(
            "microphone_selected_auto" if self.microphone_auto_selected else "microphone_selected_manual",
            name=self.selected_microphone_name or self.t("default_microphone"),
        )
        if hasattr(self, "microphone_selection_label"):
            self.microphone_selection_label.configure(text=label)

    def _selected_microphone_index(self) -> int | None:
        try:
            selection = self.microphone_combo.get()
            return int(selection.split(":", 1)[0]) if ":" in selection else None
        except (AttributeError, ValueError, tk.TclError):
            return None

    def _start_microphone_monitor(self) -> None:
        if not self.running or self.recorder.recording:
            return
        available = self.recorder.start_monitor(self._selected_microphone_index())
        try:
            if available:
                self.microphone_status_label.configure(
                    text=self.t("microphone_ready"),
                    text_color=ACCENT,
                    fg_color="#12392F",
                )
                self.microphone_privacy_label.configure(text=self.t("microphone_level_only"), text_color=MUTED)
            else:
                self.microphone_status_label.configure(
                    text=self.t("warning").upper(),
                    text_color=AMBER,
                    fg_color="#45381A",
                )
                self.microphone_privacy_label.configure(text=self.t("microphone_unavailable"), text_color=AMBER)
        except tk.TclError:
            pass

    def _update_microphone_meter(self) -> None:
        if not self.running:
            return
        amplitude, waveform = self.recorder.get_visual_state()
        try:
            self.microphone_meter.update_levels(
                amplitude,
                waveform,
                active=self.recorder.monitoring or self.recorder.recording,
                recording=self.recorder.recording and not self.recorder.paused,
            )
            if self.recorder.recording:
                self.microphone_status_label.configure(
                    text=self.t("microphone_recording"),
                    text_color="#FFDDE2",
                    fg_color="#5A2430",
                )
            elif self.recorder.monitoring:
                self.microphone_status_label.configure(
                    text=self.t("microphone_ready"),
                    text_color=ACCENT,
                    fg_color="#12392F",
                )
        except (AttributeError, tk.TclError):
            pass
        self.after(60, self._update_microphone_meter)

    def _simple_quality_changed(self, label: str) -> None:
        self.simple_quality = self.quality_display_map.get(label, "best")
        self.selected_model_id = {
            "best": AUTO_MODEL_ID,
            "fast": "large-v3-turbo",
            "light": "tiny",
        }[self.simple_quality]
        if self.simple_quality == "fast":
            self.translate_var.set(False)
        if hasattr(self, "model_combo"):
            self.model_combo.set(model_label(self.selected_model_id, self.t.language))
        self.persist_settings()

    def _simple_language_changed(self, label: str) -> None:
        self.selected_language = self.simple_language_map.get(label, "auto")
        if hasattr(self, "language_combo"):
            selected = next(
                (name for name, value in self.language_display_map.items() if value == self.selected_language),
                next(iter(self.language_display_map)),
            )
            self.language_combo.set(selected)
        self.persist_settings()

    def toggle_language(self) -> None:
        self.t.set_language("fr" if self.t.language == "en" else "en")
        self.settings.set("ui_language", self.t.language, save=True)
        self.build_ui()
        self.render_transcript()

    def toggle_mode(self) -> None:
        self.ui_mode = "advanced" if self.ui_mode == "simple" else "simple"
        if self.ui_mode == "simple":
            self.selected_model_id = {
                "best": AUTO_MODEL_ID,
                "fast": "large-v3-turbo",
                "light": "tiny",
            }.get(self.simple_quality, AUTO_MODEL_ID)
            if self.selected_language not in {"auto", "fr", "en"}:
                self.selected_language = "auto"
                self.simple_language_control.set(self.t("language_auto"))
        self.settings.set("ui_mode", self.ui_mode, save=True)
        self._apply_mode_visibility()
        self._update_source_context()
        self.persist_settings()

    def select_preset(self, preset: str) -> None:
        if self.busy or self.recorder.recording:
            return
        self.preset = preset
        if preset == "conference":
            self.speaker_var.set(True)
            self.chunk_var.set("30")
        elif preset == "dictation":
            self.speaker_var.set(False)
            self.chunk_var.set("10")
        self.settings.set("preset", preset)
        self.persist_settings()
        self._refresh_task_styles()
        self._update_source_context()

    def _model_changed(self, label: str) -> None:
        self.selected_model_id = model_id_from_label(label, self.t.language)
        self.simple_quality = {
            AUTO_MODEL_ID: "best",
            "large-v3-turbo": "fast",
            "tiny": "light",
        }.get(self.selected_model_id, "best")
        self.persist_settings()

    def _device_changed(self, label: str) -> None:
        self.selected_device = self.device_display_map.get(label, "auto")
        self.persist_settings()

    def _spoken_language_changed(self, label: str) -> None:
        self.selected_language = self.language_display_map.get(label, "auto")
        simple_label = next(
            (name for name, value in self.simple_language_map.items() if value == self.selected_language),
            self.t("language_auto"),
        )
        self.simple_language_control.set(simple_label)
        self.persist_settings()

    def persist_settings(self) -> None:
        self.settings.update(
            {
                "ui_mode": self.ui_mode,
                "simple_quality": self.simple_quality,
                "microphone": self.saved_microphone,
                "preset": self.preset,
                "model": self.selected_model_id,
                "device": self.selected_device,
                "spoken_language": self.selected_language,
                "translate": bool(self.translate_var.get()),
                "speaker_detection": bool(self.speaker_var.get()),
                "vad": bool(self.vad_var.get()),
                "cleanup": bool(self.cleanup_var.get()),
                "open_result": bool(self.open_result_var.get()),
                "smart_subtitles": bool(self.smart_subtitles_var.get()),
                "chunk_seconds": int(self.chunk_var.get()),
                "beam_size": int(self.beam_var.get()),
                "benchmarks": self.estimator.benchmarks,
            },
            save=True,
        )

    def job_config(self) -> dict[str, Any]:
        return {
            "model": self.selected_model_id,
            "device": self.selected_device,
            "language": None if self.selected_language == "auto" else self.selected_language,
            "task": "translate" if self.translate_var.get() else "transcribe",
            "speaker": bool(self.speaker_var.get()),
            "vad": bool(self.vad_var.get()),
            "cleanup": bool(self.cleanup_var.get()),
            "smart_subtitles": bool(self.smart_subtitles_var.get()),
            "open_result": bool(self.open_result_var.get()),
            "beam": int(self.beam_var.get()),
            "chunk": int(self.chunk_var.get()),
        }

    def transcribe_options(self, config: dict[str, Any]) -> TranscriptionOptions:
        return TranscriptionOptions(
            task=config["task"],
            language=config["language"],
            beam_size=config["beam"],
            vad_filter=config["vad"],
            word_timestamps=True,
        )

    def choose_files(self) -> None:
        paths = filedialog.askopenfilenames(
            parent=self,
            title=self.t("select_files"),
            filetypes=[
                (self.t("supported_files"), " ".join(f"*{ext}" for ext in sorted(AUDIO_VIDEO_EXTENSIONS))),
                (self.t("all_files"), "*.*"),
            ],
        )
        if paths:
            self.start_batch(list(paths))

    def drop_files(self, event) -> None:
        if self.busy or self.recorder.recording:
            return
        try:
            paths = list(self.tk.splitlist(event.data))
        except (tk.TclError, AttributeError):
            paths = [event.data]
        accepted: list[str] = []
        for value in paths:
            path = Path(value)
            if path.is_dir():
                accepted.extend(
                    str(item)
                    for item in sorted(path.rglob("*"))
                    if item.suffix.lower() in AUDIO_VIDEO_EXTENSIONS
                )
            elif path.suffix.lower() in AUDIO_VIDEO_EXTENSIONS:
                accepted.append(str(path))
        if accepted:
            self.preset = "files"
            self._refresh_task_styles()
            self._update_source_context()
            self.start_batch(accepted)
        else:
            messagebox.showwarning(self.t("warning"), self.t("no_files"), parent=self)

    def start_batch(self, paths: list[str]) -> None:
        valid = [str(Path(path)) for path in paths if Path(path).suffix.lower() in AUDIO_VIDEO_EXTENSIONS]
        if not valid:
            messagebox.showwarning(self.t("warning"), self.t("no_files"), parent=self)
            return
        config = self.job_config()
        durations = [self.engine.audio_duration(path) for path in valid]
        total_audio = sum(durations)
        resolved_model = self.hardware.resolve_model(config["model"])
        resolved_device = self.hardware.best_device if config["device"] == "auto" else config["device"]
        estimate = self.estimator.estimate(total_audio, resolved_model, resolved_device)
        self._start_job(estimate.seconds)
        threading.Thread(
            target=self._batch_worker,
            args=(valid, durations, config),
            daemon=True,
            name="batch-transcription",
        ).start()

    def _batch_worker(self, paths: list[str], durations: list[float], config: dict[str, Any]) -> None:
        try:
            resolved = self.hardware.resolve_model(config["model"])
            self._safe_ui(self._set_status, self.t("progress_loading", model=resolved))
            status = self.engine.load_model(config["model"], config["device"])
            session_offset = self.transcript_data[-1].get("end", 0.0) + 1.0 if self.transcript_data else 0.0
            total = len(paths)
            last_saved: Path | None = None
            for index, (filepath, duration) in enumerate(
                zip(paths, durations, strict=True), start=1
            ):
                name = Path(filepath).name
                self._safe_ui(
                    self._set_status,
                    self.t("progress_file", name=name, index=index, total=total),
                )
                started = time.monotonic()

                def progress(value: float, file_index=index) -> None:
                    self._safe_ui(self._set_progress, ((file_index - 1) + value) / total)

                result = self.engine.transcribe_file(
                    filepath,
                    self.transcribe_options(config),
                    progress_callback=progress,
                )
                segments = self._prepare_segments(result.get("segments", []), config["cleanup"])
                if config["speaker"] and segments:
                    self._safe_ui(self._set_status, self.t("progress_diarizing"))
                    segments = self.diarizer.process(filepath, segments, callback=logging.info)
                file_segments = [dict(item, source=name) for item in segments]
                display_segments = [
                    dict(item, start=item["start"] + session_offset, end=item["end"] + session_offset)
                    for item in file_segments
                ]
                self._safe_ui(self._append_segments, display_segments)
                last_saved = self.save_result_bundle(file_segments, Path(filepath).stem)
                if config["smart_subtitles"] and Path(filepath).suffix.lower() in VIDEO_EXTENSIONS:
                    self.save_smart_subtitle(Path(filepath), file_segments)
                observed_audio = duration or result.get("duration", 0.0)
                self.estimator.observe(
                    observed_audio,
                    result.get("processing_seconds", time.monotonic() - started),
                    status.model_id,
                    status.device,
                )
                session_offset += max((item.get("end", 0.0) for item in file_segments), default=0.0) + 1.0
            self._safe_ui(self._finish_job, last_saved, status.backend)
        except Exception as error:
            logging.exception("Batch transcription failed")
            self._safe_ui(self._fail_job, error)

    def start_link(self) -> None:
        url = self.url_entry.get().strip()
        if not is_supported_url(url):
            messagebox.showwarning(self.t("warning"), self.t("invalid_url"), parent=self)
            return
        config = self.job_config()
        self._start_job(0)
        threading.Thread(
            target=self._link_worker,
            args=(url, config),
            daemon=True,
            name="online-video-transcription",
        ).start()

    def _link_worker(self, url: str, config: dict[str, Any]) -> None:
        downloaded: Path | None = None
        try:
            self._safe_ui(self._set_status, self.t("progress_downloading"))
            temp_dir = Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "online-audio"
            downloaded = Path(
                download_youtube_audio(
                    url,
                    temp_dir,
                    lambda percent: self._safe_ui(self._set_progress, percent / 400.0),
                )
            )
            self._safe_ui(self._set_progress, 0.25)
            resolved = self.hardware.resolve_model(config["model"])
            self._safe_ui(self._set_status, self.t("progress_loading", model=resolved))
            status = self.engine.load_model(config["model"], config["device"])
            result = self.engine.transcribe_file(
                str(downloaded),
                self.transcribe_options(config),
                progress_callback=lambda value: self._safe_ui(self._set_progress, 0.25 + value * 0.75),
            )
            segments = self._prepare_segments(result.get("segments", []), config["cleanup"])
            if config["speaker"] and segments:
                self._safe_ui(self._set_status, self.t("progress_diarizing"))
                segments = self.diarizer.process(str(downloaded), segments, callback=logging.info)
            self._safe_ui(self._append_segments, segments)
            saved = self.save_result_bundle(segments, downloaded.stem)
            self.estimator.observe(
                result.get("duration", 0),
                result.get("processing_seconds", 0),
                status.model_id,
                status.device,
            )
            self._safe_ui(self._finish_job, saved, status.backend)
        except Exception as error:
            logging.exception("Online video transcription failed")
            self._safe_ui(self._fail_job, error)
        finally:
            if downloaded:
                try:
                    downloaded.unlink(missing_ok=True)
                except OSError:
                    pass

    def start_recording(self) -> None:
        if self.busy or self.recorder.recording:
            return
        config = self.job_config()
        microphone = self.microphone_combo.get()
        try:
            device_index = int(microphone.split(":", 1)[0]) if ":" in microphone else None
        except ValueError:
            device_index = None
        self.transcript_data = []
        self.full_audio_buffer = []
        self.recording_offset = 0.0
        self.render_transcript()
        self._start_job(0)
        threading.Thread(
            target=self._recording_worker,
            args=(device_index, config),
            daemon=True,
            name="live-transcription",
        ).start()

    def _recording_worker(self, device_index: int | None, config: dict[str, Any]) -> None:
        try:
            resolved = self.hardware.resolve_model(config["model"])
            self._safe_ui(self._set_status, self.t("progress_loading", model=resolved))
            status = self.engine.load_model(config["model"], config["device"])
            self.recorder.start(device_index, config["chunk"])
            self._safe_ui(self._recording_started)
            options = self.transcribe_options(config)
            while self.running:
                audio = self.recorder.audio_queue.get()
                if audio is None:
                    break
                flattened = np.asarray(audio, dtype=np.float32).reshape(-1)
                self.full_audio_buffer.append(flattened)
                result = self.engine.transcribe_audio(flattened, options)
                segments = self._prepare_segments(result.get("segments", []), config["cleanup"])
                shifted = [
                    dict(
                        item,
                        start=item["start"] + self.recording_offset,
                        end=item["end"] + self.recording_offset,
                    )
                    for item in segments
                ]
                self.recording_offset += flattened.size / SAMPLE_RATE
                self._safe_ui(self._append_segments, shifted)
                self._save_backup()
            if config["speaker"] and self.full_audio_buffer:
                self._safe_ui(self._set_status, self.t("progress_diarizing"))
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
                    temp_path = Path(handle.name)
                try:
                    sf.write(temp_path, np.concatenate(self.full_audio_buffer), SAMPLE_RATE)
                    diarized = self.diarizer.process(
                        str(temp_path), [dict(item) for item in self.transcript_data], callback=logging.info
                    )
                    self.transcript_data = diarized
                    self._safe_ui(self.render_transcript)
                finally:
                    temp_path.unlink(missing_ok=True)
            saved = self.save_result_bundle(
                self.transcript_data,
                "Conference" if self.preset == "conference" else "Dictation",
            )
            self._safe_ui(self._finish_recording, saved, status.backend)
        except Exception as error:
            logging.exception("Live transcription failed")
            self._safe_ui(self._fail_recording, error)

    def _recording_started(self) -> None:
        self.busy = False
        self._set_status(self.t("progress_recording"))
        self.record_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.stop_button.configure(state="normal")
        self._set_source_buttons_state("disabled")

    def toggle_pause(self) -> None:
        if not self.recorder.recording:
            return
        if self.recorder.paused:
            self.recorder.resume()
            self.pause_button.configure(text=self.t("pause"))
            self._set_status(self.t("progress_recording"))
        else:
            self.recorder.pause()
            self.pause_button.configure(text=self.t("resume"))
            self._set_status(self.t("cancelled"))

    def stop_recording(self) -> None:
        if not self.recorder.recording:
            return
        self.recorder.stop()
        self.recorder.audio_queue.put(None)
        self.pause_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self._set_status(self.t("processing"))

    def _finish_recording(self, saved: Path | None, backend: str) -> None:
        self.record_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text=self.t("pause"))
        self.stop_button.configure(state="disabled")
        self._finish_job(saved, backend)
        self.after(250, self._start_microphone_monitor)

    def _fail_recording(self, error: Exception) -> None:
        try:
            self.recorder.stop()
        except Exception:
            pass
        self.record_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self._fail_job(error)
        self.after(250, self._start_microphone_monitor)

    def _prepare_segments(self, segments: list[dict[str, Any]], cleanup: bool) -> list[dict[str, Any]]:
        prepared = []
        for item in segments:
            text = str(item.get("text", "")).strip()
            if cleanup:
                text = self.engine.cleanup_text(text)
            if not text:
                continue
            prepared.append(
                {
                    "start": float(item.get("start", 0.0)),
                    "end": float(item.get("end", 0.0)),
                    "text": text,
                    "words": item.get("words", []),
                    **({"speaker": item["speaker"]} if item.get("speaker") else {}),
                }
            )
        return prepared

    def _append_segments(self, segments: list[dict[str, Any]]) -> None:
        self.transcript_data.extend(segments)
        for item in segments:
            self.textbox.insert("end", self.format_segment(item))
        self.textbox.see("end")

    @staticmethod
    def format_segment(segment: dict[str, Any]) -> str:
        stamp = format_timestamp(segment.get("start", 0), ".")[:8]
        speaker = f"[{segment['speaker']}] " if segment.get("speaker") else ""
        return f"[{stamp}] {speaker}{segment.get('text', '').strip()}\n"

    def render_transcript(self) -> None:
        if not hasattr(self, "textbox"):
            return
        self.textbox.delete("1.0", "end")
        for item in self.transcript_data:
            self.textbox.insert("end", self.format_segment(item))
        self.textbox.see("end")

    def copy_transcript(self) -> None:
        text = self.textbox.get("1.0", "end-1c").strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status(self.t("copied"))

    def clear_transcript(self) -> None:
        if self.busy or self.recorder.recording:
            return
        self.transcript_data = []
        self.textbox.delete("1.0", "end")
        self.backup_file.unlink(missing_ok=True)

    def export_selected(self, label: str) -> None:
        mapping = {
            self.t("export_txt"): ".txt",
            self.t("export_srt"): ".srt",
            self.t("export_vtt"): ".vtt",
            self.t("export_json"): ".json",
            self.t("export_csv"): ".csv",
        }
        extension = mapping.get(label)
        if extension:
            self.export_transcript(extension)
        self.export_menu.set(self.t("export"))

    def export_transcript(self, extension: str) -> None:
        if not self.transcript_data and not self.textbox.get("1.0", "end-1c").strip():
            messagebox.showinfo(self.t("export"), self.t("no_text"), parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=extension,
            initialfile=timestamped_name() + extension,
            filetypes=[(extension.upper().lstrip("."), f"*{extension}")],
        )
        if not path:
            return
        destination = Path(path)
        self._write_export(destination, self.transcript_data)
        self._set_status(self.t("saved", path=destination))
        if self.open_result_var.get():
            self.open_file_safe(destination)

    def _write_export(self, path: Path, segments: list[dict[str, Any]]) -> None:
        if path.suffix.lower() == ".txt":
            atomic_write_text(path, self.textbox.get("1.0", "end-1c").strip() + "\n")
        elif path.suffix.lower() == ".srt":
            atomic_write_text(path, create_srt_content(segments))
        elif path.suffix.lower() == ".vtt":
            atomic_write_text(path, create_vtt_content(segments))
        elif path.suffix.lower() == ".json":
            atomic_write_text(path, json.dumps(segments, ensure_ascii=False, indent=2))
        elif path.suffix.lower() == ".csv":
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".csv.tmp")
            with temporary.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["start", "end", "speaker", "source", "text"])
                for item in segments:
                    writer.writerow(
                        [
                            item.get("start", 0),
                            item.get("end", 0),
                            item.get("speaker", ""),
                            item.get("source", ""),
                            item.get("text", ""),
                        ]
                    )
            temporary.replace(path)

    def save_result_bundle(self, segments: list[dict[str, Any]], prefix: str) -> Path | None:
        if not segments:
            return None
        output_dir = Path(self.settings.get("output_folder"))
        safe_prefix = "".join(char if char.isalnum() or char in "-_ " else "_" for char in prefix).strip()
        base = output_dir / timestamped_name(safe_prefix or "Transcription")
        text = "\n".join(self.format_segment(item).rstrip() for item in segments) + "\n"
        atomic_write_text(base.with_suffix(".txt"), text)
        atomic_write_text(base.with_suffix(".srt"), create_srt_content(segments))
        atomic_write_text(base.with_suffix(".vtt"), create_vtt_content(segments))
        atomic_write_text(base.with_suffix(".json"), json.dumps(segments, ensure_ascii=False, indent=2))
        csv_path = base.with_suffix(".csv")
        temporary = csv_path.with_suffix(".csv.tmp")
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["start", "end", "speaker", "source", "text"])
            for item in segments:
                writer.writerow(
                    [
                        item.get("start", 0),
                        item.get("end", 0),
                        item.get("speaker", ""),
                        item.get("source", ""),
                        item.get("text", ""),
                    ]
                )
        temporary.replace(csv_path)
        self.backup_file.unlink(missing_ok=True)
        return base.with_suffix(".txt")

    @staticmethod
    def save_smart_subtitle(filepath: Path, segments: list[dict[str, Any]]) -> None:
        atomic_write_text(filepath.with_suffix(".srt"), create_srt_content(segments))

    def change_output_folder(self) -> None:
        folder = filedialog.askdirectory(
            parent=self,
            initialdir=self.settings.get("output_folder"),
            title=self.t("output_folder"),
        )
        if folder:
            Path(folder).mkdir(parents=True, exist_ok=True)
            self.settings.set("output_folder", folder, save=True)

    @staticmethod
    def open_file_safe(path: Path) -> None:
        try:
            if platform.system() == "Windows":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError:
            logging.exception("Could not open result: %s", path)

    def _start_job(self, estimated_seconds: float) -> None:
        self.busy = True
        self.job_started = time.monotonic()
        self.estimated_job_seconds = estimated_seconds
        self._last_progress = 0.0
        self._set_progress(0)
        self._set_source_buttons_state("disabled")
        self._set_status(self.t("processing"))
        self.eta_label.configure(
            text=self.t("remaining", time=format_duration(estimated_seconds))
            if estimated_seconds > 0
            else self.t("calculating")
        )

    def _finish_job(self, saved: Path | None, backend: str) -> None:
        self.busy = False
        self._set_progress(1.0)
        self._set_source_buttons_state("normal")
        self._set_status(f"{self.t('progress_done')} • {self.t('backend', backend=backend)}")
        self.eta_label.configure(text=self.t("autosaved") if saved else "")
        self.persist_settings()
        if saved and self.open_result_var.get():
            self.open_file_safe(saved)

    def _fail_job(self, error: Exception) -> None:
        self.busy = False
        self._set_source_buttons_state("normal")
        self._set_status(self.t("error"))
        self.eta_label.configure(text="")
        messagebox.showerror(self.t("error"), self.t("job_error", error=str(error)), parent=self)

    def _set_source_buttons_state(self, state: str) -> None:
        for button in getattr(self, "task_buttons", {}).values():
            button.configure(state=state)
        for button in getattr(self, "simple_task_buttons", {}).values():
            button.configure(state=state)
        for name in ("choose_button", "link_button", "record_button"):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.configure(state=state)
        if self.recorder.recording:
            self.record_button.configure(state="disabled")

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _set_progress(self, value: float) -> None:
        self._last_progress = max(0.0, min(1.0, float(value)))
        self.progress_bar.set(self._last_progress)

    def _tick_clock(self) -> None:
        if not self.running:
            return
        if self.busy or self.recorder.recording:
            elapsed = time.monotonic() - self.job_started
            if self.estimated_job_seconds > 0 and self._last_progress > 0.02:
                projected = elapsed / self._last_progress
                remaining = max(0.0, projected - elapsed)
                self.eta_label.configure(
                    text=f"{self.t('elapsed', time=format_duration(elapsed))} • "
                    f"{self.t('remaining', time=format_duration(remaining))}"
                )
            elif self.recorder.recording:
                self.eta_label.configure(text=self.t("elapsed", time=format_duration(elapsed)))
        self.after(500, self._tick_clock)

    def _safe_ui(self, callback: Callable[..., None], *args: Any) -> None:
        try:
            self.after(0, callback, *args)
        except (RuntimeError, tk.TclError):
            pass

    def _save_backup(self) -> None:
        if not self.transcript_data:
            return
        try:
            self.backup_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.backup_file.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.transcript_data, ensure_ascii=False), encoding="utf-8")
            temporary.replace(self.backup_file)
        except OSError:
            logging.exception("Could not save recovery data")

    def _load_recovery(self) -> None:
        try:
            data = json.loads(self.backup_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.transcript_data = data
        except (OSError, ValueError, TypeError):
            return

    def on_close(self) -> None:
        self.running = False
        if self.recorder.recording:
            self.recorder.stop()
            self.recorder.audio_queue.put(None)
        self.recorder.stop_monitor()
        self._save_backup()
        try:
            self.settings.set("window_geometry", self.geometry())
            self.persist_settings()
        except (tk.TclError, ValueError):
            pass
        self.destroy()
