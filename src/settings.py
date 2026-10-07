"""Persistent, migration-friendly application settings."""

from __future__ import annotations

import copy
import json
import re
import threading
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_data_dir, user_documents_dir

from src.i18n import detect_ui_language
from src.models import AUTO_FAST_MODEL_ID, AUTO_MODEL_ID, MODEL_BY_ID
from src.utils import atomic_write_text


def default_output_folder() -> Path:
    return Path(user_documents_dir()) / "Transcriptions"


def ensure_output_folder(value: str | Path | None = None) -> Path:
    """Return a writable user-owned folder without requiring administrator rights."""
    preferred = Path(value).expanduser() if value else default_output_folder()
    for candidate in (preferred, Path(user_data_dir("LocalTranscriberPro", "Vhaloo")) / "Transcriptions"):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            # mkdir(exist_ok=True) alone does not prove that a folder is writable.
            import tempfile

            with tempfile.TemporaryFile(dir=candidate):
                pass
            return candidate
        except OSError:
            continue
    raise OSError("No writable transcription output folder is available")


def bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError, OverflowError):
        return default


DEFAULTS: dict[str, Any] = {
    "schema_version": 5,
    "ui_language": detect_ui_language(),
    "ui_mode": "simple",
    "simple_quality": "best",
    "microphone": "auto",
    "preset": "files",
    "model": AUTO_MODEL_ID,
    "device": "auto",
    "spoken_language": "auto",
    "translate": False,
    "speaker_detection": False,
    "vad": True,
    "cleanup": True,
    "open_result": False,
    "smart_subtitles": True,
    "chunk_seconds": 30,
    "beam_size": 8,
    "transcript_layout": "blocks",
    "show_timestamps": True,
    "show_duration": False,
    "output_folder": str(default_output_folder()),
    "benchmarks": {},
    "window_geometry": "1220x940",
    "check_updates": True,
    "keep_recording_audio": True,
    "vocabulary": "",
}


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(user_config_dir("LocalTranscriberPro", "Vhaloo")) / "settings.json"
        self._lock = threading.RLock()
        self.data = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
                if self.data.get("window_geometry") == "1180x860":
                    self.data["window_geometry"] = "1220x940"
                self.data["schema_version"] = DEFAULTS["schema_version"]
                for key, choices in {
                    "ui_language": {"en", "fr"}, "ui_mode": {"simple", "advanced"},
                    "simple_quality": {"best", "fast"}, "device": {"auto", "cpu", "cuda", "metal"},
                    "transcript_layout": {"blocks", "lines"},
                    "model": {AUTO_MODEL_ID, AUTO_FAST_MODEL_ID, *MODEL_BY_ID},
                    "preset": {"files", "conference", "dictation", "link"},
                }.items():
                    if not isinstance(self.data.get(key), str) or self.data[key] not in choices:
                        self.data[key] = DEFAULTS[key]
                for key, default in DEFAULTS.items():
                    if isinstance(default, bool) and not isinstance(self.data.get(key), bool):
                        self.data[key] = default
                self.data["chunk_seconds"] = bounded_int(self.data.get("chunk_seconds"), 30, 5, 60)
                self.data["beam_size"] = bounded_int(self.data.get("beam_size"), 8, 1, 10)
                if not isinstance(self.data.get("benchmarks"), dict):
                    self.data["benchmarks"] = {}
                if not isinstance(self.data.get("vocabulary"), str):
                    self.data["vocabulary"] = ""
                self.data["vocabulary"] = self.data["vocabulary"][:2000]
                for key in ("output_folder", "microphone", "spoken_language"):
                    if not isinstance(self.data.get(key), str) or not self.data[key].strip():
                        self.data[key] = DEFAULTS[key]
                if not re.fullmatch(r"auto|[a-z]{2,3}", self.data["spoken_language"]):
                    self.data["spoken_language"] = "auto"
                geometry = self.data.get("window_geometry")
                if not isinstance(geometry, str) or not re.fullmatch(r"\d+x\d+(?:[+-]\d+[+-]\d+)?", geometry):
                    self.data["window_geometry"] = DEFAULTS["window_geometry"]
        except (OSError, ValueError, TypeError):
            return

    def save(self) -> None:
        with self._lock:
            atomic_write_text(self.path, json.dumps(self.data, indent=2, ensure_ascii=False))

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any, save: bool = False) -> None:
        with self._lock:
            self.data[key] = value
            if save:
                self.save()

    def update(self, values: dict[str, Any], save: bool = False) -> None:
        with self._lock:
            self.data.update(values)
            if save:
                self.save()
