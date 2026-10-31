"""Literal, bounded transcript search, including logical RTL line fallback."""

from __future__ import annotations

import tkinter as tk
import unicodedata

import customtkinter as ctk


def normalized(value):
    return unicodedata.normalize("NFKC", value).casefold()


class TranscriptSearch:
    def __init__(self, app, textbox, host):
        self.app, self.textbox, self.host = app, textbox, host
        self.widget = textbox._textbox
        self.visible, self.pending = False, None
        self.matches, self.current = [], -1
        self.last_query = ""
        host.grid_columnconfigure(0, weight=1)
        self.query = ctk.CTkEntry(host, placeholder_text=app.t("workspace_search_hint"), height=30)
        self.query.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.count = ctk.CTkLabel(host, text="", width=75, text_color="#9AA8BE")
        self.count.grid(row=0, column=1)
        for column, label, action in (
            (2, "↑", lambda: self.move(-1)),
            (3, "↓", lambda: self.move(1)),
            (4, "×", self.hide),
        ):
            ctk.CTkButton(host, text=label, command=action, width=32, height=28, fg_color="#16233D").grid(
                row=0, column=column, padx=2
            )
        self.query.bind("<KeyRelease>", self.schedule)
        self.query.bind("<Return>", lambda _event: self.move(1))
        self.query.bind("<Shift-Return>", lambda _event: self.move(-1))
        self.query.bind("<Escape>", lambda _event: self.hide())
        self.widget.bind("<KeyRelease>", self.schedule, add="+")
        self.widget.tag_configure("search_match", background="#4B492C")
        self.widget.tag_configure("search_current", background="#775C25")
        host.grid_remove()

    def show(self):
        self.visible = True
        self.host.master.grid()
        self.host.grid()
        self.query.focus_set()
        self.refresh()
        return "break"

    def hide(self):
        self.visible = False
        self.host.grid_remove()
        if not self.app.live_preview_label.cget("text"):
            self.host.master.grid_remove()
        self.widget.tag_remove("search_match", "1.0", "end")
        self.widget.tag_remove("search_current", "1.0", "end")
        self.widget.focus_set()
        return "break"

    def schedule(self, _event=None):
        if not self.visible:
            return
        if _event is not None and _event.keysym in {
            "Return",
            "Escape",
            "Left",
            "Right",
            "Up",
            "Down",
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
        }:
            return
        if self.pending:
            self.app.after_cancel(self.pending)
        self.pending = self.app.after(180, self.refresh)

    def refresh(self):
        if not self.visible:
            return
        if self.pending:
            self.app.after_cancel(self.pending)
            self.pending = None
        old = self.matches[self.current] if self.matches and self.current >= 0 else None
        self.matches, self.current = [], -1
        self.widget.tag_remove("search_match", "1.0", "end")
        self.widget.tag_remove("search_current", "1.0", "end")
        query = self.query.get()
        same_query = query == self.last_query
        self.last_query = query
        if query:
            position = "1.0"
            count = tk.IntVar(master=self.widget)
            while len(self.matches) < 1000:
                found = self.widget.search(
                    query, position, stopindex="end", nocase=True, regexp=False, count=count
                )
                if not found or count.get() <= 0:
                    break
                end = self.widget.index(f"{found}+{count.get()}c")
                self.matches.append((found, end))
                position = end
            # Some Tk builds display shaped Arabic. Search the associated logical
            # Unicode in that case and highlight the matching display line.
            if not self.matches:
                for line, (logical, _language) in sorted(getattr(self.textbox, "_speech_lines", {}).items()):
                    if normalized(query) in normalized(logical):
                        self.matches.append((f"{line}.0", f"{line}.end"))
                        if len(self.matches) >= 1000:
                            break
        for start, end in self.matches:
            self.widget.tag_add("search_match", start, end)
        self.count.configure(text=f"{len(self.matches)}" + ("+" if len(self.matches) == 1000 else ""))
        if self.matches:
            if same_query and old in self.matches:
                self.current = self.matches.index(old) - 1
            self.move(1)

    def move(self, direction):
        if self.matches:
            self.current = (self.current + direction) % len(self.matches)
            self.widget.tag_remove("search_current", "1.0", "end")
            start, end = self.matches[self.current]
            self.widget.tag_add("search_current", start, end)
            self.widget.tag_raise("search_current")
            self.widget.tag_raise("sel")
            self.widget.see(start)
            self.count.configure(
                text=f"{self.current + 1}/{len(self.matches)}" + ("+" if len(self.matches) == 1000 else "")
            )
        return "break"

    def dispose(self):
        if self.pending:
            self.app.after_cancel(self.pending)
            self.pending = None
