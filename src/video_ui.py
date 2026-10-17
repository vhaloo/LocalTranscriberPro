"""Explicit authentication choices, engine repair and useful video diagnostics."""
from __future__ import annotations

import json
import platform
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from yt_dlp.version import __version__ as bundled_version

from src.jobs import JobCancelled
from src.tooltip import ToolTip
from src.video_engine import engine_directory, find_engine_update, install_engine, prepared_engine
from src.youtube_utils import VideoDownloadError, bundled_ffmpeg, javascript_runtimes, validate_cookie_file


class VideoOptionsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.app, self.t = parent, parent.t
        self.cancel = threading.Event()
        self.updating = False
        self.title(self.t("video_options"))
        self.geometry("800x760")
        self.minsize(720, 480)
        self.transient(parent)
        self.configure(fg_color="#08101F")
        self.protocol("WM_DELETE_WINDOW", self.close)
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(body, text=self.t("video_options"), font=("Segoe UI", 23, "bold")).pack(
            anchor="w", padx=25, pady=(22, 12))
        self.help_label = ctk.CTkLabel(body, text=self.t("video_help"), wraplength=700, justify="left",
                    font=("Segoe UI", 14))
        self.help_label.pack(anchor="w", padx=25, pady=(0, 14))
        self.cookies_help = ctk.CTkLabel(body, text=self.t("video_cookies_help"), wraplength=700, justify="left",
                    text_color="#9AA8BE")
        self.cookies_help.pack(anchor="w", padx=25)
        auth = ctk.CTkFrame(body, fg_color="transparent")
        auth.pack(fill="x", padx=25, pady=10)
        choose = ctk.CTkButton(auth, text=self.t("video_choose_cookies"), command=self.choose_cookies)
        choose.pack(side="left", padx=(0, 8))
        ToolTip(choose, self.t("video_cookies_tip"))
        clear = ctk.CTkButton(auth, text=self.t("video_clear_cookies"), command=self.clear_cookies, fg_color="#293244")
        clear.pack(side="left")
        ToolTip(clear, self.t("video_clear_tip"))
        self.cookie_label = ctk.CTkLabel(body, text="", wraplength=700, justify="left", text_color="#9AA8BE")
        self.cookie_label.pack(anchor="w", padx=25)
        limit = ctk.CTkFrame(body, fg_color="transparent")
        limit.pack(fill="x", padx=25, pady=12)
        ctk.CTkLabel(limit, text=self.t("video_limit")).pack(side="left", padx=(0, 12))
        unit = "Mo" if self.t.language == "fr" else "MB"
        self.limits = {f"{value} {unit}": value for value in (512, 1000, 2000, 4000)}
        picker = ctk.CTkOptionMenu(limit, values=list(self.limits), command=self.set_limit)
        current = parent.settings.get("video_max_mb", 2000)
        picker.set(next((label for label, value in self.limits.items() if value == current), f"2000 {unit}"))
        picker.pack(side="left")
        ToolTip(picker, self.t("video_limit_tip"))
        self.engine_label = ctk.CTkLabel(body, text=self.engine_text(), wraplength=700, justify="left")
        self.engine_label.pack(anchor="w", padx=25, pady=(7, 10))
        self.update_button = ctk.CTkButton(body, text=self.t("video_engine_update"), command=self.update_engine,
                                          height=38, fg_color="#2BB98D", text_color="#08101F")
        self.update_button.pack(anchor="w", padx=25)
        ToolTip(self.update_button, self.t("video_engine_tip"))
        self.progress = ctk.CTkProgressBar(body, progress_color="#5EE4B7")
        self.progress.set(0)
        self.progress.pack(fill="x", padx=25, pady=12)
        self.status = ctk.CTkLabel(body, text="", wraplength=700, justify="left", text_color="#9AA8BE")
        self.status.pack(anchor="w", padx=25)
        ctk.CTkButton(body, text=self.t("video_diagnostics"), command=self.copy_diagnostics,
                      fg_color="#293244").pack(anchor="w", padx=25, pady=10)
        body.bind("<Configure>", self.resize_text, add="+")
        self.refresh_cookie()

    def resize_text(self, event):
        for label in (self.help_label, self.cookies_help, self.cookie_label, self.engine_label, self.status):
            label.configure(wraplength=max(300, event.width - 60))

    def engine_text(self):
        ready = prepared_engine()
        return self.t("video_engine_version", bundled=bundled_version,
                      active=ready[1] if ready else self.t("video_engine_bundled"))

    def refresh_cookie(self):
        path = getattr(self.app, "video_cookies_file", "")
        self.cookie_label.configure(text=str(path) if path else self.t("video_no_cookies"))

    def choose_cookies(self):
        path = filedialog.askopenfilename(parent=self, title=self.t("video_choose_cookies"),
                                          filetypes=[("Netscape cookies", "*.txt"), ("All", "*")])
        if not path:
            return
        try:
            self.app.video_cookies_file = str(validate_cookie_file(path))
        except (VideoDownloadError, OSError):
            messagebox.showerror(self.t("error"), self.t("video_error_cookies"), parent=self)
        self.refresh_cookie()

    def clear_cookies(self):
        self.app.video_cookies_file = ""
        self.refresh_cookie()

    def set_limit(self, label):
        self.app.settings.set("video_max_mb", self.limits[label], save=True)

    def update_engine(self):
        if self.updating or self.app.busy:
            return
        self.updating = True
        self.update_button.configure(state="disabled")
        self.status.configure(text=self.t("video_engine_checking"))

        def worker():
            try:
                update = find_engine_update()
                install_engine(update, progress=lambda value: self.app._safe_ui(self.update_progress, value),
                               cancel_event=self.cancel)
                self.app._safe_ui(self.updated, "")
            except JobCancelled:
                return
            except Exception:
                self.app._safe_ui(self.updated, self.t("video_engine_failed"))

        threading.Thread(target=worker, name="video-engine-update", daemon=True).start()

    def update_progress(self, value):
        if not self.cancel.is_set() and self.winfo_exists():
            self.progress.set(value)

    def updated(self, error):
        if self.cancel.is_set() or not self.winfo_exists():
            return
        self.updating = False
        self.update_button.configure(state="normal")
        self.engine_label.configure(text=self.engine_text())
        self.status.configure(text=error or self.t("video_engine_ready"))

    def copy_diagnostics(self):
        ready = prepared_engine()
        try:
            ffmpeg_present = bool(bundled_ffmpeg())
        except (OSError, RuntimeError):
            ffmpeg_present = False
        report = {"application": "Local Transcriber Pro", "system": platform.system(),
                  "bundled_yt_dlp": bundled_version, "verified_engine": ready[1] if ready else None,
                  "javascript": list(javascript_runtimes()), "ffmpeg_present": ffmpeg_present,
                  "engine_folder": str(engine_directory()), "cookies_selected": bool(getattr(self.app, "video_cookies_file", ""))}
        self.clipboard_clear()
        self.clipboard_append(json.dumps(report, indent=2))
        self.status.configure(text=self.t("video_diagnostics_copied"))

    def close(self):
        self.cancel.set()
        self.destroy()
