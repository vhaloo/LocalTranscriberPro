"""Cancel Tk callbacks owned by a subtree before destroying its widgets."""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk


class ManagedToplevel(ctk.CTkToplevel):
    """Dialog cleanup also covers button animations queued before a close."""

    def destroy(self):
        cancel_widget_timers(self)
        super().destroy()


def cancel_widget_timers(widget) -> int:
    """Keep callbacks of surviving widgets; remove only commands being destroyed.

    Tkinter deletes a widget's Python/Tcl commands on destroy, but its queued
    ``after`` calls can outlive it. In particular, CTk button click animations
    can fire after a language change or a wizard Apply rebuilds the interface.
    """
    owners = {}
    pending = [widget]
    try:
        while pending:
            current = pending.pop()
            owners.update({name: current for name in (getattr(current, "_tclCommands", None) or [])})
            pending.extend(current.winfo_children())
        cancelled = 0
        for timer in widget.tk.splitlist(widget.tk.call("after", "info")):
            try:
                script, _kind = widget.tk.call("after", "info", timer)
                words = widget.tk.splitlist(script)
                owner = owners.get(str(words[0])) if words else None
                if owner is not None:
                    # The registering owner must remove its own command list
                    # entry, otherwise its later destroy would delete it twice.
                    owner.after_cancel(timer)
                    cancelled += 1
            except tk.TclError:
                pass
        return cancelled
    except tk.TclError:
        return 0
