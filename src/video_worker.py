"""Headless downloader worker: no GUI, model loading or access to session data."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import av
import yt_dlp

from src.storage import ONLINE_RESERVE, available_bytes
from src.video_engine import prepared_engine
from src.youtube_utils import (
    OWNER_FILE,
    VideoDownloadError,
    bundled_ffmpeg,
    classify_video_error,
    is_supported_url,
    javascript_runtimes,
    terminate_download,
)

MEDIA_EXTENSIONS = {".m4a", ".m4b", ".mp4", ".webm", ".opus", ".ogg", ".mp3", ".wav", ".flac", ".mkv", ".mka",
                    ".aac", ".ts", ".mov", ".wma", ".avi", ".aiff", ".aif", ".mpeg", ".mpg", ".mp2", ".3gp", ".weba"}
EVENT_FILE = None


def emit(kind, **values):
    value = json.dumps({"event": kind, **values}, ensure_ascii=True)
    if EVENT_FILE is not None:
        with EVENT_FILE.open("a", encoding="utf-8") as stream:
            stream.write(value + "\n")
    elif sys.stdout is not None:
        print(value, flush=True)


def valid_audio(path: Path) -> bool:
    try:
        with av.open(str(path)) as container:
            audio = next(iter(container.streams.audio), None)
            return bool(audio is not None and next(container.decode(audio=0), None) is not None)
    except (av.error.FFmpegError, OSError, ValueError):
        return False


def _space(directory, max_bytes, downloaded=0):
    free = available_bytes(directory)
    if downloaded > max_bytes or (free is not None and free < ONLINE_RESERVE):
        raise VideoDownloadError("space")


class QuietLogger:
    def debug(self, _message):
        pass

    info = debug
    warning = debug
    error = debug


def _embedded_download(url, directory, options, selector):
    def progress(data):
        downloaded = data.get("downloaded_bytes") or 0
        total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
        _space(directory, options["max_bytes"], downloaded)
        if total > options["max_bytes"]:
            raise VideoDownloadError("space")
        emit("progress", percent=downloaded / total * 99 if total else 0)

    settings = {
        "format": selector, "outtmpl": str(directory / "%(title).120B-%(id)s.%(ext)s"),
        "noplaylist": True, "playlistend": 1, "max_downloads": 1,
        "quiet": True, "no_warnings": True, "logger": QuietLogger(), "windowsfilenames": True,
        "socket_timeout": 20, "retries": 5, "fragment_retries": 5, "file_access_retries": 3,
        "skip_unavailable_fragments": False, "continuedl": True,
        "max_filesize": options["max_bytes"], "ffmpeg_location": bundled_ffmpeg(),
        "js_runtimes": javascript_runtimes(), "remote_components": set(),
        "progress_hooks": [progress], "enable_file_urls": False,
        "match_filter": lambda info, **_: "Live streams are not supported" if info.get("is_live") else None,
    }
    if options["cookies_file"]:
        settings["cookiefile"] = options["cookies_file"]
    with yt_dlp.YoutubeDL(settings) as downloader:
        try:
            downloader.extract_info(url, download=True)
        except yt_dlp.utils.MaxDownloadsReached:
            pass


def _external_download(engine, url, directory, options, selector):
    command = [str(engine), "--ignore-config", "--no-playlist", "--playlist-end", "1", "--max-downloads", "1",
               "--no-warnings", "--no-colors", "--newline", "--progress", "--no-simulate",
               "--progress-template", "download:__LTP__%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.total_bytes_estimate)s",
               "--format", selector, "--output", str(directory / "%(title).120B-%(id)s.%(ext)s"),
               "--windows-filenames", "--socket-timeout", "20", "--retries", "5", "--fragment-retries", "5",
               "--file-access-retries", "3", "--abort-on-unavailable-fragments", "--max-filesize", str(options["max_bytes"]),
               "--match-filters", "!is_live", "--ffmpeg-location", bundled_ffmpeg(), "--no-remote-components"]
    for name, spec in javascript_runtimes().items():
        command += ["--js-runtimes", name + ":" + spec["path"]]
    if options["cookies_file"]:
        command += ["--cookies", options["cookies_file"]]
    command += ["--", url]
    errors = []
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0) as process:
        try:
            for line in process.stdout:
                _space(directory, options["max_bytes"])
                if "__LTP__" in line:
                    numbers = line.split("__LTP__", 1)[1].strip().split("|")
                    values = [float(x) if x.replace(".", "", 1).isdigit() else 0 for x in numbers]
                    downloaded = values[0] if values else 0
                    total = next((x for x in values[1:] if x), 0)
                    _space(directory, options["max_bytes"], downloaded)
                    if total > options["max_bytes"]:
                        raise VideoDownloadError("space")
                    emit("progress", percent=downloaded / total * 99 if total else 0)
                elif "ERROR:" in line:
                    errors.append(line[:4000])
            code = process.wait()
        finally:
            if process.poll() is None:
                terminate_download(process)
    if code not in {0, 101}:
        raise VideoDownloadError(classify_video_error(" ".join(errors)))


def run(request: Path) -> int:
    options = json.loads(request.read_text("utf-8"))
    directory = Path(options["directory"])
    marker = json.loads((directory / OWNER_FILE).read_text("utf-8"))
    if (request.parent.resolve() != directory.resolve() or not directory.name.startswith("ltp-video-")
            or marker != {"owner": "LocalTranscriberPro", "directory": str(directory.resolve())}
            or not is_supported_url(options["url"])):
        raise VideoDownloadError("url")
    engine = prepared_engine()
    for index, selector in enumerate(("bestaudio[ext=m4a]/bestaudio/best", "worstaudio/worst[acodec!=none]/best")):
        emit("stage", stage="retry" if index else "download")
        attempt = directory / ("attempt-" + str(index))
        attempt.mkdir()
        try:
            if engine:
                _external_download(engine[0], options["url"], attempt, options, selector)
            else:
                _embedded_download(options["url"], attempt, options, selector)
            emit("stage", stage="validate")
            candidates = [p for p in attempt.iterdir() if p.suffix.lower() in MEDIA_EXTENSIONS and p.is_file()]
            if len(candidates) != 1 or not valid_audio(candidates[0]):
                raise VideoDownloadError("output")
            result = candidates[0]
            if result.stat().st_size > options["max_bytes"]:
                raise VideoDownloadError("space")
            target = directory / result.name
            result.replace(target)
            emit("complete", path=str(target.resolve()))
            return 0
        except Exception as error:
            code = error.code if isinstance(error, VideoDownloadError) else classify_video_error(str(error))
            if index or code in {"auth", "restricted", "space", "unsupported"}:
                raise VideoDownloadError(code) from None
            # The first attempt belongs to this job; free its partial fragments
            # before trying the smaller fallback format.
            shutil.rmtree(attempt)
    raise VideoDownloadError("extractor")


def main(request):
    global EVENT_FILE
    try:
        folder = Path(request).parent
        if folder.name.startswith("ltp-video-") and (folder / OWNER_FILE).is_file():
            EVENT_FILE = folder / "events.jsonl"
        return run(Path(request))
    except Exception as error:
        emit("error", code=error.code if isinstance(error, VideoDownloadError) else "extractor")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
