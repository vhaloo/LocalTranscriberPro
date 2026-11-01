"""Quiet startup checks, signed downloads and installation after an idle period."""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path

import customtkinter as ctk
from platformdirs import user_cache_dir

from src import __version__
from src.jobs import JobCancelled
from src.updater import (
    UpdateInfo,
    check_for_update,
    download_update,
    launch_installer,
    validate_installer_file,
)

IDLE_SECONDS = 60


def install_blocked(app, *, automatic=False, now=None):
    """Keep active work, editable dialogs and unpersisted private text open."""
    if app.closing or app.busy or app.recorder.recording or getattr(app, "model_preloading", False):
        return True
    for thread in [getattr(app, "worker_thread", None), getattr(app, "speech_thread", None),
                   *getattr(app, "tool_threads", []), *getattr(app, "preload_threads", [])]:
        if thread is not None and thread.is_alive():
            return True
    if automatic:
        if getattr(app, "private_mode", False):
            editor = getattr(app, "_editor_text", None)
            text = editor() if callable(editor) else getattr(app, "_rendered_text", "")
            if app.transcript_data or text.strip():
                return True
        if getattr(app, "_update_deferred", False):
            return True
        if (time.monotonic() if now is None else now) - app._update_last_activity < IDLE_SECONDS:
            return True
        if any(isinstance(window, ctk.CTkToplevel) and window.winfo_exists() and window.winfo_viewable()
               for window in app.winfo_children()):
            return True
    return False


class UpdateDialog(ctk.CTkToplevel):
    def __init__(self, parent, info: UpdateInfo):
        super().__init__(parent)
        self.parent_app, self.info = parent, info
        parent._ensure_update_state()
        if parent._available_update is None:
            parent._available_update = info
            parent._update_state = "available"
        self.title(parent.t("updates"))
        self.geometry("620x450")
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
        self.progress.set(getattr(parent, "_update_progress", 0))
        self.progress.pack(padx=28, pady=20)
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(pady=10)
        self.install_button = ctk.CTkButton(controls, text=parent.t("update_install"),
                                           fg_color="#2BB98D", command=self.install)
        self.install_button.pack(side="left", padx=8)
        ctk.CTkButton(controls, text=parent.t("update_later"), command=self.close,
                     fg_color="#293244").pack(side="left", padx=8)
        self.refresh()

    def close(self):
        self.parent_app._update_deferred = True
        self.parent_app._update_manual_install_requested = False
        self.destroy()

    def install(self):
        parent = self.parent_app
        if os.name != "nt":
            import webbrowser
            webbrowser.open(self.info.release_url)
            self.close()
        elif getattr(parent, "_update_path", None) and parent._update_state == "ready":
            parent._prepare_update_install(automatic=False)
        else:
            parent._update_manual_install_requested = True
            parent._download_available_update()

    def refresh(self):
        parent = self.parent_app
        self.progress.set(getattr(parent, "_update_progress", 0))
        self.label.configure(text=parent._update_caption())
        self.install_button.configure(state="disabled" if parent._update_state in {"downloading", "installing"} else "normal")


class UpdatesMixin:
    def _ensure_update_state(self):
        if "_update_state" not in self.__dict__:
            self._update_state = "unchecked"
            self._available_update = None
            self._update_progress = 0.0
            self._update_path = None
            self._update_digest = None
            self._update_deferred = False
            self._update_cancel = threading.Event()
            self._update_last_activity = time.monotonic()
            self._update_monitor_started = False
            self._update_manual_install_requested = False

    def start_update_monitor(self):
        self._ensure_update_state()
        if self._update_monitor_started:
            return
        self._update_monitor_started = True
        self.bind_all("<KeyPress>", self._update_activity, add="+")
        self.bind_all("<ButtonPress>", self._update_activity, add="+")
        self.after(5000, self._update_idle_tick)

    def _update_activity(self, _event=None):
        self._update_last_activity = time.monotonic()

    def _update_caption(self):
        self._ensure_update_state()
        if self._update_state == "failed":
            return self.t("update_retry_quiet")
        if self._update_state == "ready":
            return self.t("update_ready_quiet", version=self._available_update.version)
        if self._update_state in {"downloading", "installing", "checking", "offline"}:
            return self.t("update_" + self._update_state + ("_quiet" if self._update_state in {"offline", "installing"} else ""))
        if self._available_update is not None:
            return self.t("update_available", version=self._available_update.version) + "\n" + self.t("tip_update_auto_install")
        return self.t("update_current", version=__version__) if self._update_state == "current" else self.t("tip_update_automatic")

    def _refresh_update_badge(self):
        self._ensure_update_state()
        if not hasattr(self, "updates_button"):
            return
        info = self._available_update
        text = f"↥ {info.version}" if info else self.t("workspace_updates")
        if self._update_state == "downloading":
            text = f"↧ {self._update_progress:.0%}"
        elif self._update_state == "installing":
            text = "↥ …"
        self.updates_button.configure(text=text, width=100 if info else 36,
                                      fg_color="#235F50" if info else "#16233D")
        if hasattr(self, "update_tooltip"):
            self.update_tooltip.text = self._update_caption()
        for window in self.winfo_children():
            if isinstance(window, UpdateDialog) and window.winfo_exists():
                window.refresh()

    def open_update_or_check(self):
        self._ensure_update_state()
        if self._available_update is None:
            self.check_updates()
        elif not any(isinstance(window, UpdateDialog) for window in self.winfo_children()):
            UpdateDialog(self, self._available_update)

    def check_updates(self, silent: bool = False) -> None:
        self._ensure_update_state()
        if self.update_checking or self.closing:
            return
        self.update_checking = True
        if self._available_update is None:
            self._update_state = "checking"
        self._refresh_update_badge()

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
        self._ensure_update_state()
        if result is not None:
            if self._available_update is None or self._available_update.version != result.version:
                self._available_update = result
                self._update_state = "available"
                self._update_path = self._update_digest = None
            if self._automatic_updates_enabled():
                self._download_available_update()
        elif self._available_update is None:
            self._update_state = "offline" if error else "current"
        self._refresh_update_badge()
        if not silent:
            self._set_status(self._update_caption())

    def _automatic_updates_enabled(self):
        return (os.name == "nt" and getattr(sys, "frozen", False)
                and self.settings.get("check_updates", True)
                and self.settings.get("auto_install_updates", True))

    def _update_preferences_changed(self):
        self.persist_settings()
        if not self._automatic_updates_enabled():
            self._update_cancel.set()
        elif self._available_update is not None:
            self._download_available_update()

    def _download_available_update(self):
        self._ensure_update_state()
        if self.closing or self._available_update is None or self._update_state in {"downloading", "installing", "ready"}:
            return
        info = self._available_update
        self._update_cancel = cancel = threading.Event()
        self._update_state = "downloading"
        self._refresh_update_badge()

        def worker():
            try:
                folder = Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "updates"
                checksums = []
                path = download_update(info, folder, lambda value: self._safe_ui(self._update_download_progress, value), cancel,
                                       verified_checksum=checksums.append)
                if len(checksums) != 1:
                    raise ValueError("No publisher-verified checksum was returned")
                if not cancel.is_set():
                    self._safe_ui(self._update_download_ready, path, checksums[0])
                else:
                    self._safe_ui(self._update_download_failed, True)
            except JobCancelled:
                self._safe_ui(self._update_download_failed, True)
            except Exception:
                logging.exception("Verified update download unavailable; application remains open")
                self._safe_ui(self._update_download_failed, False)

        threading.Thread(target=worker, name="signed-update-download", daemon=True).start()

    def _update_download_progress(self, value):
        if not self.closing:
            self._update_progress = value
            self._refresh_update_badge()

    def _update_download_ready(self, path, digest):
        if self.closing or self._update_cancel.is_set():
            self._update_download_failed(True)
            return
        self._update_path, self._update_digest = path, digest
        self._update_state = "ready"
        self._refresh_update_badge()
        if self._update_manual_install_requested:
            self._prepare_update_install(automatic=False)

    def _update_download_failed(self, cancelled=False):
        if not self.closing:
            self._update_state = "available" if cancelled else "failed"
            self._refresh_update_badge()

    def _update_idle_tick(self):
        if self.closing:
            return
        if self._update_state == "ready":
            if self._update_manual_install_requested:
                self._prepare_update_install(automatic=False)
            elif self._automatic_updates_enabled() and not install_blocked(self, automatic=True):
                self._prepare_update_install(automatic=True)
        self.after(5000, self._update_idle_tick)

    def _prepare_update_install(self, *, automatic):
        if self._update_state != "ready" or install_blocked(self, automatic=automatic):
            return
        self._update_state = "installing"
        self._refresh_update_badge()

        def worker():
            try:
                validate_installer_file(self._update_path, self._update_digest)
                self._safe_ui(self._apply_prepared_update, automatic)
            except Exception:
                logging.exception("Update installation preparation failed; application remains open")
                self._safe_ui(self._update_download_failed, False)

        threading.Thread(target=worker, name="update-preflight", daemon=True).start()

    def _apply_prepared_update(self, automatic):
        if self.closing:
            return
        if (install_blocked(self, automatic=automatic)
                or automatic and not self._automatic_updates_enabled()):
            self._update_state = "ready"
            self._refresh_update_badge()
            return
        try:
            self._commit_editor_changes()
            self._save_backup()
            self.persist_settings()
            launch_installer(self._update_path)
        except Exception:
            logging.exception("Update handoff failed; application remains open")
            self._update_download_failed(False)
            return
        self.on_close()

    def stop_update_tasks(self):
        if "_update_cancel" in self.__dict__:
            self._update_cancel.set()
