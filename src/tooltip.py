"""Accessible, delayed tooltips shared by simple and advanced controls."""

import tkinter as tk


class ToolTip:
    def __init__(self, widget, text: str, delay_ms: int = 420):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tooltip_window = None
        self.pending = None
        targets = [self.widget, *self.widget.winfo_children()]
        canvas = getattr(self.widget, "_canvas", None)
        if canvas is not None and canvas not in targets:
            targets.append(canvas)
        for target in targets:
            self._safe_bind(target, "<Enter>", self.schedule)
            self._safe_bind(target, "<Leave>", self.hide_tooltip)
            self._safe_bind(target, "<ButtonPress>", self.hide_tooltip)

    @staticmethod
    def _safe_bind(target, sequence: str, callback) -> None:
        try:
            target.bind(sequence, callback, add="+")
        except NotImplementedError:
            tk.Misc.bind(target, sequence, callback, add="+")

    def schedule(self, _event=None) -> None:
        self.cancel()
        if self.text:
            self.pending = self.widget.after(self.delay_ms, self.show_tooltip)

    def cancel(self) -> None:
        if self.pending is not None:
            try:
                self.widget.after_cancel(self.pending)
            except tk.TclError:
                pass
            self.pending = None

    def show_tooltip(self) -> None:
        self.pending = None
        if self.tooltip_window or not self.text or not self.widget.winfo_exists():
            return
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        try:
            self.tooltip_window.attributes("-topmost", True)
        except tk.TclError:
            pass
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify="left",
            background="#16233D",
            foreground="#F5F7FB",
            relief="solid",
            borderwidth=1,
            padx=11,
            pady=8,
            wraplength=340,
            font=("Segoe UI", 10),
        )
        label.pack()
        self.tooltip_window.update_idletasks()
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 7
        width = self.tooltip_window.winfo_reqwidth()
        height = self.tooltip_window.winfo_reqheight()
        x = min(x, max(0, self.widget.winfo_screenwidth() - width - 10))
        if y + height > self.widget.winfo_screenheight():
            y = max(0, self.widget.winfo_rooty() - height - 7)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

    def hide_tooltip(self, _event=None) -> None:
        self.cancel()
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass
            self.tooltip_window = None
