"""Searchable language selection, contextual help and bilingual text display."""
from __future__ import annotations

import unicodedata

import customtkinter as ctk

from src.confidence import confidence_caption
from src.translation_languages import language_choices, language_label
from src.utils import format_timestamp

BACKGROUND, PANEL, MUTED = "#08101F", "#16233D", "#9AA8BE"
SOURCE, TRANSLATED, THIRD = "#F5F7FB", "#5EE4B7", "#65A8FF"


def search_key(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(char))


class LanguagePickerDialog(ctk.CTkToplevel):
    def __init__(self, parent, current, callback, optional=None, speech_only=False):
        super().__init__(parent)
        self.t, self.callback = parent.t, callback
        self.title(self.t("translation_choose_language"))
        self.geometry("620x650")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=BACKGROUND)
        self.values = language_choices(self.t.language, speech_only)
        if optional:
            self.values.insert(0, optional)
        self.current = current
        self.search = ctk.CTkEntry(self, placeholder_text=self.t("translation_search"), height=42)
        self.search.pack(fill="x", padx=22, pady=(22, 8))
        self.search.bind("<KeyRelease>", lambda _event: self.refresh())
        self.count = ctk.CTkLabel(self, text="", text_color=MUTED)
        self.count.pack(anchor="w", padx=24)
        self.results = ctk.CTkScrollableFrame(self, fg_color=PANEL)
        self.results.pack(fill="both", expand=True, padx=22, pady=(8, 22))
        self.refresh()
        self.after(100, self.search.focus_set)

    def refresh(self):
        for widget in self.results.winfo_children():
            widget.destroy()
        needle = search_key(self.search.get())
        matches = [(code, label) for code, label in self.values if needle in search_key(label)]
        self.count.configure(text=self.t("translation_matches", count=len(matches)))
        for code, label in matches[:80]:
            ctk.CTkButton(self.results, text=("✓ " if code == self.current else "") + label,
                          anchor="w", height=36, fg_color="#14372F" if code == self.current else "transparent",
                          hover_color="#28405C", command=lambda value=code: self.choose(value)).pack(fill="x", pady=2)

    def choose(self, code):
        self.destroy()
        self.callback(code)


class TranslationHelpDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title(parent.t("translation_help_title"))
        self.geometry("760x650")
        self.transient(parent)
        self.configure(fg_color=BACKGROUND)
        text = ctk.CTkTextbox(self, wrap="word", font=("Segoe UI", 16), fg_color=PANEL)
        text.pack(fill="both", expand=True, padx=24, pady=24)
        text.insert("1.0", parent.t("translation_help_body"))
        text.configure(state="disabled")


class TranslationControls(ctk.CTkFrame):
    def __init__(self, app, master):
        super().__init__(master, fg_color="#0B1724", corner_radius=16)
        self.app, self.t = app, app.t
        self.buttons = {}
        for column in range(3):
            self.grid_columnconfigure(column, weight=1)
        self.pair_label = ctk.CTkLabel(self, text=self.t("translation_pair_wait"), text_color=TRANSLATED,
                                     font=("Segoe UI", 13, "bold"))
        self.pair_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 3))
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=2, sticky="e", padx=10)
        ctk.CTkButton(top, text=self.t("translation_how"), width=100, height=26, fg_color=PANEL,
                      command=lambda: TranslationHelpDialog(app)).pack(side="right", padx=3)
        self.model_button = ctk.CTkButton(top, text=self.t("translation_speech_model"), width=130, height=26,
                                        fg_color=PANEL, command=app.open_model_selector)
        self.model_button.pack(side="right", padx=3)
        for column, (field, title) in enumerate((
            ("translation_target", "translation_target"), ("conversation_partner", "translation_partner"),
            ("translation_third", "translation_third"),
        )):
            ctk.CTkLabel(self, text=self.t(title), text_color=MUTED, font=("Segoe UI", 11)).grid(
                row=1, column=column, sticky="w", padx=14)
            button = ctk.CTkButton(self, text="", fg_color=PANEL, height=32,
                                  command=lambda value=field: self.choose(value))
            button.grid(row=2, column=column, sticky="ew", padx=12, pady=(2, 5))
            self.buttons[field] = button
        self.guide = ctk.CTkLabel(self, text=self.t("translation_inline"), text_color=MUTED,
                                  font=("Segoe UI", 11), justify="left", wraplength=1000)
        self.guide.grid(row=3, column=0, columnspan=3, sticky="w", padx=14, pady=(2, 9))
        self.refresh()

    def refresh(self):
        for field, button in self.buttons.items():
            code = getattr(self.app, field)
            label = self.t("translation_auto_partner" if code == "auto" else "translation_no_third") if code in {"auto", "none"} else language_label(code, self.t.language)
            button.configure(text=label + " ▾")
        self.set_enabled(not self.app.busy)

    def set_enabled(self, enabled):
        for field, button in self.buttons.items():
            button.configure(state="normal" if enabled and (field == "translation_target" or self.app.preset == "universal") else "disabled")
        self.model_button.configure(state="normal" if enabled else "disabled")

    def choose(self, field):
        optional = ("auto", self.t("translation_auto_partner")) if field == "conversation_partner" else (
            ("none", self.t("translation_no_third")) if field == "translation_third" else None)
        LanguagePickerDialog(self.app, getattr(self.app, field), lambda code: self.app.translation_changed(field, code),
                             optional, speech_only=False)

    def update_pair(self, pair):
        self.pair_label.configure(text=(" ↔ ".join(language_label(code, self.t.language) for code in pair)
                                       if len(pair) == 2 else self.t("translation_pair_wait")))


def display_line(value: str) -> tuple[str, bool]:
    rtl = any("\u0590" <= char <= "\u08ff" for char in value)
    if rtl:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(value), base_dir="R"), True
    return value, False


def render_conversation(textbox, segments, options, translator=None, show_confidence=False):
    widget = textbox._textbox
    widget.tag_configure("confidence", foreground=MUTED, font=("Segoe UI", 10), spacing3=7)
    for tag, color in (("original", SOURCE), ("translated", TRANSLATED), ("third", THIRD)):
        widget.tag_configure(tag, foreground=color, spacing1=3, spacing3=3)
        widget.tag_configure(tag + "_rtl", foreground=color, justify="right", spacing1=3, spacing3=3)
    for item in segments:
        if "source_text" not in item:
            textbox.insert("end", str(item.get("text", "")) + "\n\n", "original")
            continue
        prefix = f"[{format_timestamp(float(item.get('start', 0)), '.')[:8]}] " if options.show_timestamps else ""
        if item.get("separated_source") and translator:
            prefix += "[" + translator("overlap_channel", value=item["separated_source"]) + "] "
        lines = [("original", f"{prefix}[{item.get('source_language', 'und')}] {item['source_text']}")]
        if item.get("target_language") and not item.get("translation_pending"):
            lines.append(("translated", f"[{item['target_language']}] {item.get('text', '')}"))
        elif item.get("translation_pending") and translator:
            lines.append(("translated", translator("translation_processing" if item.get("translation_pending_reason") == "processing"
                                                     else "translation_pending")))
        if item.get("third_text") and item.get("third_language") not in {item.get("source_language"), item.get("target_language")}:
            lines.append(("third", f"[{item['third_language']}] {item['third_text']}"))
        for tag, line in lines:
            if tag in {"original", "translated", "third"}:
                language = item.get({"original": "source_language", "translated": "target_language", "third": "third_language"}[tag])
                logical = item.get({"original": "source_text", "translated": "text", "third": "third_text"}[tag], "")
                if language and not (tag == "translated" and item.get("translation_pending")):
                    row = int(widget.index("end-1c").split(".")[0])
                    textbox._speech_lines[row] = (logical, language)
            visible, rtl = display_line(line)
            textbox.insert("end", visible + "\n", tag + ("_rtl" if rtl else ""))
        if show_confidence and translator:
            textbox.insert("end", confidence_caption(item, translator) + "\n", "confidence")
        textbox.insert("end", "\n")
