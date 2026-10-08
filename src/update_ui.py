"""Nonblocking update flow, with user acceptance and recoverable downloads."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from platformdirs import user_cache_dir

from src import __version__
from src.jobs import JobCancelled
from src.updater import UpdateInfo, check_for_update, download_update, launch_installer


class UpdateDialog(ctk.CTkToplevel):
    def __init__(self, parent, info: UpdateInfo):
        super().__init__(parent)
        self.parent_app, self.info = parent, info
        self.cancel_event = threading.Event()
        self.downloading = False
        self.title(parent.t("updates"))
        self.geometry("600x360")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color="#111C32")
        self.protocol("WM_DELETE_WINDOW", self.close)
        ctk.CTkLabel(self, text=parent.t("update_available", version=info.version),
                    font=("Segoe UI", 22, "bold")).pack(padx=28, pady=(30, 14))
        self.label = ctk.CTkLabel(self, text=parent.t("update_explanation"), wraplength=530,
                                 justify="left", font=("Segoe UI", 14))
        self.label.pack(padx=28, pady=8)
        self.progress = ctk.CTkProgressBar(self, width=530, progress_color="#5EE4B7")
        self.progress.set(0)
        self.progress.pack(padx=28, pady=20)
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(pady=10)
        self.install_button = ctk.CTkButton(controls, text=parent.t("update_install"),
                                           fg_color="#2BB98D", command=self.install)
        self.install_button.pack(side="left", padx=8)
        ctk.CTkButton(controls, text=parent.t("update_later"), command=self.close,
                     fg_color="#293244").pack(side="left", padx=8)

    def close(self):
        self.cancel_event.set()
        self.destroy()

    def install(self):
        parent = self.parent_app
        if parent.busy or parent.recorder.recording or parent.closing or self.downloading:
            return
        if os.name != "nt":
            import webbrowser

            webbrowser.open(self.info.release_url)
            self.close()
            return
        self.downloading = True
        self.install_button.configure(state="disabled")
        self.label.configure(text=parent.t("update_downloading"))

        def worker():
            try:
                folder = Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "updates"
                path = download_update(self.info, folder,
                                       lambda value: parent._safe_ui(self.set_progress, value), self.cancel_event)
                parent._safe_ui(self.ready, path)
            except JobCancelled:
                return
            except Exception as error:
                logging.exception("Verified update download failed")
                parent._safe_ui(self.failed, str(error))

        threading.Thread(target=worker, name="update-download", daemon=True).start()

    def set_progress(self, value):
        if self.winfo_exists():
            self.progress.set(value)

    def failed(self, error):
        if self.winfo_exists():
            self.downloading = False
            self.label.configure(text=self.parent_app.t("update_failed", error=error))
            self.install_button.configure(state="normal")

    def ready(self, path):
        if not self.winfo_exists() or self.cancel_event.is_set():
            return
        parent = self.parent_app
        if parent.busy or parent.recorder.recording:
            self.downloading = False
            self.label.configure(text=parent.t("update_wait_idle"))
            self.install_button.configure(state="normal")
            return
        try:
            parent._commit_editor_changes()
            parent._save_backup()
            parent.persist_settings()
            launch_installer(path)
        except Exception as error:
            self.failed(str(error))
            return
        self.destroy()
        parent.on_close()


class UpdatesMixin:
    def check_updates(self, silent: bool = False) -> None:
        if self.update_checking or self.closing:
            return
        self.update_checking = True
        if not silent:
            self._set_status(self.t("update_checking"))

        def worker():
            try:
                result = check_for_update(__version__)
                self._safe_ui(self._update_checked, result, silent, "")
            except Exception as error:
                logging.info("Update check unavailable: %s", error)
                self._safe_ui(self._update_checked, None, silent, str(error))

        threading.Thread(target=worker, name="release-check", daemon=True).start()

    def _update_checked(self, result: UpdateInfo | None, silent: bool, error: str) -> None:
        self.update_checking = False
        if self.closing:
            return
        if error:
            if not silent:
                messagebox.showinfo(self.t("updates"), self.t("update_failed", error=error), parent=self)
            return
        if result is not None:
            if self.busy or self.recorder.recording:
                self.after(5000, lambda: self._update_checked(result, silent, ""))
            elif not any(isinstance(window, UpdateDialog) for window in self.winfo_children()):
                UpdateDialog(self, result)
        elif not silent:
            messagebox.showinfo(self.t("updates"), self.t("update_current", version=__version__), parent=self)
