"""Thread-safe commands and review overlays for one recording session.

The audio worker owns inference. UI language changes are consumed between
complete turns, and edits are reapplied to worker snapshots by stable ID.
"""
from __future__ import annotations

import copy
import threading
from uuid import uuid4


def identified(segments):
    return [dict(item, segment_id=item.get("segment_id") or uuid4().hex) for item in segments]


class SessionController:
    def __init__(self):
        self._lock = threading.RLock()
        self.languages = None
        self.edits = {}
        self.extras = []
        self.generation = 0

    def configure_languages(self, target, partner=None, third=None):
        if not target or target == partner:
            raise ValueError("Choose two different conversation languages")
        with self._lock:
            self.languages = (target, partner, third)
            self.generation += 1

    def language_command(self, generation):
        with self._lock:
            return (self.generation, self.languages) if generation != self.generation else (generation, None)

    def correct(self, item):
        if not item.get("segment_id"):
            raise ValueError("A reviewed segment needs a stable ID")
        with self._lock:
            self.edits[item["segment_id"]] = copy.deepcopy(item)

    def snapshot(self, segments):
        with self._lock:
            ids = {item.get("segment_id") for item in segments}
            values = [*segments, *(item for item in self.extras if item["segment_id"] not in ids)]
            values.sort(key=lambda item: item.get("start", 0))
            return [copy.deepcopy(self.edits.get(item.get("segment_id"), item)) for item in values]

    def add_reply(self, item):
        with self._lock:
            self.extras.append(copy.deepcopy(item))


class PreviewScheduler:
    """Only preview idle inference capacity; final audio always has priority."""
    def __init__(self, interval=2.5):
        self.interval, self.last, self.duration, self.cost = interval, 0.0, 0.0, 0.0

    def due(self, now, seconds, pending=0):
        return (pending == 0 and seconds >= 1.5 and seconds > self.duration + 0.8
                and now - self.last >= max(self.interval, self.cost * 2))

    def completed(self, now, seconds, cost):
        self.last, self.duration, self.cost = now, seconds, cost

    def reset_turn(self):
        self.duration = 0.0
