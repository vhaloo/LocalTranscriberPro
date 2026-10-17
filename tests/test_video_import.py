import contextlib
import hashlib
import http.server
import json
import threading
import time
import wave
from functools import partial

import pytest

from src.jobs import JobCancelled
from src.youtube_utils import (
    OWNER_FILE,
    VideoDownloadError,
    cleanup_online_audio,
    download_online_audio,
    is_supported_url,
    validate_cookie_file,
)


@contextlib.contextmanager
def media_server(folder, handler=None):
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(handler or QuietHandler, directory=str(folder)))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_audio_real_worker_is_readable_compressed_or_original_and_owned_cleanup(tmp_path):
    from src.video_worker import valid_audio

    source = tmp_path / "server"
    source.mkdir()
    audio = source / "sample.wav"
    with wave.open(str(audio), "wb") as writer:
        writer.setparams((1, 2, 16_000, 0, "NONE", "not compressed"))
        writer.writeframes(b"\x00\x00" * 32_000)
    original_hash = hashlib.sha256(audio.read_bytes()).hexdigest()
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    progress, stages = [], []
    imports = tmp_path / "imports"
    with media_server(source) as base:
        result = download_online_audio(base + "/sample.wav", imports, progress.append,
                                       cookies_file=cookies, status_callback=stages.append)
    from pathlib import Path

    target = Path(result)
    assert valid_audio(target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == original_hash
    assert progress[-1] == 100 and progress == sorted(progress)
    assert "validate" in stages
    assert not (target.parent / "cookies.txt").exists()
    assert not (target.parent / "request.json").exists()
    assert cookies.read_text("utf-8") == "# Netscape HTTP Cookie File\n"
    cleanup_online_audio(target)
    assert not list(imports.iterdir())
    assert audio.is_file() and cookies.is_file()


def test_cancel_stalled_metadata_terminates_worker_without_waiting_for_socket_timeout(tmp_path):
    entered = threading.Event()
    release = threading.Event()

    class StallHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            entered.set()
            release.wait(15)

        def log_message(self, *_args):
            pass

    cancel = threading.Event()
    results = []
    imports = tmp_path / "imports"
    with media_server(tmp_path, StallHandler) as base:
        def run():
            try:
                download_online_audio(base + "/stall.mp4", imports, cancel_event=cancel)
            except BaseException as error:
                results.append(error)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        try:
            assert entered.wait(12), "Worker never reached the local test server"
            started = time.monotonic()
            cancel.set()
            thread.join(timeout=6)
            assert not thread.is_alive()
            assert time.monotonic() - started < 6
            assert len(results) == 1 and isinstance(results[0], JobCancelled)
            assert not list(imports.iterdir())
        finally:
            cancel.set()
            release.set()
            thread.join(timeout=6)


def test_non_audio_response_is_rejected_and_its_partial_files_removed(tmp_path):
    (tmp_path / "bad.mp3").write_bytes(b"not an audio container")
    with media_server(tmp_path) as base, pytest.raises(VideoDownloadError):
        download_online_audio(base + "/bad.mp3", tmp_path / "imports")
    assert not list((tmp_path / "imports").iterdir())


def test_cleanup_refuses_unmarked_or_forged_jobs_and_keeps_siblings(tmp_path):
    job = tmp_path / "ltp-video-example"
    job.mkdir()
    valuable = job / "keep.txt"
    valuable.write_text("user file", encoding="utf-8")
    cleanup_online_audio(valuable)
    assert valuable.exists()
    (job / OWNER_FILE).write_text(json.dumps({"owner": "LocalTranscriberPro", "directory": str(tmp_path)}), encoding="utf-8")
    cleanup_online_audio(valuable)
    assert valuable.exists()
    (job / OWNER_FILE).write_text(json.dumps({"owner": "LocalTranscriberPro", "directory": str(job.resolve())}), encoding="utf-8")
    sibling = tmp_path / "other.txt"
    sibling.write_text("keep", encoding="utf-8")
    cleanup_online_audio(valuable)
    assert not job.exists() and sibling.read_text("utf-8") == "keep"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "javascript:alert(1)", "https://user:secret@example.com/video",
                                  "https://example.com:0/file", "https://[broken", "https://example.com/a\nb"])
def test_unsafe_or_malformed_urls_are_rejected(url):
    assert not is_supported_url(url)


def test_other_sites_and_direct_media_urls_are_accepted():
    assert is_supported_url("https://vimeo.com/123")
    assert is_supported_url("https://example.org/audio.mp3?token=example")
    assert is_supported_url("https://www.youtube.com/watch?v=example")


def test_cookie_validation_never_treats_browser_database_or_json_as_export(tmp_path):
    path = tmp_path / "cookies.txt"
    path.write_text('{"cookies": []}', encoding="utf-8")
    with pytest.raises(VideoDownloadError, match="cookies"):
        validate_cookie_file(path)

