"""Immediate, responsive startup screen and duplicate-launch protection."""

from __future__ import annotations

import ctypes
import locale
import os
import queue
import sys
import tempfile
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

_ALREADY_EXISTS = 183

STARTUP_TEXT = {
    "en": {
        "title": "Local Transcriber Pro",
        "version": "VERSION 2.2  •  PRIVATE AND LOCAL",
        "starting": "Opening the application…",
        "libraries": "Loading the private audio engine…",
        "hardware_memory": "Checking memory and available storage…",
        "hardware_gpu": "Detecting the graphics card and its memory…",
        "hardware_engine": "Verifying the safe CPU engine…",
        "hardware_acceleration": "Testing GPU acceleration without starting a model…",
        "hardware_ready": "Choosing the safest maximum-quality model…",
        "preloading_model": "Loading that model now so Record will be ready immediately…",
        "interface": "Preparing the simple and advanced interfaces…",
        "ready": "Everything is ready.",
        "patience": "The first launch can take up to a minute. The application is working.",
        "already_running": "Local Transcriber Pro is already open. Its existing window is ready to use.",
        "startup_error": "The application could not finish starting.",
    },
    "fr": {
        "title": "Local Transcriber Pro",
        "version": "VERSION 2.2  •  PRIVÉE ET LOCALE",
        "starting": "Ouverture de l’application…",
        "libraries": "Chargement du moteur audio privé…",
        "hardware_memory": "Vérification de la mémoire et de l’espace disponible…",
        "hardware_gpu": "Détection de la carte graphique et de sa mémoire…",
        "hardware_engine": "Vérification du moteur CPU sécurisé…",
        "hardware_acceleration": "Test de l’accélération GPU sans lancer de modèle…",
        "hardware_ready": "Choix du meilleur modèle pouvant fonctionner sans risque…",
        "preloading_model": "Chargement du modèle maintenant pour que le bouton Enregistrer soit immédiatement prêt…",
        "interface": "Préparation des interfaces simple et avancée…",
        "ready": "Tout est prêt.",
        "patience": "Le premier démarrage peut prendre jusqu’à une minute. L’application travaille.",
        "already_running": "Local Transcriber Pro est déjà ouvert. Sa fenêtre actuelle est prête à utiliser.",
        "startup_error": "L’application n’a pas pu terminer son démarrage.",
    },
}


def startup_language() -> str:
    candidates = [os.environ.get("LANG", ""), os.environ.get("LC_ALL", "")]
    try:
        candidates.append(locale.getlocale()[0] or "")
    except (ValueError, TypeError):
        pass
    return "fr" if any(value.lower().startswith("fr") for value in candidates) else "en"


class SingleInstanceLock:
    """Keep accidental repeated double-clicks from opening multiple AI runtimes."""

    def __init__(self) -> None:
        self._handle: int | None = None
        self._file: Any = None

    def acquire(self) -> bool:
        if sys.platform == "win32":
            kernel32 = ctypes.windll.kernel32
            kernel32.SetLastError(0)
            handle = kernel32.CreateMutexW(None, False, "LocalTranscriberPro-Desktop-v2")
            if not handle:
                return False
            self._handle = handle
            if kernel32.GetLastError() == _ALREADY_EXISTS:
                kernel32.CloseHandle(handle)
                self._handle = None
                return False
            return True

        try:
            import fcntl

            path = Path(tempfile.gettempdir()) / "local-transcriber-pro.lock"
            self._file = path.open("a+", encoding="utf-8")
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (ImportError, OSError):
            if self._file:
                self._file.close()
                self._file = None
            return False

    def release(self) -> None:
        if self._handle is not None:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None
        if self._file is not None:
            try:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass
            self._file.close()
            self._file = None


def notify_already_running() -> None:
    language = startup_language()
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(STARTUP_TEXT[language]["title"], STARTUP_TEXT[language]["already_running"])
    root.destroy()


class StartupSplash:
    """A tiny standard-library UI that appears before heavy AI imports."""

    def __init__(self, language: str | None = None) -> None:
        self.language = language or startup_language()
        self.text = STARTUP_TEXT[self.language]
        self._messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._result: Any = None
        self._error: BaseException | None = None

        self.root = tk.Tk()
        self.root.title(f"{self.text['title']} — {self.text['starting']}")
        self.root.overrideredirect(True)
        self.root.configure(bg="#07101F")
        self.root.attributes("-topmost", True)
        width, height = 670, 390
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg="#07101F",
            highlightthickness=1,
            highlightbackground="#294261",
        )
        canvas.place(x=0, y=0)
        canvas.create_oval(510, -90, 760, 160, fill="#173C43", outline="")
        canvas.create_oval(-130, 265, 145, 535, fill="#152A4D", outline="")
        canvas.create_text(
            54,
            68,
            anchor="w",
            text=self.text["title"],
            fill="#F6F9FD",
            font=("Segoe UI", 28, "bold"),
        )
        canvas.create_text(
            56,
            108,
            anchor="w",
            text=self.text["version"],
            fill="#60E4B8",
            font=("Segoe UI", 10, "bold"),
        )
        canvas.create_rectangle(55, 149, 615, 150, fill="#294261", outline="")

        self.status = tk.Label(
            self.root,
            text=self.text["starting"],
            bg="#07101F",
            fg="#F6F9FD",
            anchor="w",
            font=("Segoe UI", 15, "bold"),
        )
        self.status.place(x=55, y=181, width=560, height=32)
        self.detail = tk.Label(
            self.root,
            text=self.text["patience"],
            bg="#07101F",
            fg="#9DACC1",
            anchor="w",
            justify="left",
            font=("Segoe UI", 11),
        )
        self.detail.place(x=55, y=220, width=560, height=48)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "LTP.Horizontal.TProgressbar",
            troughcolor="#1B2A42",
            background="#60E4B8",
            lightcolor="#60E4B8",
            darkcolor="#60E4B8",
            bordercolor="#1B2A42",
        )
        self.progress = ttk.Progressbar(
            self.root,
            style="LTP.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
            value=8,
        )
        self.progress.place(x=55, y=291, width=560, height=10)
        self.percent = tk.Label(
            self.root,
            text="8%",
            bg="#07101F",
            fg="#60E4B8",
            anchor="e",
            font=("Segoe UI", 10, "bold"),
        )
        self.percent.place(x=550, y=314, width=65, height=22)
        self.root.update_idletasks()
        self.root.update()

    def report(self, stage: str, progress: float) -> None:
        self._messages.put(("progress", (stage, progress)))

    def _apply_progress(self, stage: str, progress: float) -> None:
        self.status.configure(text=self.text.get(stage, self.text["starting"]))
        value = max(1, min(100, round(progress * 100)))
        self.progress.configure(value=value)
        self.percent.configure(text=f"{value}%")

    def run(self, worker: Callable[[Callable[[str, float], None]], Any]) -> Any:
        def execute() -> None:
            try:
                result = worker(self.report)
                self._messages.put(("done", result))
            except BaseException as exc:  # Propagate startup faults to the main thread.
                self._messages.put(("error", exc))

        threading.Thread(target=execute, name="startup-preflight", daemon=True).start()
        self.root.after(40, self._poll)
        self.root.mainloop()
        if self._error:
            raise self._error
        return self._result

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._messages.get_nowait()
                if kind == "progress":
                    self._apply_progress(*payload)
                elif kind == "done":
                    self._result = payload
                    self._apply_progress("ready", 1.0)
                    self.root.after(180, self.root.destroy)
                    return
                else:
                    self._error = payload
                    self.root.destroy()
                    return
        except queue.Empty:
            self.root.after(40, self._poll)


def notify_startup_error(error: BaseException) -> None:
    language = startup_language()
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        STARTUP_TEXT[language]["title"],
        f"{STARTUP_TEXT[language]['startup_error']}\n\n{type(error).__name__}: {error}",
    )
    root.destroy()
