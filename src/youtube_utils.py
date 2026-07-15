"""Deliberately scoped online-video download helper."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "music.youtube.com",
}


def is_supported_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in {"http", "https"} and parsed.hostname in ALLOWED_HOSTS
    except ValueError:
        return False


def download_youtube_audio(url, output_dir, progress_callback=None):
    if not is_supported_url(url):
        raise ValueError("Only valid YouTube URLs are supported")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    before = set(output_path.iterdir())
    options = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
        "outtmpl": str(output_path / "%(title).160B-%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "windowsfilenames": os.name == "nt",
    }

    if progress_callback:

        def progress_hook(data):
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                downloaded = data.get("downloaded_bytes") or 0
                if total:
                    progress_callback(min(99.0, downloaded * 100.0 / total))
            elif data.get("status") == "finished":
                progress_callback(99.0)

        options["progress_hooks"] = [progress_hook]

    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
        candidates = sorted(
            (path for path in output_path.iterdir() if path not in before and path.suffix.lower() == ".wav"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            expected = output_path / (Path(downloader.prepare_filename(info)).stem + ".wav")
            if expected.exists():
                candidates = [expected]
        if not candidates:
            raise FileNotFoundError("Downloaded audio could not be located")
        if progress_callback:
            progress_callback(100.0)
        return str(candidates[0])
    except Exception:
        logging.exception("YouTube download failed")
        raise
