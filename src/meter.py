"""Vector microphone meter inspired by classic tape recorders."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Sequence


def amplitude_to_db(amplitude: float) -> float:
    """Convert a normalized amplitude to a display-safe decibel value."""
    value = max(0.000001, min(1.0, float(amplitude)))
    return max(-60.0, min(0.0, 20.0 * math.log10(value)))


class TapeMeter(tk.Canvas):
    """Responsive waveform, LED bar and analog VU needle in one canvas."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("height", 112)
        kwargs.setdefault("background", "#07131D")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(master, **kwargs)
        self.amplitude = 0.0
        self.peak = 0.0
        self.waveform = [0.0] * 50
        self.active = False
        self.recording = False
        self.bind("<Configure>", lambda _event: self._draw(), add="+")

    def update_levels(
        self,
        amplitude: float,
        waveform: Sequence[float],
        *,
        active: bool,
        recording: bool,
    ) -> None:
        incoming = max(0.0, min(1.0, float(amplitude)))
        self.amplitude = (self.amplitude * 0.68) + (incoming * 0.32)
        self.peak = max(incoming, self.peak * 0.94)
        samples = [max(-1.0, min(1.0, float(value))) for value in waveform]
        self.waveform = samples or [0.0] * 50
        self.active = active
        self.recording = recording
        self._draw()

    def _draw(self) -> None:
        width = max(320, self.winfo_width())
        height = max(92, self.winfo_height())
        self.delete("all")
        self.create_rectangle(0, 0, width, height, fill="#07131D", outline="#29445A", width=1)

        wave_right = int(width * 0.69)
        center_y = int(height * 0.47)
        for index in range(1, 6):
            x = 16 + ((wave_right - 32) * index / 6)
            self.create_line(x, 14, x, height - 25, fill="#173044")
        for offset in (-26, 0, 26):
            self.create_line(16, center_y + offset, wave_right - 12, center_y + offset, fill="#173044")

        if self.active:
            count = max(2, len(self.waveform))
            points: list[float] = []
            wave_height = max(18.0, (height - 38) * 0.45)
            for index, sample in enumerate(self.waveform):
                x = 16 + ((wave_right - 32) * index / (count - 1))
                y = center_y - (sample * wave_height * 7.0)
                y = max(12.0, min(height - 29.0, y))
                points.extend((x, y))
            if len(points) >= 4:
                self.create_line(
                    *points,
                    fill="#FF6F7F" if self.recording else "#5EE4B7",
                    width=2,
                    smooth=True,
                )
        else:
            self.create_line(16, center_y, wave_right - 12, center_y, fill="#456071", width=2)

        bar_x0, bar_x1 = 16, wave_right - 12
        bar_y0, bar_y1 = height - 18, height - 10
        self.create_rectangle(bar_x0, bar_y0, bar_x1, bar_y1, fill="#102638", outline="")
        ratio = max(0.0, min(1.0, (amplitude_to_db(self.amplitude) + 60.0) / 60.0))
        fill_x = bar_x0 + ((bar_x1 - bar_x0) * ratio)
        color = "#F06878" if ratio > 0.86 else ("#F3C969" if ratio > 0.68 else "#5EE4B7")
        self.create_rectangle(bar_x0, bar_y0, fill_x, bar_y1, fill=color, outline="")
        for marker in (0.33, 0.66, 0.86):
            marker_x = bar_x0 + ((bar_x1 - bar_x0) * marker)
            self.create_line(marker_x, bar_y0, marker_x, bar_y1, fill="#07131D")

        pivot_x, pivot_y = int(width * 0.845), int(height * 0.83)
        radius = min(int(width * 0.135), int(height * 0.64))
        for index, label in enumerate(("-30", "-20", "-10", "-6", "-3", "0")):
            angle = math.radians(205 + (index * 25))
            outer_x = pivot_x + math.cos(angle) * radius
            outer_y = pivot_y + math.sin(angle) * radius
            inner_x = pivot_x + math.cos(angle) * (radius - 8)
            inner_y = pivot_y + math.sin(angle) * (radius - 8)
            self.create_line(inner_x, inner_y, outer_x, outer_y, fill="#8BA1AE", width=1)
            text_x = pivot_x + math.cos(angle) * (radius - 18)
            text_y = pivot_y + math.sin(angle) * (radius - 18)
            self.create_text(text_x, text_y, text=label, fill="#708692", font=("Segoe UI", 7))

        needle_ratio = max(0.0, min(1.0, (amplitude_to_db(self.amplitude) + 40.0) / 40.0))
        needle_angle = math.radians(205 + (needle_ratio * 125))
        needle_x = pivot_x + math.cos(needle_angle) * (radius - 5)
        needle_y = pivot_y + math.sin(needle_angle) * (radius - 5)
        self.create_line(pivot_x, pivot_y, needle_x, needle_y, fill="#FF6F7F", width=2)
        self.create_oval(pivot_x - 5, pivot_y - 5, pivot_x + 5, pivot_y + 5, fill="#D7B16C", outline="")
        self.create_text(pivot_x, 14, text="VU", fill="#D7B16C", font=("Georgia", 11, "bold"))
        state_text = "REC" if self.recording else ("MIC" if self.active else "OFF")
        self.create_text(
            wave_right + 8,
            height - 12,
            anchor="w",
            text=f"{state_text}   {amplitude_to_db(self.peak):.0f} dB",
            fill="#FF6F7F" if self.recording else ("#5EE4B7" if self.active else "#708692"),
            font=("Consolas", 9, "bold"),
        )
