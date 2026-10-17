"""Optional official yt-dlp executable updates, size/SHA-256 verified first."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_cache_dir

from src.jobs import check_cancelled
from src.updater import _open, expected_checksum
from src.utils import atomic_write_text

REPOSITORY = "yt-dlp/yt-dlp-nightly-builds"
RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
MAX_ENGINE_BYTES = 96 * 1024**2


def engine_directory() -> Path:
    return Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "video-engine"


def engine_filename() -> str:
    system = platform.system()
    if system == "Windows":
        return "yt-dlp.exe"
    if system == "Darwin":
        return "yt-dlp_macos"
    if system == "Linux" and platform.machine().lower() in {"x86_64", "amd64"}:
        return "yt-dlp_linux"
    raise ValueError("No verified video engine package for this platform")


@dataclass(frozen=True)
class VideoEngineUpdate:
    version: str
    filename: str
    url: str
    checksum_url: str
    size: int


def parse_engine_release(payload: dict) -> VideoEngineUpdate:
    version = str(payload.get("tag_name", ""))
    if payload.get("draft") or not re.fullmatch(r"20\d{2}\.\d{1,2}\.\d{1,2}(?:\.\d+)?", version):
        raise ValueError("Invalid official video engine release")
    filename = engine_filename()
    assets = {item.get("name"): item for item in payload.get("assets", []) if isinstance(item, dict)}
    package, checksums = assets.get(filename), assets.get("SHA2-256SUMS")
    if not package or not checksums:
        raise ValueError("The official release is missing its package or checksums")
    prefix = f"https://github.com/{REPOSITORY}/releases/download/{version}/"
    for item in (package, checksums):
        if item.get("browser_download_url") != prefix + item["name"]:
            raise ValueError("Video engine assets are outside the official repository")
    size = int(package.get("size", 0))
    if not 0 < size <= MAX_ENGINE_BYTES:
        raise ValueError("Invalid video engine package size")
    return VideoEngineUpdate(version, filename, package["browser_download_url"],
                             checksums["browser_download_url"], size)


def find_engine_update() -> VideoEngineUpdate:
    with _open(RELEASE_API) as response:
        data = response.read(1024**2 + 1)
    if len(data) > 1024**2:
        raise ValueError("Video engine release metadata is too large")
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError("Invalid video engine release metadata")
    return parse_engine_release(payload)


def prepared_engine(folder: Path | None = None) -> tuple[Path, str] | None:
    """An unverified or changed executable is never launched."""
    folder = folder or engine_directory()
    try:
        receipt = json.loads((folder / "verified-engine.json").read_text("utf-8"))
        if receipt.get("repository") != REPOSITORY or receipt.get("filename") != engine_filename():
            return None
        if not re.fullmatch(r"20\d{2}\.\d{1,2}\.\d{1,2}(?:\.\d+)?", receipt["version"]):
            return None
        path = folder / engine_filename()
        stat = path.lstat()
        if path.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
            return None
        if stat.st_size != receipt["size"] or not 0 < stat.st_size <= MAX_ENGINE_BYTES:
            return None
        with path.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != receipt["sha256"]:
                return None
        return path, receipt["version"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def install_engine(update: VideoEngineUpdate, folder: Path | None = None, progress=None, cancel_event=None) -> Path:
    """Only called after the user chooses the engine update button."""
    folder = folder or engine_directory()
    prefix = f"https://github.com/{REPOSITORY}/releases/download/{update.version}/"
    if (not re.fullmatch(r"20\d{2}\.\d{1,2}\.\d{1,2}(?:\.\d+)?", update.version)
            or update.filename != engine_filename() or update.url != prefix + update.filename
            or update.checksum_url != prefix + "SHA2-256SUMS" or not 0 < update.size <= MAX_ENGINE_BYTES):
        raise ValueError("Invalid video engine download")
    check_cancelled(cancel_event)
    with _open(update.checksum_url) as response:
        manifest = response.read(256 * 1024 + 1)
    if len(manifest) > 256 * 1024:
        raise ValueError("Video engine checksum manifest is too large")
    expected = expected_checksum(manifest.decode("utf-8-sig"), update.filename)
    folder.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix="engine-", suffix=".part", dir=folder)
    temporary = Path(filename)
    try:
        digest, downloaded = hashlib.sha256(), 0
        with os.fdopen(descriptor, "wb") as handle, _open(update.url) as response:
            while True:
                check_cancelled(cancel_event)
                block = response.read(1024**2)
                if not block:
                    break
                downloaded += len(block)
                if downloaded > update.size:
                    raise ValueError("Video engine exceeds its announced size")
                digest.update(block)
                handle.write(block)
                if progress:
                    progress(downloaded / update.size)
            handle.flush()
            os.fsync(handle.fileno())
        check_cancelled(cancel_event)
        if downloaded != update.size or digest.hexdigest() != expected:
            raise ValueError("Video engine failed size/SHA-256 verification")
        if os.name != "nt":
            temporary.chmod(temporary.stat().st_mode | 0o100)
        destination = folder / update.filename
        temporary.replace(destination)
        atomic_write_text(folder / "verified-engine.json", json.dumps({
            "repository": REPOSITORY, "version": update.version, "filename": update.filename,
            "size": downloaded, "sha256": expected,
        }))
        return destination
    finally:
        temporary.unlink(missing_ok=True)
