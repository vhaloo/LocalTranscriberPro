"""Language-bound logical lines and selection-friendly click-to-speak bindings."""
from __future__ import annotations

import sys
from tkinter import TclError

SELECTION_MODIFIERS = 0x20005 if sys.platform == "win32" else 0x000D

def speech_language(segment, fallback="und"):
    return segment.get("target_language") or segment.get("source_language") or segment.get("language") or fallback


def insert_speech_line(textbox, visible, logical, language, tags=()):
    """Map every logical row, including wrapped/multiline RTL utterances."""
    widget = textbox._textbox
    first = int(widget.index("end-1c").split(".")[0])
    textbox.insert("end", visible + "\n", tags)
    if logical.strip() and language:
        item = (logical, language)
        for row in range(first, first + visible.count("\n") + 1):
            textbox._speech_lines[row] = item


def selected_lines(mapping, first, last):
    # Multiline rows share the exact tuple; distinct, identical turns still read twice.
    return [item for row, item in mapping.items() if first <= row <= last
            and (row == first or item is not mapping.get(row - 1))]


class ClickSpeechBinding:
    """Read a stable clicked utterance without intercepting normal Text selection."""

    def __init__(self, textbox, enabled, speak):
        self.textbox, self.widget = textbox, textbox._textbox
        self.enabled, self.speak = enabled, speak
        self.press = None
        self.pending = None
        self.widget.tag_configure("speech_click", background="#24483F")
        for event, callback in (("<ButtonPress-1>", self._press), ("<ButtonRelease-1>", self._release),
                                ("<B1-Motion>", self._motion), ("<Double-Button-1>", self._cancel),
                                ("<Triple-Button-1>", self._cancel), ("<MouseWheel>", self._cancel),
                                ("<Button-4>", self._cancel), ("<Button-5>", self._cancel),
                                ("<Destroy>", self._cancel)):
            self.widget.bind(event, callback, add="+")

    def _cancel(self, _event=None):
        self.press = None
        if self.pending is not None:
            self.widget.after_cancel(self.pending)
            self.pending = None

    def _item_at(self, event):
        index = self.widget.index(f"@{event.x},{event.y}")
        bounds = self.widget.dlineinfo(index)
        # Text.index clamps clicks below the last line to its last character.
        if not bounds or not bounds[1] <= event.y < bounds[1] + bounds[3]:
            return None
        row = int(index.split(".")[0])
        item = self.textbox._speech_lines.get(row)
        return (row, item) if item else None

    def _press(self, event):
        self._cancel()
        # Modified clicks extend selection. Never turn those into speech.
        # Windows reports Num Lock as bit 0x8; on X11 that bit means Alt.
        if self.enabled() and not event.state & SELECTION_MODIFIERS:
            self.press = (event.x, event.y, self._item_at(event))

    def _motion(self, event):
        if self.press and (abs(event.x - self.press[0]) > 4 or abs(event.y - self.press[1]) > 4):
            self._cancel()

    def _release(self, event):
        press, self.press = self.press, None
        if not press or not press[2] or not self.enabled():
            return
        if abs(event.x - press[0]) > 4 or abs(event.y - press[1]) > 4:
            return
        selected = self.widget.tag_ranges("sel")
        if selected or self._item_at(event) != press[2]:
            return
        row, item = press[2]

        def read():
            self.pending = None
            if self.enabled() and self.widget.winfo_exists():
                self.widget.tag_remove("speech_click", "1.0", "end")
                # Highlight only if that row still contains the clicked utterance.
                if self.textbox._speech_lines.get(row) == item:
                    self.widget.tag_add("speech_click", f"{row}.0", f"{row}.end")
                self.speak(item)
        # Leave time for the platform's double/triple click word/paragraph selection.
        try:
            self.pending = self.widget.after(500, read)
        except TclError:
            pass
