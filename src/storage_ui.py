"""Always-accessible storage locations and transparent space requirements."""
from __future__ import annotations

import sys
import threading

import customtkinter as ctk

from src.storage import available_bytes, catalogue_budget, directory_usage, format_bytes, storage_locations
from src.tooltip import ToolTip


class StorageDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.app, self.t = parent, parent.t
        self.title(self.t("storage_title"))
        self.geometry("850x700")
        self.minsize(650, 480)
        self.transient(parent)
        self.configure(fg_color="#08101F")
        self.alive = True
        self.protocol("WM_DELETE_WINDOW", self.close)
        ctk.CTkLabel(self, text=self.t("storage_title"), font=("Segoe UI", 22, "bold")).pack(
            anchor="w", padx=24, pady=(22, 6))
        budget = {key: format_bytes(value, self.t.language) for key, value in catalogue_budget().items()}
        self.budget_label = ctk.CTkLabel(self, text=self.t("storage_budget", **budget), justify="left", wraplength=790,
                    font=("Segoe UI", 14), text_color="#5EE4B7")
        self.budget_label.pack(anchor="w", padx=24, pady=(0, 8))
        self.limit_label = ctk.CTkLabel(self, text=self.t("storage_limit"), justify="left", wraplength=790,
                    text_color="#9AA8BE")
        self.limit_label.pack(anchor="w", padx=24, pady=(0, 10))
        self.bind("<Configure>", self.resize_text, add="+")
        listing = ctk.CTkScrollableFrame(self, fg_color="#111C32")
        listing.pack(fill="both", expand=True, padx=22, pady=(0, 12))
        self.rows = []
        for key, path in storage_locations(parent.output_folder, parent.settings.path, parent.history.database_path):
            row = ctk.CTkFrame(listing, fg_color="#16233D", corner_radius=10)
            row.pack(fill="x", pady=4)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=self.t(key), font=("Segoe UI", 13, "bold")).grid(
                row=0, column=0, sticky="w", padx=12, pady=(7, 0))
            entry = ctk.CTkEntry(row, height=28, border_width=0, fg_color="#16233D")
            entry.insert(0, str(path))
            entry.configure(state="readonly")
            entry.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
            ToolTip(entry, self.t("storage_path_tip"))
            measure = ctk.CTkLabel(row, text=self.t("storage_scanning"), text_color="#9AA8BE")
            measure.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 6))
            button = ctk.CTkButton(row, text=self.t("storage_open"), width=82, height=29,
                                  command=lambda p=path: parent.open_file_safe(p if p.is_dir() else p.parent))
            button.grid(row=0, column=1, rowspan=2, padx=10)
            ToolTip(button, self.t("storage_open_tip"))
            self.rows.append((path, measure, key))
        ctk.CTkButton(self, text=self.t("storage_copy"), command=self.copy_locations).pack(pady=(0, 18))
        threading.Thread(target=self.scan, name="storage-inspection", daemon=True).start()

    def resize_text(self, event):
        if event.widget is self:
            for label in (self.budget_label, self.limit_label):
                label.configure(wraplength=max(300, event.width - 55))

    def scan(self):
        for path, label, key in self.rows:
            if not self.alive or self.app.closing:
                return
            exclude = (".git", ".venv", "build", "dist", "artifacts", "__pycache__") if (
                key == "storage_application" and not getattr(sys, "frozen", False)) else ()
            usage = directory_usage(path, exclude=exclude)
            text = self.t("storage_usage", size=format_bytes(usage.bytes, self.t.language),
                          free=format_bytes(available_bytes(path), self.t.language))
            if usage.partial:
                text += " · " + self.t("storage_partial")
            self.app._safe_ui(self.set_measure, label, text)

    def set_measure(self, label, text):
        if self.alive and self.winfo_exists():
            label.configure(text=text)

    def copy_locations(self):
        text = "\n".join(self.t(key) + ": " + str(path) for path, _, key in self.rows)
        self.clipboard_clear()
        self.clipboard_append(text)

    def close(self):
        self.alive = False
        self.destroy()
