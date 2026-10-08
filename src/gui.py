"""Local Transcriber Pro desktop interface."""

from __future__ import annotations

import json
import logging
import os
import platform
import queue
import sqlite3
import subprocess
import threading
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
import numpy as np
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


from src import __version__
from src.audio import SAMPLE_RATE, AudioRecorder
from src.conversation_ui import ConversationMixin
from src.diarizer import Diarizer
from src.editing import apply_text_edits
from src.estimator import TimeEstimator, format_duration
from src.exports import write_bundle, write_export
from src.hardware import HardwareProfile, ModelCompatibility, detect_hardware
from src.history import HistoryStore, SessionRecord
from src.i18n import Translator
from src.jobs import JobCancelled, check_cancelled
from src.media import RecordingSpool
from src.meter import TapeMeter
from src.models import (
    AUTO_FAST_MODEL_ID,
    AUTO_MODEL_ID,
    AUTO_MULTILINGUAL_MODEL_ID,
    get_model,
    model_capability_text,
    model_id_from_label,
    model_label,
    model_requirement_text,
    ranked_models,
)
from src.segments import shift_segments, validate_segments
from src.settings import SettingsStore, bounded_int, ensure_output_folder
from src.tooltip import ToolTip
from src.transcriber import EngineStatus, TranscriberEngine, TranscriptionOptions
from src.transcript_format import TranscriptFormat, format_transcript
from src.translation_languages import normalize_language
from src.translation_ui import TranslationControls, render_conversation
from src.update_ui import UpdatesMixin
from src.utils import (
    atomic_write_text,
    create_srt_content,
    timestamped_name,
)
from src.youtube_utils import download_youtube_audio, is_supported_url

APP_VERSION = __version__
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


def compatibility_text(t: Translator, compatibility: ModelCompatibility) -> str:
    if compatibility.supported:
        return t("model_ready_on", device=compatibility.device.upper())
    if compatibility.reason_code in {"cpu_runtime", "gpu_runtime", "model_runtime"}:
        return t(f"compat_{compatibility.reason_code}")
    return t(
        f"compat_{compatibility.reason_code}",
        required=compatibility.required,
        detected=compatibility.detected,
    )

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


class HistoryDialog(ctk.CTkToplevel):
    """Review every completed session without exposing database details."""

    def __init__(self, parent: TranscriberApp):
        super().__init__(parent)
        self.parent_app = parent
        self.t = parent.t
        self.title(self.t("history"))
        self.geometry("900x680")
        self.minsize(760, 520)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=BACKGROUND)

        heading = ctk.CTkFrame(self, fg_color="transparent")
        heading.pack(fill="x", padx=28, pady=(24, 10))
        ctk.CTkLabel(
            heading,
            text=self.t("history"),
            font=("Segoe UI", 25, "bold"),
            text_color=TEXT,
        ).pack(side="left")
        ctk.CTkButton(
            heading,
            text=self.t("open_transcriptions_folder"),
            command=lambda: parent.open_file_safe(parent.output_folder),
            fg_color=PANEL_ALT,
            hover_color="#233654",
            cursor="hand2",
        ).pack(side="right")
        ctk.CTkLabel(
            self,
            text=self.t("history_help", path=parent.output_folder),
            font=("Segoe UI", 12),
            text_color=MUTED,
            justify="left",
            wraplength=820,
        ).pack(anchor="w", padx=28, pady=(0, 12))

        scroll = ctk.CTkScrollableFrame(self, fg_color=PANEL, corner_radius=18)
        scroll.pack(fill="both", expand=True, padx=28, pady=(0, 14))
        records = parent.history.list_sessions()
        if not records:
            ctk.CTkLabel(
                scroll,
                text=self.t("history_empty"),
                font=("Segoe UI", 14),
                text_color=MUTED,
            ).pack(padx=22, pady=40)
        for record in records:
            self._add_record(scroll, record)
        ctk.CTkButton(
            self,
            text=self.t("close"),
            command=self.destroy,
            width=120,
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
            cursor="hand2",
        ).pack(pady=(0, 20))

    def _add_record(self, parent: ctk.CTkScrollableFrame, record: SessionRecord) -> None:
        row = ctk.CTkFrame(parent, fg_color=PANEL_ALT, corner_radius=14)
        row.pack(fill="x", padx=8, pady=6)
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.pack(side="left", fill="both", expand=True, padx=15, pady=12)
        try:
            created = time.strftime("%Y-%m-%d  %H:%M", time.localtime(time.mktime(time.strptime(record.created_at[:19], "%Y-%m-%dT%H:%M:%S"))))
        except ValueError:
            created = record.created_at[:16].replace("T", "  ")
        ctk.CTkLabel(
            text,
            text=f"{record.title}  •  {created}",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT,
            anchor="w",
        ).pack(fill="x")
        meta = self.t(
            "history_meta",
            task=self.t(f"task_{record.task}") if record.task in {"files", "conference", "dictation", "link"} else self.t("history_legacy"),
            duration=format_duration(record.duration_seconds),
            words=record.word_count,
            model=record.model or "—",
        )
        ctk.CTkLabel(
            text,
            text=meta,
            font=("Segoe UI", 11),
            text_color=ACCENT,
            anchor="w",
        ).pack(fill="x", pady=(3, 0))
        ctk.CTkLabel(
            text,
            text=record.preview or self.t("history_no_preview"),
            font=("Segoe UI", 11),
            text_color=MUTED,
            justify="left",
            wraplength=580,
            anchor="w",
        ).pack(fill="x", pady=(4, 0))
        buttons = ctk.CTkFrame(row, fg_color="transparent")
        buttons.pack(side="right", padx=12)
        available = Path(record.text_path).exists()
        ctk.CTkButton(
            buttons,
            text=self.t("history_load"),
            width=96,
            state="normal" if Path(record.json_path).exists() else "disabled",
            command=lambda: self._load(record),
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
            cursor="hand2",
        ).pack(pady=(8, 4))
        ctk.CTkButton(
            buttons,
            text=self.t("history_open"),
            width=96,
            state="normal" if available else "disabled",
            command=lambda: self.parent_app.open_file_safe(Path(record.text_path)),
            fg_color=BLUE,
            hover_color="#86BBFF",
            text_color="#07111F",
            cursor="hand2",
        ).pack(pady=(4, 8))

    def _load(self, record: SessionRecord) -> None:
        self.parent_app.load_history_session(record)
        self.destroy()


class HardwareDialog(ctk.CTkToplevel):
    def __init__(self, parent: TranscriberApp):
        super().__init__(parent)
        self.t = parent.t
        profile = parent.hardware
        self.title(self.t("hardware_title"))
        self.geometry("720x570")
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
            text=self.t(
                "recommended_model",
                model=profile.recommended_model(cached_model_ids=parent.engine.cached_model_ids()),
            ),
            font=("Segoe UI", 13),
            text_color=TEXT,
        ).pack(anchor="w", padx=18, pady=3)
        resources = self.t(
            "hardware_resources",
            available=profile.effective_available_ram_gb,
            total=profile.ram_gb,
            disk=profile.disk_free_gb,
            vram_free=profile.effective_free_vram_gb,
            vram_total=profile.gpu_vram_gb,
        )
        ctk.CTkLabel(
            status,
            text=resources,
            font=("Segoe UI", 12),
            text_color=MUTED,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(8, 2))
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
        ctk.CTkLabel(
            self,
            text=self.t("hardware_safety_explainer"),
            font=("Segoe UI", 12),
            text_color=MUTED,
            justify="left",
            wraplength=650,
        ).pack(anchor="w", padx=28, pady=(12, 4))
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=28, pady=18)
        ctk.CTkButton(
            buttons,
            text=self.t("model_requirements"),
            command=lambda: (self.destroy(), ModelSelectorDialog(parent)),
            fg_color=BLUE,
            hover_color="#86BBFF",
            text_color="#07111F",
        ).pack(side="left")
        ctk.CTkButton(
            buttons,
            text=self.t("close"),
            command=self.destroy,
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
        ).pack(side="right")


class ModelSelectorDialog(ctk.CTkToplevel):
    """Show every model while making unsafe choices visibly impossible."""

    def __init__(self, parent: TranscriberApp):
        super().__init__(parent)
        self.parent_app = parent
        self.t = parent.t
        self.cached = parent.engine.cached_model_ids()
        parent.hardware.refresh_resources()
        self.title(self.t("model_requirements"))
        self.geometry(f"{min(1180, parent.winfo_screenwidth() - 40)}x760")
        self.minsize(min(1040, parent.winfo_screenwidth() - 40), 580)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=BACKGROUND)

        ctk.CTkLabel(
            self,
            text=self.t("model_requirements"),
            font=("Segoe UI", 25, "bold"),
            text_color=TEXT,
        ).pack(anchor="w", padx=28, pady=(24, 4))
        ctk.CTkLabel(
            self,
            text=self.t("model_requirements_help"),
            font=("Segoe UI", 13),
            text_color=MUTED,
            justify="left",
            wraplength=960,
        ).pack(anchor="w", padx=28, pady=(0, 12))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=PANEL, corner_radius=18)
        self.scroll.pack(fill="both", expand=True, padx=28, pady=4)
        self._add_auto_row()
        self._add_auto_row(AUTO_FAST_MODEL_ID)
        self._add_auto_row(AUTO_MULTILINGUAL_MODEL_ID)
        for spec in ranked_models():
            self._add_model_row(spec.model_id)

        ctk.CTkButton(
            self,
            text=self.t("close"),
            command=self.destroy,
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
            width=120,
        ).pack(pady=(12, 20))

    def _add_auto_row(self, profile_id: str = AUTO_MODEL_ID) -> None:
        recommended = self.parent_app.hardware.resolve_model(
            profile_id, self.parent_app.selected_device, self.cached,
            self.parent_app.selected_language,
            "transcribe",
        )
        supported = self.parent_app.hardware.has_safe_model(
            self.parent_app.selected_device, self.cached
        )
        selected = self.parent_app.selected_model_id == profile_id
        row = ctk.CTkFrame(
            self.scroll,
            fg_color="#14372F" if selected else PANEL_ALT,
            corner_radius=14,
            border_width=1,
            border_color=ACCENT if selected else "#2A3C5E",
        )
        row.pack(fill="x", padx=8, pady=(8, 5))
        row.grid_columnconfigure(0, weight=1)
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.grid(row=0, column=0, sticky="nsew", padx=15, pady=12)
        ctk.CTkLabel(
            text,
            text=model_label(profile_id, self.t.language),
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            text,
            text=self.t("auto_multilingual_will_use" if profile_id == AUTO_MULTILINGUAL_MODEL_ID else (
                "auto_fast_will_use" if profile_id == AUTO_FAST_MODEL_ID else "auto_will_use"), model=recommended),
            font=("Segoe UI", 12),
            text_color=ACCENT if supported else RED,
        ).pack(anchor="w", pady=(3, 0))
        self._add_scores(row, recommended)
        ctk.CTkButton(
            row,
            text=self.t("selected" if selected else "select"),
            width=112,
            state="disabled" if selected or not supported else "normal",
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
            command=lambda: self._select(profile_id),
        ).grid(row=0, column=4, padx=14)

    def _add_scores(self, row: ctk.CTkFrame, model_id: str) -> None:
        spec = get_model(model_id)
        for column, label, score, color in (
            (1, self.t("model_precision_score"), spec.multilingual_score, ACCENT),
            (2, self.t("model_speed_score"), spec.relative_speed_score, BLUE),
            (3, self.t("model_coverage_score"), spec.coverage_score, AMBER),
        ):
            cell = ctk.CTkFrame(row, fg_color="transparent", width=100)
            cell.grid(row=0, column=column, padx=5, pady=12)
            ctk.CTkLabel(cell, text=label, font=("Segoe UI", 11), text_color=MUTED).pack()
            value = f"{score:.1f}/10" if score is not None else self.t("model_english_only_score")
            ctk.CTkLabel(cell, text=value, font=("Segoe UI", 18, "bold"), text_color=color).pack(pady=(3, 4))
            if score is not None:
                bar = ctk.CTkProgressBar(cell, width=100, height=5, progress_color=color)
                bar.set(score / 10)
                bar.pack()
            if column == 3:
                ctk.CTkLabel(cell, text=self.t("model_languages", count=spec.language_count),
                             font=("Segoe UI", 10), text_color=MUTED).pack(pady=(3, 0))

    def _add_model_row(self, model_id: str) -> None:
        compatibility = self.parent_app.hardware.model_compatibility(
            model_id,
            self.parent_app.selected_device,
            model_id in self.cached,
        )
        selected = self.parent_app.selected_model_id == model_id
        row = ctk.CTkFrame(
            self.scroll,
            fg_color="#14372F" if selected else (PANEL_ALT if compatibility.supported else "#111827"),
            corner_radius=14,
            border_width=1,
            border_color=ACCENT if selected else ("#2A3C5E" if compatibility.supported else "#222C3E"),
        )
        row.pack(fill="x", padx=8, pady=5)
        row.grid_columnconfigure(0, weight=1)
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.grid(row=0, column=0, sticky="nsew", padx=15, pady=11)
        ctk.CTkLabel(
            text,
            text=model_label(model_id, self.t.language),
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT if compatibility.supported else "#69768B",
            wraplength=450,
            justify="left",
        ).pack(anchor="w")
        ctk.CTkLabel(
            text,
            text=model_capability_text(model_id, self.t.language),
            font=("Segoe UI", 11),
            text_color=MUTED,
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            text,
            text=model_requirement_text(model_id, self.t.language),
            font=("Segoe UI", 11),
            text_color=MUTED if compatibility.supported else "#596579",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            text,
            text=compatibility_text(self.t, compatibility),
            font=("Segoe UI", 11, "bold"),
            text_color=ACCENT if compatibility.supported else AMBER,
        ).pack(anchor="w", pady=(3, 0))
        self._add_scores(row, model_id)
        ctk.CTkButton(
            row,
            text=self.t("selected" if selected else ("select" if compatibility.supported else "unavailable")),
            width=112,
            state="disabled" if selected or not compatibility.supported else "normal",
            fg_color=ACCENT_DARK if compatibility.supported else "#293244",
            hover_color=ACCENT,
            text_color_disabled="#647084",
            command=lambda value=model_id: self._select(value),
        ).grid(row=0, column=4, padx=14)

    def _select(self, model_id: str) -> None:
        self.parent_app._select_model(model_id)
        self.destroy()


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
        if self.parent_app.busy or self.parent_app.recorder.recording or self.parent_app.model_preloading:
            messagebox.showinfo(self.t("model_manager"), self.t("model_delete_busy"), parent=self)
            return
        if not messagebox.askyesno(self.t("model_manager"), self.t("confirm_delete"), parent=self):
            return
        if self.parent_app.engine.delete_model_file(path):
            self.refresh()
        else:
            messagebox.showerror(self.t("error"), self.t("job_error", error=path), parent=self)


class TranscriberApp(ConversationMixin, UpdatesMixin, ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(
        self,
        hardware: HardwareProfile | None = None,
        engine: TranscriberEngine | None = None,
        preloaded_status: EngineStatus | None = None,
        settings: SettingsStore | None = None,
        history: HistoryStore | None = None,
    ):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=BACKGROUND)

        self.settings = settings or SettingsStore()
        self.t = Translator(self.settings.get("ui_language"))
        self.hardware: HardwareProfile = hardware or detect_hardware()
        self.engine = engine or TranscriberEngine(self.hardware)
        self.estimator = TimeEstimator(self.settings.get("benchmarks", {}))
        self.recorder = AudioRecorder()
        self.diarizer = Diarizer()
        self.output_folder = ensure_output_folder(self.settings.get("output_folder"))
        self.settings.set("output_folder", str(self.output_folder))
        self.history = history or HistoryStore()
        self.history.index_existing(self.output_folder)

        self.ui_mode = self.settings.get("ui_mode", "simple")
        self.simple_quality = self.settings.get("simple_quality", "best")
        self.saved_microphone = self.settings.get("microphone", "auto")
        self.preset = self.settings.get("preset", "files")
        self.selected_model_id = self.settings.get("model", AUTO_MODEL_ID)
        self.selected_device = self.settings.get("device", "auto")
        self.selected_language = self.settings.get("spoken_language", "auto")
        self.transcript_layout = self.settings.get("transcript_layout", "blocks")
        self.show_timestamps = bool(self.settings.get("show_timestamps", True))
        self.show_duration = bool(self.settings.get("show_duration", False))
        self.maximum_quality_beam = (
            8
            if self.hardware.ram_gb >= 8 and self.hardware.effective_available_ram_gb >= 4
            else 5
        )
        self.maximum_quality_chunk = 30 if self.hardware.ram_gb >= 6 else 20
        if self.ui_mode == "simple":
            self.selected_model_id = AUTO_FAST_MODEL_ID if self.simple_quality == "fast" else AUTO_MODEL_ID
            self.selected_device = "auto"
        if self.preset == "universal":
            self.selected_model_id = self.settings.get("model", AUTO_MULTILINGUAL_MODEL_ID)
            if self.selected_model_id in {AUTO_MODEL_ID, AUTO_FAST_MODEL_ID}:
                self.selected_model_id = AUTO_MULTILINGUAL_MODEL_ID
            self.selected_language = "auto"
        available_devices = {"auto", "cpu"}
        if self.hardware.ctranslate_cuda or self.hardware.torch_cuda:
            available_devices.add("cuda")
        if self.hardware.mlx_available or self.hardware.torch_mps:
            available_devices.add("metal")
        if self.selected_device not in available_devices:
            self.selected_device = "auto"
        cached_models = self.engine.cached_model_ids()
        if self.selected_model_id not in {AUTO_MODEL_ID, AUTO_FAST_MODEL_ID, AUTO_MULTILINGUAL_MODEL_ID} and not self.hardware.model_compatibility(
            self.selected_model_id,
            self.selected_device,
            self.selected_model_id in cached_models,
        ).supported:
            self.selected_model_id = AUTO_MODEL_ID
            self.simple_quality = "best"
        self.hardware_ready = self.hardware.has_safe_model(self.selected_device, cached_models)
        self.pending_files: list[str] = []
        self.transcript_data: list[dict[str, Any]] = []
        self.recording_spool: RecordingSpool | None = None
        self.recording_offset = 0.0
        self.running = True
        self.closing = False
        self.update_checking = False
        self.cancel_event = threading.Event()
        self.ui_tasks: queue.Queue = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self._rendered_text = ""
        self.busy = False
        self.job_started = 0.0
        self.estimated_job_seconds = 0.0
        self._last_progress = 0.0
        self.microphone_auto_selected = False
        self.selected_microphone_name = ""
        self.last_engine_status = preloaded_status
        self.preload_generation = 0
        self.model_preloading = False
        self.active_recording_base: Path | None = None
        self.translation_target = self.settings.get("translation_target", "fr" if self.t.language == "fr" else "en")
        self.conversation_partner = self.settings.get("conversation_partner", "auto")
        self.translation_third = self.settings.get("translation_third", "none")
        self.conversation_font_size = self.settings.get("conversation_font_size", 22)
        self.reading_view = False
        self.pipeline_stage = "waiting"
        self.pipeline_started = time.monotonic()

        data_dir = history.database_path.parent if history is not None else Path(user_data_dir("LocalTranscriberPro", "Vhaloo"))
        data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_file = data_dir / "unsaved_session.json"

        self.translate_var = ctk.BooleanVar(value=self.preset == "universal" or bool(self.settings.get("translate")))
        self.speaker_var = ctk.BooleanVar(value=bool(self.settings.get("speaker_detection")))
        self.vad_var = ctk.BooleanVar(value=bool(self.settings.get("vad", True)))
        self.cleanup_var = ctk.BooleanVar(value=bool(self.settings.get("cleanup", True)))
        self.open_result_var = ctk.BooleanVar(value=bool(self.settings.get("open_result")))
        self.smart_subtitles_var = ctk.BooleanVar(value=bool(self.settings.get("smart_subtitles", True)))
        self.chunk_var = ctk.StringVar(value=str(self.settings.get("chunk_seconds", 30)))
        self.beam_var = ctk.StringVar(value=str(self.settings.get("beam_size", 8)))
        if self.ui_mode == "simple":
            self.chunk_var.set(str(self.maximum_quality_chunk))
            self.beam_var.set(str(self.maximum_quality_beam))
        if self.preset == "universal":
            self.chunk_var.set("12")
            self.speaker_var.set(False)
        self.layout_var = ctk.StringVar(value=self.transcript_layout)
        self.show_timestamps_var = ctk.BooleanVar(value=self.show_timestamps)
        self.show_duration_var = ctk.BooleanVar(value=self.show_duration)

        self._load_recovery()
        self.title(f"Local Transcriber Pro {APP_VERSION}")
        geometry = self.settings.get("window_geometry", "1220x940").split("+")[0].split("-")[0]
        width, height = (int(value) for value in geometry.split("x"))
        self.geometry(f"{min(width, self.winfo_screenwidth() - 40)}x{min(height, self.winfo_screenheight() - 80)}")
        self.minsize(min(1000, self.winfo_screenwidth() - 40), min(760, self.winfo_screenheight() - 80))
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._init_drag_and_drop()
        self.build_ui()
        self._bind_shortcuts()
        self.render_transcript()
        if preloaded_status is not None:
            self.after(80, self._show_preloaded_model_ready)
        else:
            self.after(700, self.preload_selected_model)
        self.after(500, self._tick_clock)
        self.after(350, self._start_microphone_monitor)
        self.after(80, self._update_microphone_meter)
        self.after(25, self._drain_ui_tasks)
        self.after(2000, self._autosave_editor)
        if self.settings.get("check_updates", True):
            self.after(3500, lambda: self.check_updates(silent=True))

    def _bind_shortcuts(self) -> None:
        def action(callback):
            def invoke(_event):
                callback()
                return "break"
            return invoke

        self.bind("<Control-o>", action(self.choose_files))
        self.bind("<Control-s>", action(lambda: self.export_transcript(".txt")))
        self.bind("<Control-Shift-S>", action(lambda: self.export_transcript(".srt")))
        self.bind("<Control-Shift-R>", action(self._recording_shortcut))
        self.bind("<Control-p>", action(self.toggle_pause))
        self.bind("<Escape>", action(self._escape_action))
        self.bind("<F11>", action(self.toggle_reading_view))
        self.bind("<Control-plus>", action(lambda: self.change_transcript_font(2)))
        self.bind("<Control-minus>", action(lambda: self.change_transcript_font(-2)))

    def _recording_shortcut(self) -> None:
        if self.recorder.recording:
            self.stop_recording()
        elif not self.busy and not self.closing:
            self.select_preset("dictation")
            self.start_recording()

    def _init_drag_and_drop(self) -> None:
        self.TkdndVersion = None
        if not HAS_DND:
            return
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except Exception:
            logging.exception("Drag-and-drop initialization failed")

    def _build_blocking_overlay(self) -> None:
        self.blocking_overlay = ctk.CTkFrame(
            self,
            fg_color="#050A13",
            corner_radius=0,
        )
        card = ctk.CTkFrame(
            self.blocking_overlay,
            width=650,
            height=340,
            fg_color=PANEL,
            corner_radius=32,
            border_width=2,
            border_color=ACCENT_DARK,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)
        self.blocking_badge = ctk.CTkLabel(
            card,
            text=self.t("initializing_badge"),
            fg_color="#12392F",
            corner_radius=14,
            text_color=ACCENT,
            font=("Segoe UI", 11, "bold"),
            padx=12,
            pady=5,
        )
        self.blocking_badge.pack(pady=(34, 18))
        self.blocking_title = ctk.CTkLabel(
            card,
            text=self.t("record_initializing_title"),
            font=("Segoe UI", 25, "bold"),
            text_color=TEXT,
        )
        self.blocking_title.pack(padx=34)
        self.blocking_detail = ctk.CTkLabel(
            card,
            text=self.t("record_initializing_help"),
            font=("Segoe UI", 14),
            text_color=MUTED,
            justify="center",
            wraplength=560,
        )
        self.blocking_detail.pack(padx=34, pady=(12, 24))
        self.blocking_progress = ctk.CTkProgressBar(
            card,
            width=500,
            height=12,
            mode="indeterminate",
            progress_color=ACCENT,
            fg_color="#26344D",
        )
        self.blocking_progress.pack()
        ctk.CTkLabel(
            card,
            text=self.t("record_initializing_patience"),
            font=("Segoe UI", 11),
            text_color=AMBER,
        ).pack(pady=(18, 0))
        self.blocking_overlay.place_forget()

    def _show_recording_initialization(self) -> None:
        self.blocking_title.configure(text=self.t("record_initializing_title"))
        self.blocking_detail.configure(text=self.t("record_initializing_help"))
        self.blocking_overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.blocking_overlay.lift()
        self.blocking_overlay.focus_set()
        self.blocking_progress.start()
        self.update_idletasks()

    def _set_initialization_detail(self, text: str) -> None:
        if hasattr(self, "blocking_detail") and self.blocking_overlay.winfo_ismapped():
            self.blocking_detail.configure(text=text)

    def _hide_recording_initialization(self) -> None:
        if not hasattr(self, "blocking_overlay"):
            return
        self.blocking_progress.stop()
        self.blocking_overlay.place_forget()

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
        self._build_blocking_overlay()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame = header
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
        self.history_button = ctk.CTkButton(
            controls,
            text=self.t("history"),
            width=94,
            height=36,
            fg_color=PANEL,
            hover_color=PANEL_ALT,
            command=lambda: HistoryDialog(self),
            cursor="hand2",
        )
        self.history_button.pack(side="left", padx=5)
        ToolTip(self.history_button, self.t("tip_history"))
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
        self.updates_button = ctk.CTkButton(
            controls, text="↻", width=36, height=36, fg_color=PANEL, hover_color=PANEL_ALT,
            font=("Segoe UI", 20), command=self.check_updates,
        )
        self.updates_button.pack(side="left", padx=5)
        ToolTip(self.updates_button, self.t("updates"))
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
            ("universal", "simple_task_universal", "task_universal_help"),
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
        self.simple_choices = choices
        choices.grid(row=2, column=0, sticky="ew", padx=20, pady=(11, 6))
        for column in range(3):
            choices.grid_columnconfigure(column, weight=1)

        quality_box = ctk.CTkFrame(choices, fg_color="transparent")
        quality_box.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(quality_box, text=self.t("simple_quality"), text_color=MUTED).pack(anchor="w")
        self.quality_control = ctk.CTkSegmentedButton(
            quality_box, values=[self.t("quality_best"), self.t("quality_fast")],
            height=38, corner_radius=19, selected_color=ACCENT_DARK,
            unselected_color=PANEL_ALT, command=self._simple_quality_changed,
        )
        self.quality_control.pack(fill="x", pady=(4, 0))
        self.quality_control.set(self.t("quality_fast" if self.simple_quality == "fast" else "quality_best"))
        ToolTip(self.quality_control, self.t("tip_quality_automatic"))

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

        automatic_model = self.hardware.recommended_model(
            self.selected_device, self.engine.cached_model_ids()
        )
        self.simple_auto_summary_label = ctk.CTkLabel(
            self.simple_panel,
            text=self.t(
                "simple_automatic_summary",
                model=automatic_model,
                device=self.hardware.display_device,
            ),
            font=("Segoe UI", 11),
            text_color=ACCENT if self.hardware_ready else RED,
        )
        self.simple_auto_summary_label.grid(row=3, column=0, sticky="w", padx=22, pady=(3, 13))

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
            ("universal", "task_universal", "task_universal_help"),
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
        self.file_controls.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 18))
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
        self.record_controls.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 18))
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
            width=122,
            height=50,
            corner_radius=25,
            state="disabled",
            fg_color="#60708A",
            hover_color=RED,
            font=("Segoe UI", 13, "bold"),
            command=self.stop_recording,
            cursor="hand2",
        )
        self.stop_button.grid(row=0, column=4, padx=(4, 0))
        ToolTip(self.stop_button, self.t("tip_stop"))

        self.link_controls = ctk.CTkFrame(self.source_card, fg_color="transparent")
        self.link_controls.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 18))
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
        self.translation_controls = TranslationControls(self, self.source_card)
        self.translation_controls.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))

    def open_model_selector(self) -> None:
        if not self.busy and not self.recorder.recording:
            ModelSelectorDialog(self)

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

        model_box = ctk.CTkFrame(self.advanced_panel, fg_color="transparent")
        model_box.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        ctk.CTkLabel(
            model_box,
            text=self.t("model"),
            font=("Segoe UI", 11),
            text_color=MUTED,
        ).pack(anchor="w")
        self.model_button = ctk.CTkButton(
            model_box,
            text=model_label(self.selected_model_id, self.t.language),
            height=34,
            fg_color=PANEL_ALT,
            hover_color="#233654",
            border_width=1,
            border_color=ACCENT,
            command=lambda: ModelSelectorDialog(self),
        )
        self.model_button.pack(fill="x", pady=(4, 0))
        ToolTip(self.model_button, self.t("model_help"))

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
                command=self._translation_toggled if key == "translate" else self.persist_settings,
            )
            widget.grid(row=index // 4, column=index % 4, sticky="w", padx=6, pady=7)
            ToolTip(widget, self.t(tip_key))
        self.update_var = ctk.BooleanVar(value=self.settings.get("check_updates", True))
        ctk.CTkCheckBox(checks, text=self.t("update_automatic"), variable=self.update_var,
                       font=("Segoe UI", 12), checkbox_width=20, checkbox_height=20,
                       fg_color=ACCENT_DARK, command=self.persist_settings).grid(row=1, column=2, sticky="w", padx=6, pady=7)
        self.keep_audio_var = ctk.BooleanVar(value=self.settings.get("keep_recording_audio", True))
        ctk.CTkCheckBox(checks, text=self.t("keep_audio"), variable=self.keep_audio_var,
                       font=("Segoe UI", 12), checkbox_width=20, checkbox_height=20,
                       fg_color=ACCENT_DARK, command=self.persist_settings).grid(row=1, column=3, sticky="w", padx=6, pady=7)

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

        formatting = ctk.CTkFrame(self.advanced_panel, fg_color="transparent")
        formatting.grid(row=4, column=0, columnspan=4, sticky="ew", padx=20, pady=(0, 15))
        ctk.CTkLabel(
            formatting,
            text=self.t("transcript_layout"),
            text_color=MUTED,
        ).pack(side="left")
        self.layout_display_map = {
            self.t("layout_blocks"): "blocks",
            self.t("layout_lines"): "lines",
        }
        selected_layout = next(
            (
                label
                for label, value in self.layout_display_map.items()
                if value == self.transcript_layout
            ),
            self.t("layout_blocks"),
        )
        self.layout_combo = ctk.CTkComboBox(
            formatting,
            values=list(self.layout_display_map),
            width=150,
            height=32,
            fg_color=PANEL_ALT,
            border_color="#2A3C5E",
            dropdown_fg_color=PANEL_ALT,
            command=self._layout_changed,
        )
        self.layout_combo.set(selected_layout)
        self.layout_combo.pack(side="left", padx=(7, 20))
        ToolTip(self.layout_combo, self.t("tip_layout"))
        self.timestamps_check = ctk.CTkCheckBox(
            formatting,
            text=self.t("show_timestamps"),
            variable=self.show_timestamps_var,
            checkbox_width=20,
            checkbox_height=20,
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
            command=self._format_options_changed,
        )
        self.timestamps_check.pack(side="left", padx=8)
        ToolTip(self.timestamps_check, self.t("tip_timestamps"))
        self.duration_check = ctk.CTkCheckBox(
            formatting,
            text=self.t("show_duration"),
            variable=self.show_duration_var,
            checkbox_width=20,
            checkbox_height=20,
            fg_color=ACCENT_DARK,
            hover_color=ACCENT,
            command=self._format_options_changed,
        )
        self.duration_check.pack(side="left", padx=8)
        ToolTip(self.duration_check, self.t("tip_duration"))

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
        self.output_card = output
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
        self.cancel_button = ctk.CTkButton(progress_row, text=self.t("cancel_job"), width=88, height=29,
                                          fg_color="#5A2430", hover_color=RED, state="disabled",
                                          command=self.cancel_job)
        self.cancel_button.grid(row=0, column=2, padx=(12, 0))
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
        self.vocabulary_button = ctk.CTkButton(toolbar, text=self.t("vocabulary"), width=108, height=31,
                                              fg_color=PANEL_ALT, command=self.edit_vocabulary)
        self.vocabulary_button.grid(row=0, column=4, padx=(8, 0))
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
        self._build_conversation_toolbar(toolbar)

        self.textbox = ctk.CTkTextbox(
            output,
            height=250,
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
        if self.hardware.ctranslate_cuda or self.hardware.torch_cuda:
            values[self.t("device_cuda")] = "cuda"
        if self.hardware.mlx_available or self.hardware.torch_mps:
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
        if self.reading_view:
            for frame in (self.header_frame, self.simple_panel, self.task_frame, self.source_card, self.advanced_panel):
                frame.grid_remove()
            self.output_card.grid_configure(padx=12, pady=12)
            return
        self.header_frame.grid()
        self.source_card.grid()
        self.output_card.grid_configure(padx=28, pady=(6, 22))
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
        if self.preset == "universal":
            self.advanced_panel.grid_remove()
            self.simple_choices.grid_remove()
            self.source_title.grid_remove()
            self.source_help.grid_remove()
            self.microphone_meter.configure(height=56)
        else:
            self.simple_choices.grid()

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
            "universal": ("task_universal", "task_universal_help"),
        }
        title_key, help_key = mapping.get(self.preset, mapping["files"])
        if self.ui_mode == "simple":
            action_key = {
                "files": "action_files",
                "conference": "action_conference",
                "dictation": "action_dictation",
                "link": "action_link",
                "universal": "action_universal",
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
        elif self.preset in {"conference", "dictation", "universal"}:
            self.record_controls.grid()
        else:
            self.link_controls.grid()
        if self.translate_var.get() or self.preset == "universal":
            self.translation_controls.grid()
            self.translation_controls.refresh()
        else:
            self.translation_controls.grid_remove()

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
        if not self.running or self.closing:
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
            self._update_pipeline_display()
        except (AttributeError, tk.TclError):
            pass
        self.after(60, self._update_microphone_meter)

    def _simple_language_changed(self, label: str) -> None:
        self.selected_language = self.simple_language_map.get(label, "auto")
        if hasattr(self, "language_combo"):
            selected = next(
                (name for name, value in self.language_display_map.items() if value == self.selected_language),
                next(iter(self.language_display_map)),
            )
            self.language_combo.set(selected)
        self.persist_settings()
        self._update_model_indicators()

    def _simple_quality_changed(self, label: str) -> None:
        if self.busy or self.recorder.recording:
            self.quality_control.set(self.t("quality_fast" if self.simple_quality == "fast" else "quality_best"))
            return
        self.simple_quality = "fast" if label == self.t("quality_fast") else "best"
        self.selected_model_id = AUTO_FAST_MODEL_ID if self.simple_quality == "fast" else AUTO_MODEL_ID
        self.persist_settings()
        self._update_model_indicators()
        self.preload_selected_model()

    def _layout_changed(self, label: str) -> None:
        self._commit_editor_changes()
        self.transcript_layout = self.layout_display_map.get(label, "blocks")
        self.layout_var.set(self.transcript_layout)
        self.persist_settings()
        self.render_transcript()

    def _format_options_changed(self) -> None:
        self._commit_editor_changes()
        self.show_timestamps = bool(self.show_timestamps_var.get())
        self.show_duration = bool(self.show_duration_var.get())
        self.persist_settings()
        self.render_transcript()

    def _apply_maximum_quality_defaults(self, preset: str) -> None:
        """Make Simple mode choose quality and stability, never speed."""
        self.selected_model_id = AUTO_FAST_MODEL_ID if self.simple_quality == "fast" else AUTO_MODEL_ID
        self.selected_device = "auto"
        self.beam_var.set(str(self.maximum_quality_beam))
        self.chunk_var.set(str(self.maximum_quality_chunk))
        self.vad_var.set(True)
        self.cleanup_var.set(True)
        self.smart_subtitles_var.set(True)
        self.translate_var.set(False)
        self.speaker_var.set(preset == "conference")
        if preset == "universal":
            self.selected_model_id = AUTO_MULTILINGUAL_MODEL_ID
            self.selected_language = "auto"
            self.translate_var.set(True)
            self.chunk_var.set("12")

    def toggle_language(self) -> None:
        self._commit_editor_changes()
        self.t.set_language("fr" if self.t.language == "en" else "en")
        self.settings.set("ui_language", self.t.language, save=True)
        self.build_ui()
        self.render_transcript()

    def toggle_mode(self) -> None:
        if self.busy or self.recorder.recording:
            return
        self.ui_mode = "advanced" if self.ui_mode == "simple" else "simple"
        if self.ui_mode == "simple":
            self._apply_maximum_quality_defaults(self.preset)
            if self.selected_language not in {"auto", "fr", "en"}:
                self.selected_language = "auto"
                self.simple_language_control.set(self.t("language_auto"))
            self._update_model_indicators()
        self.settings.set("ui_mode", self.ui_mode, save=True)
        self._apply_mode_visibility()
        self._update_source_context()
        self.persist_settings()
        self.preload_selected_model()

    def select_preset(self, preset: str) -> None:
        if self.busy or self.recorder.recording:
            return
        previous = self.preset
        self.preset = preset
        if previous == "universal" and preset != "universal":
            self.translate_var.set(False)
            self.selected_model_id = AUTO_MODEL_ID
        if self.ui_mode == "simple":
            self._apply_maximum_quality_defaults(preset)
            self._update_model_indicators()
        elif preset == "universal":
            self.selected_model_id = AUTO_MULTILINGUAL_MODEL_ID
            self.selected_device = "auto"
            self.selected_language = "auto"
            self.translate_var.set(True)
            self.speaker_var.set(False)
            self.vad_var.set(True)
            self.chunk_var.set("12")
        elif preset == "conference":
            self.speaker_var.set(True)
            self.chunk_var.set("30")
        elif preset == "dictation":
            self.speaker_var.set(False)
            self.chunk_var.set("10")
        self.settings.set("preset", preset)
        self.persist_settings()
        self._refresh_task_styles()
        self._apply_mode_visibility()
        self._update_source_context()
        self._update_model_indicators()
        self.render_transcript()
        self.preload_selected_model()

    def _model_changed(self, label: str) -> None:
        self._select_model(model_id_from_label(label, self.t.language))

    def _select_model(self, model_id: str) -> None:
        if self.busy or self.recorder.recording:
            return
        cached = self.engine.cached_model_ids()
        if model_id not in {AUTO_MODEL_ID, AUTO_FAST_MODEL_ID, AUTO_MULTILINGUAL_MODEL_ID}:
            compatibility = self.hardware.model_compatibility(
                model_id, self.selected_device, model_id in cached
            )
            if not compatibility.supported:
                messagebox.showwarning(
                    self.t("warning"), compatibility_text(self.t, compatibility), parent=self
                )
                return
        self.selected_model_id = model_id
        self.simple_quality = {
            AUTO_MODEL_ID: "best",
            AUTO_FAST_MODEL_ID: "fast",
            "large-v3-turbo": "fast",
            "tiny": "light",
        }.get(self.selected_model_id, "best")
        self._update_model_indicators()
        self.persist_settings()
        self.preload_selected_model()

    def _device_changed(self, label: str) -> None:
        if self.busy or self.recorder.recording:
            return
        self.selected_device = self.device_display_map.get(label, "auto")
        cached = self.engine.cached_model_ids()
        if self.selected_model_id not in {AUTO_MODEL_ID, AUTO_FAST_MODEL_ID, AUTO_MULTILINGUAL_MODEL_ID} and not self.hardware.model_compatibility(
            self.selected_model_id,
            self.selected_device,
            self.selected_model_id in cached,
        ).supported:
            self.selected_model_id = AUTO_MODEL_ID
            self.simple_quality = "best"
        self._update_model_indicators()
        self.persist_settings()
        self.preload_selected_model()

    def _update_model_indicators(self) -> None:
        if hasattr(self, "model_button"):
            self.model_button.configure(text=model_label(self.selected_model_id, self.t.language))
        if hasattr(self, "simple_auto_summary_label"):
            resolved = self.hardware.resolve_model(
                self.selected_model_id,
                self.selected_device,
                self.engine.cached_model_ids(),
            )
            self.simple_auto_summary_label.configure(
                text=self.t(
                    "universal_automatic_summary" if self.preset == "universal" else "simple_automatic_summary",
                    model=resolved,
                    device=self.hardware.display_device,
                    count=get_model(resolved).language_count,
                )
            )

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
                "translation_target": self.translation_target,
                "conversation_partner": self.conversation_partner,
                "translation_third": self.translation_third,
                "conversation_font_size": self.conversation_font_size,
                "show_confidence": bool(self.show_confidence_var.get()),
                "overlap_separation": bool(self.overlap_var.get()),
                "speaker_detection": bool(self.speaker_var.get()),
                "vad": bool(self.vad_var.get()),
                "cleanup": bool(self.cleanup_var.get()),
                "open_result": bool(self.open_result_var.get()),
                "smart_subtitles": bool(self.smart_subtitles_var.get()),
                "chunk_seconds": bounded_int(self.chunk_var.get(), 30, 5, 60),
                "beam_size": bounded_int(self.beam_var.get(), 8, 1, 10),
                "check_updates": bool(self.update_var.get()),
                "keep_recording_audio": bool(self.keep_audio_var.get()),
                "transcript_layout": self.transcript_layout,
                "show_timestamps": self.show_timestamps,
                "show_duration": self.show_duration,
                "output_folder": str(self.output_folder),
                "benchmarks": self.estimator.benchmarks,
            },
            save=True,
        )

    def job_config(self) -> dict[str, Any]:
        return {
            "model": self.selected_model_id,
            "device": self.selected_device,
            "language": None if self.selected_language == "auto" or self.preset == "universal" else self.selected_language,
            "task": "transcribe",
            "target_language": self.translation_target if self.translate_var.get() or self.preset == "universal" else None,
            "conversation": self.preset == "universal",
            "partner_language": None if self.conversation_partner == "auto" else self.conversation_partner,
            "third_language": None if self.translation_third == "none" else self.translation_third,
            "speaker": bool(self.speaker_var.get()) and self.preset != "universal",
            "vad": bool(self.vad_var.get()),
            "cleanup": bool(self.cleanup_var.get()),
            "smart_subtitles": bool(self.smart_subtitles_var.get()),
            "open_result": bool(self.open_result_var.get()),
            "beam": bounded_int(self.beam_var.get(), 8, 1, 10),
            "chunk": 12 if self.preset == "universal" else bounded_int(self.chunk_var.get(), 30, 5, 60),
            "vocabulary": self.settings.get("vocabulary", ""),
            "keep_audio": bool(self.settings.get("keep_recording_audio", True)),
            "overlap_separation": bool(self.overlap_var.get()),
        }

    def transcribe_options(self, config: dict[str, Any]) -> TranscriptionOptions:
        return TranscriptionOptions(
            task=config["task"],
            language=config["language"],
            beam_size=config["beam"],
            vad_filter=config["vad"],
            word_timestamps=True,
            initial_prompt=config.get("vocabulary") or None,
            cancel_event=self.cancel_event,
            target_language=config.get("target_language"),
            conversation=config.get("conversation", False),
            partner_language=config.get("partner_language"),
            third_language=config.get("third_language") if config.get("conversation") else None,
            activity_callback=lambda stage: self._safe_ui(self._pipeline_activity, stage),
            overlap_separation=config.get("overlap_separation", False),
            original_callback=(lambda result: self._safe_ui(self._preview_conversation, result, self.recording_offset))
                if config.get("conversation") else None,
        )

    def _engine_load_status(self, stage: str, model: str, device: str) -> None:
        key = {
            "resource_check": "load_resource_check",
            "model_download": "load_model_download",
            "model_cached": "load_model_cached",
            "engine_start": "load_engine_start",
            "safe_fallback": "load_safe_fallback",
            "translation_prepare": "load_translation_prepare",
            "separation_prepare": "load_separation_prepare",
        }.get(stage, "progress_loading")
        self._safe_ui(
            self._set_status,
            self.t(key, model=model, device=device.upper()),
        )
        self._safe_ui(
            self._set_initialization_detail,
            self.t(key, model=model, device=device.upper()),
        )

    def _show_preloaded_model_ready(self) -> None:
        if self.last_engine_status is None:
            return
        self.model_preloading = False
        if self.busy or self.recorder.recording or self.closing:
            return
        self._set_status(
            self.t(
                "model_armed",
                model=self.last_engine_status.model_id,
                device=self.last_engine_status.device.upper(),
            )
        )
        self._update_model_indicators()
        if self.engine.translator.model is not None:
            self._set_status(self.t("translation_armed", model=self.last_engine_status.model_id,
                                    device=self.engine.translator.device.upper()))

    def preload_selected_model(self) -> None:
        if self.closing:
            return
        if self.busy or self.recorder.recording:
            self.after(1000, self.preload_selected_model)
            return
        self.preload_generation += 1
        generation = self.preload_generation
        model = self.selected_model_id
        device = self.selected_device
        options = self.transcribe_options(self.job_config())
        self.model_preloading = True
        resolved = self.hardware.resolve_model(model, device, self.engine.cached_model_ids(),
                                               options.language, options.task)
        self._set_status(self.t("model_arming", model=resolved))
        if self.preset in {"conference", "dictation", "universal"}:
            self.record_button.configure(state="disabled", text=self.t("arming"))

        threading.Thread(
            target=self._preload_worker,
            args=(generation, model, device, options),
            daemon=True,
            name="model-preload",
        ).start()

    def _preload_worker(self, generation: int, model: str, device: str, options: TranscriptionOptions) -> None:
        try:
            status = self.engine.load_model(model, device,
                lambda stage, selected, mode: self._safe_ui(self._preload_progress, generation, stage, selected, mode), options)
            self._safe_ui(self._finish_preload, generation, status)
        except Exception as error:
            logging.exception("Background model preload failed")
            self._safe_ui(self._fail_preload, generation, error)

    def _preload_progress(self, generation: int, stage: str, model: str, device: str) -> None:
        if generation == self.preload_generation and not self.busy and not self.recorder.recording and not self.closing:
            self._engine_load_status(stage, model, device)

    def _finish_preload(self, generation: int, status: EngineStatus) -> None:
        if generation != self.preload_generation:
            return
        self.last_engine_status = status
        self.model_preloading = False
        self._show_preloaded_model_ready()
        if not self.busy and not self.recorder.recording:
            self.record_button.configure(state="normal", text=self.t("record"))

    def _fail_preload(self, generation: int, error: Exception) -> None:
        if generation != self.preload_generation:
            return
        self.model_preloading = False
        self._set_status(self.t("model_preload_failed", error=error))
        if not self.busy and not self.recorder.recording:
            self.record_button.configure(state="normal", text=self.t("record"))

    def _model_is_armed(self, config: dict[str, Any]) -> bool:
        if self.model_preloading:
            return False
        try:
            return self.engine.is_ready(config["model"], config["device"]) and (
                not config.get("target_language") or self.engine.translator.model is not None)
        except (OSError, RuntimeError, ValueError):
            return False

    def _can_start_safely(self) -> bool:
        cached = self.engine.cached_model_ids()
        if self.hardware.has_safe_model(self.selected_device, cached):
            return True
        messagebox.showerror(
            self.t("error"),
            self.t("no_safe_model"),
            parent=self,
        )
        return False

    def choose_files(self) -> None:
        if self.busy or self.recorder.recording or self.closing:
            return
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
        if self.busy or self.recorder.recording or self.closing:
            return
        if not self._can_start_safely():
            return
        valid = list(dict.fromkeys(str(Path(path).resolve()) for path in paths
                                   if Path(path).suffix.lower() in AUDIO_VIDEO_EXTENSIONS and Path(path).is_file()))
        if not valid:
            messagebox.showwarning(self.t("warning"), self.t("no_files"), parent=self)
            return
        config = self.job_config()
        durations = [self.engine.audio_duration(path) for path in valid]
        total_audio = sum(durations)
        cached = self.engine.cached_model_ids()
        resolved_model = self.hardware.resolve_model(config["model"], config["device"], cached)
        compatibility = self.hardware.model_compatibility(
            resolved_model, config["device"], resolved_model in cached
        )
        resolved_device = compatibility.device
        estimate = self.estimator.estimate(total_audio, resolved_model, resolved_device)
        self._start_job(estimate.seconds)
        self.worker_thread = threading.Thread(
            target=self._batch_worker,
            args=(valid, durations, config),
            daemon=True,
            name="batch-transcription",
        )
        self.worker_thread.start()

    def _batch_worker(self, paths: list[str], durations: list[float], config: dict[str, Any]) -> None:
        try:
            resolved = self.hardware.resolve_model(
                config["model"], config["device"], self.engine.cached_model_ids()
            )
            self._safe_ui(self._set_status, self.t("progress_loading", model=resolved))
            status = self.engine.load_model(
                config["model"], config["device"], self._engine_load_status, self.transcribe_options(config)
            )
            self.last_engine_status = status
            session_offset = self.transcript_data[-1].get("end", 0.0) + 1.0 if self.transcript_data else 0.0
            total = len(paths)
            last_saved: Path | None = None
            failed: list[str] = []
            done = 0
            for index, (filepath, duration) in enumerate(
                zip(paths, durations, strict=True), start=1
            ):
                check_cancelled(self.cancel_event)
                name = Path(filepath).name
                self._safe_ui(
                    self._set_status,
                    self.t("progress_file", name=name, index=index, total=total),
                )
                started = time.monotonic()

                def progress(value: float, file_index=index) -> None:
                    self._safe_ui(self._set_progress, ((file_index - 1) + value) / total)

                try:
                    result = self.engine.transcribe_file(
                        filepath, self.transcribe_options(config), progress_callback=progress,
                    )
                    segments = self._prepare_segments(result.get("segments", []), config["cleanup"])
                    if config["speaker"] and segments:
                        self._safe_ui(self._set_status, self.t("progress_diarizing"))
                        segments = self.diarizer.process(filepath, segments, callback=logging.info, cancel_event=self.cancel_event)
                    file_segments = [dict(item, source=name) for item in segments]
                    display_segments = shift_segments(file_segments, session_offset)
                    self._safe_ui(self._append_segments, display_segments)
                    saved = self.save_result_bundle(file_segments, Path(filepath).stem)
                    if saved is not None:
                        last_saved = saved
                    if config["smart_subtitles"] and Path(filepath).suffix.lower() in VIDEO_EXTENSIONS:
                        try:
                            self.save_smart_subtitle(Path(filepath), file_segments)
                        except OSError:
                            logging.exception("Could not write subtitle beside %s; output-folder exports were saved", filepath)
                    done += 1
                except JobCancelled:
                    raise
                except Exception:
                    logging.exception("Skipping failed batch file: %s", filepath)
                    failed.append(name)
                    progress(1.0)
                    continue
                observed_audio = duration or result.get("duration", 0.0)
                self.estimator.observe(
                    observed_audio,
                    result.get("processing_seconds", time.monotonic() - started),
                    status.model_id,
                    status.device,
                )
                session_offset += max((item.get("end", 0.0) for item in file_segments), default=0.0) + 1.0
            self._safe_ui(self._finish_batch, last_saved, status.backend, done, failed)
        except Exception as error:
            logging.exception("Batch transcription failed")
            self._safe_ui(self._fail_job, error)

    def start_link(self) -> None:
        if self.busy or self.recorder.recording or self.closing:
            return
        if not self._can_start_safely():
            return
        url = self.url_entry.get().strip()
        if not is_supported_url(url):
            messagebox.showwarning(self.t("warning"), self.t("invalid_url"), parent=self)
            return
        config = self.job_config()
        self._start_job(0)
        self.worker_thread = threading.Thread(
            target=self._link_worker,
            args=(url, config),
            daemon=True,
            name="online-video-transcription",
        )
        self.worker_thread.start()

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
                    cancel_event=self.cancel_event,
                )
            )
            self._safe_ui(self._set_progress, 0.25)
            resolved = self.hardware.resolve_model(
                config["model"], config["device"], self.engine.cached_model_ids()
            )
            self._safe_ui(self._set_status, self.t("progress_loading", model=resolved))
            status = self.engine.load_model(
                config["model"], config["device"], self._engine_load_status, self.transcribe_options(config)
            )
            self.last_engine_status = status
            result = self.engine.transcribe_file(
                str(downloaded),
                self.transcribe_options(config),
                progress_callback=lambda value: self._safe_ui(self._set_progress, 0.25 + value * 0.75),
            )
            segments = self._prepare_segments(result.get("segments", []), config["cleanup"])
            if config["speaker"] and segments:
                self._safe_ui(self._set_status, self.t("progress_diarizing"))
                segments = self.diarizer.process(str(downloaded), segments, callback=logging.info, cancel_event=self.cancel_event)
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
        if self.busy or self.recorder.recording or self.closing:
            return
        if not self._can_start_safely():
            return
        self.stop_speaking(resume=False)
        config = self.job_config()
        microphone = self.microphone_combo.get()
        try:
            device_index = int(microphone.split(":", 1)[0]) if ":" in microphone else None
        except ValueError:
            device_index = None
        self.transcript_data = []
        self.recording_offset = 0.0
        prefix = "Conversation" if self.preset == "universal" else ("Conference" if self.preset == "conference" else "Dictation")
        self.active_recording_base = self._new_output_base(prefix)
        self.render_transcript()
        self._start_job(0)
        if not self._model_is_armed(config):
            self._show_recording_initialization()
        self.worker_thread = threading.Thread(
            target=self._recording_worker,
            args=(device_index, config),
            daemon=True,
            name="live-transcription",
        )
        self.worker_thread.start()

    def _recording_worker(self, device_index: int | None, config: dict[str, Any]) -> None:
        segments_all: list[dict[str, Any]] = []
        spool: RecordingSpool | None = None
        completed = False
        try:
            resolved = self.hardware.resolve_model(
                config["model"], config["device"], self.engine.cached_model_ids()
            )
            self._safe_ui(self._set_status, self.t("progress_loading", model=resolved))
            status = self.engine.load_model(
                config["model"], config["device"], self._engine_load_status, self.transcribe_options(config)
            )
            self.last_engine_status = status
            check_cancelled(self.cancel_event)
            spool = RecordingSpool(self.active_recording_base.with_suffix(".wav"))
            self.recording_spool = spool
            options = self.transcribe_options(config)
            self.engine.reset_translation_session(options)
            if config.get("conversation"):
                self.recorder.start(device_index, config["chunk"], smart_splits=True)
            else:
                self.recorder.start(device_index, config["chunk"])
            self._safe_ui(self._recording_started)
            while True:
                try:
                    audio = self.recorder.audio_queue.get(timeout=0.25)
                except queue.Empty:
                    if not self.recorder.recording and not self.recorder.segmenting:
                        break
                    continue
                if audio is None:
                    break
                flattened = np.asarray(audio, dtype=np.float32).reshape(-1)
                self.last_audio = flattened.copy()
                spool.append(flattened)
                result = self.engine.transcribe_audio(flattened, options)
                segments = self._prepare_segments(result.get("segments", []), config["cleanup"])
                shifted = shift_segments(segments, self.recording_offset)
                segments_all.extend(shifted)
                self.recording_offset += flattened.size / SAMPLE_RATE
                if config.get("conversation"):
                    segments_all = self.engine.translator.complete_conversation(segments_all, self.cancel_event)
                    self._safe_ui(self._replace_segments, list(segments_all))
                    self._safe_ui(self.translation_controls.update_pair, result.get("conversation_pair", []))
                else:
                    self._safe_ui(self._append_segments, shifted)
                self._safe_ui(self._pipeline_activity, "waiting")
                # The worker owns this snapshot. It never depends on whether
                # the UI has already consumed its queued segment event.
                write_export(self.active_recording_base.with_suffix(".json"), segments_all)
                write_export(self.active_recording_base.with_suffix(".txt"), segments_all, self.transcript_format_options())
                if self.recorder.capture_error:
                    raise RuntimeError(self.recorder.capture_error)
            spool.close()
            if config["speaker"] and segments_all:
                self._safe_ui(self._set_status, self.t("progress_diarizing"))
                segments_all = self.diarizer.process(str(spool.path), segments_all, callback=logging.info, cancel_event=self.cancel_event)
                self._safe_ui(self._replace_segments, segments_all)
            saved = self.save_result_bundle(
                segments_all,
                "Conversation" if config.get("conversation") else ("Conference" if self.preset == "conference" else "Dictation"),
                base_override=self.active_recording_base,
            )
            completed = True
            self._safe_ui(self._finish_recording, saved, status.backend)
        except Exception as error:
            logging.exception("Live transcription failed")
            self._safe_ui(self._fail_recording, error)
        finally:
            if spool is not None:
                try:
                    if not completed:
                        # Preserve captured backlog after an engine/device failure.
                        self.recorder.stop()
                        while True:
                            try:
                                pending = self.recorder.audio_queue.get_nowait()
                            except queue.Empty:
                                break
                            if pending is not None:
                                spool.append(pending)
                        if self.recorder.overflow_chunk is not None:
                            spool.append(self.recorder.overflow_chunk)
                except (OSError, RuntimeError):
                    logging.exception("Could not flush all pending audio; the existing WAV was preserved")
                finally:
                    spool.close()
                if completed and not config.get("keep_audio", True):
                    spool.path.unlink(missing_ok=True)
            self.recording_spool = None

    def _recording_started(self) -> None:
        self.busy = False
        self._hide_recording_initialization()
        self._set_status(self.t("progress_recording"))
        self.record_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.stop_button.configure(
            state="normal",
            text=self.t("stop_recording"),
            fg_color=RED,
            hover_color="#FF8290",
            border_width=2,
            border_color="#FFD7DC",
        )
        self._set_source_buttons_state("disabled")
        self._pipeline_activity("waiting")

    def toggle_pause(self) -> None:
        self.stop_speaking(resume=False)
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
        self.stop_speaking(resume=False)
        if not self.recorder.recording:
            return
        self.recorder.stop()
        self.busy = True
        self.pause_button.configure(state="disabled")
        self.stop_button.configure(state="disabled", text=self.t("processing"))
        self._set_status(self.t("processing"))

    def _finish_recording(self, saved: Path | None, backend: str) -> None:
        self._hide_recording_initialization()
        self.active_recording_base = None
        self.record_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text=self.t("pause"))
        self.stop_button.configure(
            state="disabled",
            text=self.t("stop"),
            fg_color="#60708A",
            border_width=0,
        )
        self._finish_job(saved, backend)
        self.after(250, self._start_microphone_monitor)

    def _fail_recording(self, error: Exception) -> None:
        self._hide_recording_initialization()
        self._save_backup()
        self.active_recording_base = None
        try:
            self.recorder.stop()
        except Exception:
            pass
        self.record_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.stop_button.configure(
            state="disabled",
            text=self.t("stop"),
            fg_color="#60708A",
            border_width=0,
        )
        self._fail_job(error)
        self.after(250, self._start_microphone_monitor)

    def _prepare_segments(self, segments: list[dict[str, Any]], cleanup: bool) -> list[dict[str, Any]]:
        prepared = []
        for item in segments:
            text = str(item.get("text", "")).strip()
            if cleanup and "source_text" not in item:
                text = self.engine.cleanup_text(text)
            if not text:
                continue
            prepared.append(
                {
                    **item,
                    "start": float(item.get("start", 0.0)),
                    "end": float(item.get("end", 0.0)),
                    "text": text,
                    "words": item.get("words", []),
                    **({"speaker": item["speaker"]} if item.get("speaker") else {}),
                }
            )
        return prepared

    def _append_segments(self, segments: list[dict[str, Any]]) -> None:
        self._commit_editor_changes()
        self.transcript_data.extend(segments)
        self.render_transcript()
        self._save_backup()

    def _replace_segments(self, segments: list[dict[str, Any]]) -> None:
        self.transcript_data = segments
        self.render_transcript()
        self._save_backup()

    def _preview_conversation(self, result: dict[str, Any], offset: float) -> None:
        values = result.get("segments", [])
        if not values:
            return
        preview = dict(values[0], end=values[-1].get("end", 0), source_text=result.get("text", ""),
                       source_language=normalize_language(result.get("language")) or "und", target_language="",
                       translation_pending=True, translation_pending_reason="processing")
        self.transcript_data.append(shift_segments([preview], offset)[0])
        self.render_transcript()
        self._save_backup()

    def transcript_format_options(self) -> TranscriptFormat:
        return TranscriptFormat(
            mode=self.transcript_layout,
            show_timestamps=self.show_timestamps,
            show_duration=self.show_duration,
        )

    def render_transcript(self) -> None:
        if not hasattr(self, "textbox"):
            return
        self.textbox.configure(state="normal", font=("Segoe UI", self.conversation_font_size))
        self.textbox.delete("1.0", "end")
        text = format_transcript(self.transcript_data, self.transcript_format_options())
        self.textbox._speech_lines = {}
        bilingual = any("source_text" in item for item in self.transcript_data)
        if bilingual:
            render_conversation(self.textbox, self.transcript_data, self.transcript_format_options(), self.t,
                                self.show_confidence_var.get())
            self.textbox.configure(state="disabled")
        elif text and self.show_confidence_var.get():
            from src.confidence import confidence_caption
            from src.transcript_format import format_segment
            self.textbox._textbox.tag_configure("confidence", foreground=MUTED, font=("Segoe UI", 10))
            pieces = []
            for item in self.transcript_data:
                line = format_segment(item, self.transcript_format_options())
                pieces.append(line)
                row = int(self.textbox._textbox.index("end-1c").split(".")[0])
                self.textbox._speech_lines[row] = (item["text"], item.get("language") or self.t.language)
                self.textbox.insert("end", line + "\n")
                self.textbox.insert("end", confidence_caption(item, self.t) + "\n", "confidence")
                self.textbox.insert("end", "\n")
            text = "\n\n".join(pieces)
        elif text:
            self.textbox.insert("end", text + "\n")
        self._rendered_text = text
        self.conversation_legend.configure(text=self.t("translation_legend") if bilingual or self.preset == "universal" else "")
        self.textbox.see("end")
        self.textbox.bind("<Button-3>", self._transcript_context_menu)
        self._offer_detected_voice()

    def copy_transcript(self) -> None:
        text = (format_transcript(self.transcript_data, self.transcript_format_options())
                if any("source_text" in item for item in self.transcript_data)
                else self._editor_text())
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status(self.t("copied"))

    def clear_transcript(self) -> None:
        if self.busy or self.recorder.recording:
            return
        self.transcript_data = []
        self.render_transcript()
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
        self._commit_editor_changes()
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
        write_export(path, segments, self.transcript_format_options(),
                     self.textbox.get("1.0", "end-1c").strip() if path.suffix.lower() == ".txt" else None)

    def _new_output_base(self, prefix: str) -> Path:
        self.output_folder = ensure_output_folder(self.output_folder)
        safe_prefix = "".join(
            char if char.isalnum() or char in "-_ " else "_" for char in prefix
        ).strip()
        candidate = self.output_folder / timestamped_name(safe_prefix or "Transcription")
        suffix = 2
        while candidate.with_suffix(".txt").exists() or candidate.with_suffix(".json").exists():
            candidate = candidate.with_name(f"{candidate.name}_{suffix}")
            suffix += 1
        return candidate

    def save_result_bundle(
        self,
        segments: list[dict[str, Any]],
        prefix: str,
        base_override: Path | None = None,
    ) -> Path | None:
        if not segments:
            return None
        base = base_override or self._new_output_base(prefix)
        text_path = base.with_suffix(".txt")
        json_path = base.with_suffix(".json")
        write_bundle(base, segments, self.transcript_format_options())
        status = self.last_engine_status
        try:
            self.history.add(
                SessionRecord.create(
                    title=base.stem,
                    task=self.preset,
                    text_path=text_path,
                    json_path=json_path,
                    model=status.model_id if status else "",
                    device=status.device if status else "",
                    segments=segments,
                )
            )
        except (OSError, sqlite3.Error, ValueError):
            logging.exception("Could not add the completed transcription to history")
        return text_path

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
            self.output_folder = ensure_output_folder(folder)
            self.history.index_existing(self.output_folder)
            self.settings.set("output_folder", str(self.output_folder), save=True)

    def load_history_session(self, record: SessionRecord) -> None:
        if self.busy or self.recorder.recording:
            return
        try:
            self.transcript_data = self.history.load_segments(record)
        except (OSError, ValueError, TypeError) as error:
            messagebox.showerror(
                self.t("error"), self.t("history_load_error", error=error), parent=self
            )
            return
        if record.task in {"files", "conference", "dictation", "link"}:
            self.preset = record.task
            self._refresh_task_styles()
            self._update_source_context()
        self.render_transcript()
        self._set_status(self.t("history_loaded", title=record.title))

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
        self.diarizer.last_warning = ""
        self._commit_editor_changes()
        self.cancel_event.clear()
        self.busy = True
        self.job_started = time.monotonic()
        self.estimated_job_seconds = estimated_seconds
        self._last_progress = 0.0
        self._set_progress(0)
        self._set_source_buttons_state("disabled")
        self._set_status(self.t("processing"))
        self.cancel_button.configure(state="normal")
        self.eta_label.configure(
            text=self.t("remaining", time=format_duration(estimated_seconds))
            if estimated_seconds > 0
            else self.t("calculating")
        )

    def _finish_job(self, saved: Path | None, backend: str) -> None:
        self.busy = False
        self._pipeline_activity("waiting")
        self._set_progress(1.0)
        self._set_source_buttons_state("normal")
        self.cancel_button.configure(state="disabled")
        self._set_status(f"{self.t('progress_done')} • {self.t('backend', backend=backend)}")
        if self.diarizer.last_warning:
            self._set_status(self.t(self.diarizer.last_warning))
        self.eta_label.configure(text=self.t("autosaved") if saved else "")
        self.persist_settings()
        if saved and self.open_result_var.get():
            self.open_file_safe(saved)

    def _finish_batch(self, saved: Path | None, backend: str, done: int, failed: list[str]) -> None:
        self._finish_job(saved, backend)
        if failed:
            self._set_status(self.t("batch_partial", done=done, failed=len(failed)))
            if not self.closing:
                messagebox.showwarning(self.t("warning"), self.t("batch_partial", done=done, failed=len(failed))
                                       + "\n\n" + "\n".join(failed[:20]), parent=self)

    def _fail_job(self, error: Exception) -> None:
        self.busy = False
        self._pipeline_activity("waiting")
        self._set_source_buttons_state("normal")
        self._set_status(self.t("error"))
        self.eta_label.configure(text="")
        self.cancel_button.configure(state="disabled")
        if isinstance(error, JobCancelled):
            self._save_backup()
            self._set_status(self.t("job_cancelled"))
            return
        if not self.closing:
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
        self.translation_controls.set_enabled(state == "normal" and not self.recorder.recording)

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
        if self.running:
            self.ui_tasks.put((callback, args))

    def _drain_ui_tasks(self) -> None:
        if not self.running:
            return
        for _ in range(100):
            try:
                callback, args = self.ui_tasks.get_nowait()
            except queue.Empty:
                break
            try:
                callback(*args)
            except tk.TclError:
                logging.debug("A closed dialog no longer accepts UI updates")
            except Exception:
                logging.exception("Background UI task failed")
        self.after(25, self._drain_ui_tasks)

    def _commit_editor_changes(self) -> None:
        if not hasattr(self, "textbox"):
            return
        if any("source_text" in item for item in self.transcript_data):
            # Visual RTL shaping is presentation only. Never overwrite logical
            # originals/translation metadata with the displayed glyph order.
            return
        edited = self._editor_text()
        self.transcript_data = apply_text_edits(self.transcript_data, self._rendered_text, edited)
        self._rendered_text = edited

    def _editor_text(self):
        widget = self.textbox._textbox
        ranges = widget.tag_ranges("confidence")
        cursor = "1.0"
        pieces = []
        for start, end in zip(ranges[::2], ranges[1::2], strict=True):
            pieces.append(widget.get(cursor, start))
            cursor = end
        pieces.append(widget.get(cursor, "end-1c"))
        return "".join(pieces).strip()

    def _autosave_editor(self) -> None:
        if not self.running:
            return
        self._commit_editor_changes()
        self._save_backup()
        self.after(2000, self._autosave_editor)

    def cancel_job(self) -> None:
        if self.recorder.recording:
            self.stop_recording()
        elif self.busy:
            self.cancel_event.set()
            self.cancel_button.configure(state="disabled")
            self._set_status(self.t("job_cancelling"))

    def edit_vocabulary(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(self.t("vocabulary"))
        dialog.geometry("600x330")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text=self.t("vocabulary_help"), wraplength=530, justify="left").pack(padx=24, pady=18)
        editor = ctk.CTkTextbox(dialog, height=150)
        editor.pack(fill="both", expand=True, padx=24, pady=8)
        editor.insert("1.0", self.settings.get("vocabulary", ""))

        def save():
            self.settings.set("vocabulary", editor.get("1.0", "end-1c").strip()[:2000], save=True)
            dialog.destroy()

        ctk.CTkButton(dialog, text=self.t("save"), command=save).pack(pady=18)

    def _save_backup(self) -> None:
        if not self.transcript_data:
            return
        try:
            self.backup_file.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(self.backup_file, json.dumps(self.transcript_data, ensure_ascii=False))
            if self.active_recording_base is not None:
                atomic_write_text(
                    self.active_recording_base.with_suffix(".txt"),
                    format_transcript(self.transcript_data, self.transcript_format_options()) + "\n",
                )
                atomic_write_text(
                    self.active_recording_base.with_suffix(".json"),
                    json.dumps(self.transcript_data, ensure_ascii=False, indent=2),
                )
        except OSError:
            logging.exception("Could not save recovery data")

    def _load_recovery(self) -> None:
        try:
            data = json.loads(self.backup_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.transcript_data = validate_segments(data)
        except (OSError, ValueError, TypeError):
            return

    def on_close(self) -> None:
        if self.closing:
            return
        self.closing = True
        self.stop_speaking(resume=False)
        if self.recorder.recording:
            self.stop_recording()
        elif self.busy:
            self.cancel_event.set()
        self._commit_editor_changes()
        self.recorder.stop_monitor()
        self._save_backup()
        self._close_when_idle()

    def _close_when_idle(self) -> None:
        if self.worker_thread is not None and self.worker_thread.is_alive():
            self._set_status(self.t("closing_safely"))
            self.after(100, self._close_when_idle)
            return
        # Consume the final worker's completion/segment events before saving.
        self._drain_ui_tasks()
        self._commit_editor_changes()
        self._save_backup()
        self.running = False
        try:
            self.settings.set("window_geometry", self.geometry())
            self.persist_settings()
        except (tk.TclError, ValueError):
            pass
        self.destroy()
