"""Accessible, delayed tooltips shared by simple and advanced controls."""

import tkinter as tk


class ToolTip:
    active = None

    def __new__(cls, widget, *args, **kwargs):
        existing = getattr(widget, "_ltp_tooltip", None)
        return existing if isinstance(existing, cls) else super().__new__(cls)

    def __init__(self, widget, text: str, delay_ms: int = 350, title: str | None = None):
        if getattr(self, "_initialized", False):
            self.text, self.title = text, title
            return
        self._initialized = True
        self.widget = widget
        widget._ltp_tooltip = self
        self.text = text
        self.title = title
        self.delay_ms = delay_ms
        self.tooltip_window = None
        self.pending = None
        self.cause = None
        targets = [self.widget]
        for target in targets:
            targets.extend(child for child in target.winfo_children() if child not in targets)
        for target in targets:
            self._safe_bind(target, "<Enter>", self.schedule)
            self._safe_bind(target, "<Leave>", self.leave)
            self._safe_bind(target, "<ButtonPress>", self.hide_tooltip)
            self._safe_bind(target, "<FocusIn>", self.schedule)
            self._safe_bind(target, "<FocusOut>", self.hide_tooltip)
            self._safe_bind(target, "<Escape>", self.escape)
            self._safe_bind(target, "<F1>", self.help_key)
        self._safe_bind(self.widget, "<Destroy>", self.hide_tooltip)
        self._safe_bind(self.widget, "<Unmap>", self.hide_tooltip)

    @staticmethod
    def _safe_bind(target, sequence: str, callback) -> None:
        try:
            target.bind(sequence, callback, add="+")
        except NotImplementedError:
            tk.Misc.bind(target, sequence, callback, add="+")

    def _owns(self, target):
        while target is not None:
            owner = getattr(target, "_ltp_tooltip", None)
            if owner is not None:
                return owner is self
            target = getattr(target, "master", None)
        return False

    def schedule(self, event=None) -> None:
        self.cancel()
        self.cause = "focus" if event is not None and str(event.type) == "9" else "pointer"
        try:
            if self.text and self.widget.winfo_exists():
                self.pending = self.widget.after(self.delay_ms, self.show_tooltip)
        except tk.TclError:
            return

    def leave(self, _event=None):
        try:
            target = self.widget.winfo_containing(*self.widget.winfo_pointerxy())
            if not self._owns(target):
                self.hide_tooltip()
        except tk.TclError:
            self.hide_tooltip()

    def escape(self, _event=None):
        visible = self.tooltip_window is not None or self.pending is not None
        self.hide_tooltip()
        return "break" if visible else None

    def help_key(self, event=None):
        self.show_tooltip(event=True)
        return "break"

    def cancel(self) -> None:
        if self.pending is not None:
            try:
                self.widget.after_cancel(self.pending)
            except tk.TclError:
                pass
            self.pending = None

    def show_tooltip(self, event=None) -> None:
        self.pending = None
        try:
            if self.tooltip_window or not self.text or not self.widget.winfo_exists() or not self.widget.winfo_ismapped():
                return
            if event is None and self.cause is not None:
                target = (self.widget.focus_get() if self.cause == "focus" else
                          self.widget.winfo_containing(*self.widget.winfo_pointerxy()))
                if not self._owns(target):
                    return
        except tk.TclError:
            return
        if ToolTip.active is not None and ToolTip.active is not self:
            ToolTip.active.hide_tooltip()
        ToolTip.active = self
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        try:
            self.tooltip_window.attributes("-topmost", True)
        except tk.TclError:
            pass
        title = self.title
        parent = self.widget
        while not title and parent is not None:
            if hasattr(parent, "t"):
                title = parent.t("help_hover_title")
                break
            parent = getattr(parent, "master", None)
        tk.Label(self.tooltip_window, text=title or "ℹ", anchor="w", justify="left",
                 background="#223451", foreground="#7AE9C0", font=("Segoe UI", 11, "bold"),
                 padx=14, pady=7, wraplength=400).pack(fill="x")
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify="left",
            background="#18263D",
            foreground="#F5F7FB",
            relief="solid",
            borderwidth=1,
            padx=14,
            pady=12,
            wraplength=400,
            font=("Segoe UI", 11),
        )
        label.pack()
        self.tooltip_window.update_idletasks()
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 7
        width = self.tooltip_window.winfo_reqwidth()
        height = self.tooltip_window.winfo_reqheight()
        left, top = self.widget.winfo_vrootx(), self.widget.winfo_vrooty()
        right, bottom = left + self.widget.winfo_vrootwidth(), top + self.widget.winfo_vrootheight()
        x = max(left + 8, min(x, right - width - 8))
        if y + height > bottom:
            y = max(top + 8, self.widget.winfo_rooty() - height - 7)
        self.tooltip_window.wm_geometry(f"{x:+d}{y:+d}")

    def hide_tooltip(self, _event=None) -> None:
        self.cancel()
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass
            self.tooltip_window = None
        if ToolTip.active is self:
            ToolTip.active = None
