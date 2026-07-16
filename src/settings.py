"""Persistent, migration-friendly application settings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_data_dir, user_documents_dir

from src.i18n import detect_ui_language
from src.models import AUTO_MODEL_ID


def default_output_folder() -> Path:
    return Path(user_documents_dir()) / "Transcriptions"


def ensure_output_folder(value: str | Path | None = None) -> Path:
    """Return a writable user-owned folder without requiring administrator rights."""
    preferred = Path(value).expanduser() if value else default_output_folder()
    for candidate in (preferred, Path(user_data_dir("LocalTranscriberPro", "Vhaloo")) / "Transcriptions"):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue
    return preferred


DEFAULTS: dict[str, Any] = {
    "schema_version": 4,
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
}


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(user_config_dir("LocalTranscriberPro", "Vhaloo")) / "settings.json"
        self.data = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
                if self.data.get("window_geometry") == "1180x860":
                    self.data["window_geometry"] = "1220x940"
                self.data["schema_version"] = DEFAULTS["schema_version"]
        except (OSError, ValueError, TypeError):
            return

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any, save: bool = False) -> None:
        self.data[key] = value
        if save:
            self.save()

    def update(self, values: dict[str, Any], save: bool = False) -> None:
        self.data.update(values)
        if save:
            self.save()
