"""Readable storage budgets and bounded, read-only directory inspection."""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_cache_dir, user_log_dir

from src.models import MODEL_CATALOG

GB = 1_000_000_000
APPLICATION_BUDGET = 5.8 * GB
MINIMUM_INSTALL_FREE = 12 * GB
ONLINE_RESERVE = GB


def format_bytes(value: int | float | None, language="en") -> str:
    if value is None:
        return "—"
    if value >= GB:
        return f"{value / GB:.1f} {'Go' if language == 'fr' else 'GB'}"
    return f"{value / 1_000_000:.0f} {'Mo' if language == 'fr' else 'MB'}"


def catalogue_budget() -> dict[str, int]:
    """Budgets, not promises: Hub copies/revisions and recordings can grow."""
    data = Path(__file__).parent / "data"
    piper = json.loads((data / "voices.json").read_text("utf-8"))
    mms = json.loads((data / "mms_voices.json").read_text("utf-8"))
    voices = sum(f["size"] for voice in [*piper["voices"].values(), *mms.values()]
                 for f in voice["files"].values())
    voices += sum(f["size"] for f in piper["common"]["files"].values())
    recognizers = sum(model.size_gb for model in MODEL_CATALOG) * GB
    extras = (2.96 + 8.33 + 0.113 + 0.10 + 0.25) * GB + voices
    stored = APPLICATION_BUDGET + recognizers + extras
    # Windows Hub fallback may retain both blobs and materialized snapshots.
    preparation = stored + recognizers + 8 * GB
    return {
        "minimum_files": int(APPLICATION_BUDGET + 0.08 * GB),
        "minimum_free": int(MINIMUM_INSTALL_FREE),
        "universal_files": int(APPLICATION_BUDGET + (3.10 + 2.96) * GB),
        "coverage_files": int(APPLICATION_BUDGET + (5.60 + 2.96) * GB),
        "catalogue_files": math.ceil(stored / GB) * GB,
        "catalogue_free_budget": math.ceil(preparation / (5 * GB)) * 5 * GB,
        "recording_hour": 16_000 * 2 * 3600,
    }


def available_bytes(path: Path) -> int | None:
    candidate = Path(path).absolute()
    try:
        while not candidate.exists() and candidate != candidate.parent:
            candidate = candidate.parent
        return shutil.disk_usage(candidate).free
    except OSError:
        return None


@dataclass(frozen=True)
class DirectoryUsage:
    bytes: int
    files: int
    partial: bool = False


def directory_usage(path: Path, *, seconds=2.0, max_files=100_000, exclude=()) -> DirectoryUsage:
    """Never traverse junctions/symlinks or hold up the desktop UI."""
    path = Path(path)
    try:
        info = path.lstat()
        if path.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            return DirectoryUsage(0, 0, True)
        if path.is_file():
            return DirectoryUsage(info.st_size, 1)
    except FileNotFoundError:
        return DirectoryUsage(0, 0)
    except OSError:
        return DirectoryUsage(0, 0, True)
    started = time.monotonic()
    total = count = 0
    partial = False
    stack = [path]
    seen = set()
    while stack:
        try:
            with os.scandir(stack.pop()) as entries:
                for entry in entries:
                    if time.monotonic() - started > seconds or count >= max_files:
                        return DirectoryUsage(total, count, True)
                    if entry.name in exclude:
                        continue
                    try:
                        stat = entry.stat(follow_symlinks=False)
                        if entry.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
                            partial = True
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        else:
                            # On Windows DirEntry.stat() omits file identity;
                            # os.stat() is required to recognize hardlinks.
                            if os.name == "nt" and not stat.st_ino:
                                stat = os.stat(entry.path, follow_symlinks=False)
                            identity = (stat.st_dev, stat.st_ino)
                            if stat.st_ino and identity in seen:
                                continue
                            seen.add(identity)
                            total += stat.st_size
                            count += 1
                    except OSError:
                        partial = True
        except OSError:
            partial = True
    return DirectoryUsage(total, count, partial)


def storage_locations(output: Path, settings: Path, history: Path) -> list[tuple[str, Path]]:
    cache = Path(user_cache_dir("LocalTranscriberPro", "Vhaloo"))
    application = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parents[1]
    if application.name == "MacOS" and application.parent.name == "Contents":
        application = application.parent.parent
    return [
        ("storage_application", application), ("storage_exports", Path(output)),
        ("storage_settings", Path(settings)), ("storage_history", Path(history)),
        ("storage_recovery", Path(history).parent / "unsaved_session.json"),
        ("storage_models", cache / "models"), ("storage_omnilingual", cache / "omnilingual"),
        ("storage_translation", cache / "translation"), ("storage_voices", cache / "voices"),
        ("storage_separation", cache / "separation"), ("storage_speakers", cache / "speechbrain"),
        ("storage_online", cache / "online-audio"), ("storage_video_engine", cache / "video-engine"),
        ("storage_updates", cache / "updates"),
        ("storage_logs", Path(user_log_dir("LocalTranscriberPro", "Vhaloo"))),
    ]
