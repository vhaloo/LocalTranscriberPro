"""Cancellable online media import, isolated from the GUI and private sessions."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import imageio_ffmpeg
import psutil

from src.jobs import JobCancelled, check_cancelled
from src.storage import ONLINE_RESERVE, available_bytes

OWNER_FILE = ".ltp-owned-download.json"
MAX_COOKIE_BYTES = 10 * 1024**2
ERROR_CODES = {"url", "size_limit", "cookies", "space", "output", "auth", "restricted", "unsupported", "network", "extractor"}


class VideoDownloadError(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code, self.detail = code if code in ERROR_CODES else "extractor", detail
        super().__init__(self.code)


def classify_video_error(message: str) -> str:
    text = message.casefold()
    for code, tokens in (
        ("auth", ("sign in", "login", "log in", "cookies", "confirm you're not a bot", "authentication", "private video", "members-only")),
        ("restricted", ("drm", "geo-restrict", "not available in your country", "copyright", "removed", "video unavailable", "not found")),
        ("space", ("no space left", "disk full", "not enough space", "file is larger", "maximum filesize")),
        ("unsupported", ("unsupported url", "no video formats", "no suitable extractor")),
        ("network", ("403", "429", "timed out", "timeout", "connection", "network", "unable to download", "fragment")),
    ):
        if any(token in text for token in tokens):
            return code
    return "extractor"


def bundled_ffmpeg() -> str:
    path = imageio_ffmpeg.get_ffmpeg_exe()
    if not Path(path).is_file():
        raise FileNotFoundError("The packaged FFmpeg audio helper is missing")
    return path


def is_supported_url(url: str) -> bool:
    try:
        value = url.strip()
        parsed = urlparse(value)
        return bool(parsed.scheme in {"http", "https"} and parsed.hostname and parsed.port != 0
                    and parsed.username is None and parsed.password is None
                    and not any(ord(char) < 33 for char in value))
    except (ValueError, AttributeError):
        return False


def javascript_runtimes() -> dict:
    filename = "node.exe" if os.name == "nt" else "node"
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    bundled = root / "js-runtime" / filename
    if bundled.is_file():
        return {"node": {"path": str(bundled)}}
    for name in ("deno", "node"):
        path = shutil.which(name)
        if path:
            return {name: {"path": path}}
    return {}


def validate_cookie_file(path: str | Path) -> Path:
    source = Path(path).expanduser()
    if not source.is_file() or source.stat().st_size > MAX_COOKIE_BYTES:
        raise VideoDownloadError("cookies")
    with source.open("rb") as handle:
        header = handle.read(256).decode("utf-8-sig", errors="replace")
    if "HTTP Cookie File" not in header.split("\n", 1)[0]:
        raise VideoDownloadError("cookies")
    return source


def cleanup_online_audio(path: str | Path) -> None:
    """Remove only an import directory this application explicitly owns."""
    job = Path(path).parent
    try:
        if (not job.name.startswith("ltp-video-") or job.is_symlink()
                or getattr(job.lstat(), "st_file_attributes", 0) & 0x400):
            return
        marker = json.loads((job / OWNER_FILE).read_text("utf-8"))
        if marker != {"owner": "LocalTranscriberPro", "directory": str(job.resolve())}:
            return
        shutil.rmtree(job)
    except (OSError, ValueError):
        return


def terminate_download(process: subprocess.Popen) -> None:
    """Cancel only this worker and its own downloader/JavaScript children."""
    try:
        children = psutil.Process(process.pid).children(recursive=True)
    except psutil.Error:
        children = []
    for child in reversed(children):
        try:
            child.terminate()
        except psutil.Error:
            pass
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
    for child in children:
        try:
            if child.is_running():
                child.kill()
        except psutil.Error:
            pass


def download_online_audio(url, output_dir, progress_callback=None, cancel_event=None, *,
                          cookies_file=None, max_bytes=2_000_000_000, status_callback=None):
    if not is_supported_url(url):
        raise VideoDownloadError("url")
    if not 64 * 1024**2 <= max_bytes <= 8 * 1024**3:
        raise VideoDownloadError("size_limit")
    cookie = validate_cookie_file(cookies_file) if cookies_file else None
    check_cancelled(cancel_event)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    free = available_bytes(root)
    if free is not None and free < ONLINE_RESERVE:
        raise VideoDownloadError("space")
    job = Path(tempfile.mkdtemp(prefix="ltp-video-", dir=root))
    (job / OWNER_FILE).write_text(json.dumps({"owner": "LocalTranscriberPro", "directory": str(job.resolve())}), encoding="utf-8")
    request = job / "request.json"
    events_path = job / "events.jsonl"
    process = None
    events = None
    succeeded = False
    try:
        if cookie:
            destination = job / "cookies.txt"
            with cookie.open("rb") as source:
                content = source.read(MAX_COOKIE_BYTES + 1)
            if len(content) > MAX_COOKIE_BYTES:
                raise VideoDownloadError("cookies")
            destination.write_bytes(content)
            if os.name != "nt":
                destination.chmod(0o600)
            cookie = destination
        request.write_text(json.dumps({"url": url.strip(), "directory": str(job.resolve()),
                                       "cookies_file": str(cookie) if cookie else "", "max_bytes": max_bytes}), encoding="utf-8")
        events_path.touch()
        events = events_path.open("r", encoding="utf-8")
        command = ([sys.executable, "--video-worker", str(request)] if getattr(sys, "frozen", False)
                   else [sys.executable, "-m", "src.video_worker", str(request)])
        process = subprocess.Popen(command, cwd=Path(__file__).parents[1] if not getattr(sys, "frozen", False) else None,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        deadline, highest_progress = time.monotonic() + 45 * 60, 0.0
        pending = ""
        while True:
            check_cancelled(cancel_event)
            if time.monotonic() > deadline:
                raise VideoDownloadError("network")
            line = events.readline(64 * 1024)
            if not line:
                if process.poll() is not None:
                    raise VideoDownloadError("extractor")
                time.sleep(0.12)
                continue
            pending += line
            if len(pending) > 64 * 1024:
                raise VideoDownloadError("output")
            if not pending.endswith("\n"):
                continue
            event = json.loads(pending)
            pending = ""
            if not isinstance(event, dict):
                raise VideoDownloadError("output")
            kind = event.get("event")
            if kind == "progress":
                highest_progress = max(highest_progress, min(99, max(0, float(event.get("percent", 0)))))
                if progress_callback:
                    progress_callback(highest_progress)
            elif kind == "stage" and status_callback:
                status_callback(str(event.get("stage", "download")))
            elif kind == "error":
                raise VideoDownloadError(str(event.get("code", "extractor")))
            elif kind == "complete":
                path = Path(event.get("path", ""))
                if path.parent.resolve() != job.resolve() or not path.is_file() or path.is_symlink():
                    raise VideoDownloadError("output")
                process.wait(timeout=10)
                if process.returncode != 0:
                    raise VideoDownloadError("extractor")
                check_cancelled(cancel_event)
                if progress_callback:
                    progress_callback(100)
                succeeded = True
                return str(path)
    except JobCancelled:
        raise
    finally:
        if process is not None and process.poll() is None:
            terminate_download(process)
        if events is not None:
            events.close()
        if not succeeded:
            cleanup_online_audio(job / "unused")
        else:
            request.unlink(missing_ok=True)
            if cookie and cookie.parent == job:
                cookie.unlink(missing_ok=True)


def download_youtube_audio(url, output_dir, progress_callback=None, cancel_event=None, **options):
    """Compatibility entry point; other supported websites now use the same flow."""
    return download_online_audio(url, output_dir, progress_callback, cancel_event, **options)
