"""Cancellable CPU inference in owned processes, with memory-only local IPC.

JSON and float32 frames cross an authenticated OS pipe/socket. No pickle and no
conversation files are used. The OS can page allocations; it remains responsible
for the commit limit. The application never changes system pagefile settings.
"""
from __future__ import annotations

import base64
import json
import os
import queue
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from multiprocessing.connection import Client, Listener
from pathlib import Path

MAX_FRAME = 512 * 1024 * 1024
AUTH_ENV = "LTP_CPU_WORKER_AUTH"
PARENT_ENV = "LTP_CPU_WORKER_PARENT"


def _encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      default=lambda item: item.item()).encode("utf-8")


def options_payload(options):
    from dataclasses import fields
    return {item.name: getattr(options, item.name) for item in fields(options)
            if item.name not in {"cancel_event", "activity_callback", "original_callback"}}


class CPUWorkerClient:
    """Own exactly one subprocess; closing it never waits for an inference lock."""

    def __init__(self):
        self._lock = threading.RLock()
        self._closed = False
        self._connection = None
        self._temporary = None
        self._process = None
        self._worker_pid = None
        self._accepted = queue.Queue(maxsize=1)
        key = secrets.token_bytes(32)
        if os.name == "nt":
            address = rf"\\.\pipe\ltp-cpu-{uuid.uuid4().hex}"
            family = "AF_PIPE"
        else:
            self._temporary = tempfile.TemporaryDirectory(prefix="ltp-cpu-")
            os.chmod(self._temporary.name, 0o700)
            address = str(Path(self._temporary.name) / "worker.sock")
            family = "AF_UNIX"
        self._listener = Listener(address, family=family, authkey=key)

        def accept():
            try:
                connection = self._listener.accept()
                if self._closed:
                    connection.close()
                else:
                    self._accepted.put(connection)
            except (OSError, EOFError) as error:
                if not self._closed:
                    self._accepted.put(error)

        threading.Thread(target=accept, daemon=True, name="cpu-worker-handshake").start()
        environment = os.environ.copy()
        environment[AUTH_ENV] = base64.b64encode(key).decode("ascii")
        environment[PARENT_ENV] = str(os.getpid())
        environment["CUDA_VISIBLE_DEVICES"] = ""
        command = [sys.executable]
        if not getattr(sys, "frozen", False):
            command.append(str(Path(__file__).resolve().parents[1] / "main.py"))
        command += ["--cpu-worker", address]
        try:
            self._process = subprocess.Popen(
                command, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except BaseException:
            self.close()
            raise

    @property
    def pid(self):
        return self._worker_pid or (self._process.pid if self._process else None)

    @property
    def alive(self):
        return not self._closed and self._process is not None and self._process.poll() is None

    def _check(self, cancel_event):
        from src.jobs import JobCancelled, check_cancelled
        try:
            check_cancelled(cancel_event)
        except JobCancelled:
            self.close()
            raise
        if self._closed:
            raise JobCancelled("CPU operation cancelled")
        if not self.alive:
            raise RuntimeError("The CPU worker stopped. The requested model was not replaced. "
                               "Check available disk space and the OS virtual-memory limit, then retry.")

    def _connect(self, cancel_event):
        if self._connection is not None:
            return
        deadline = time.monotonic() + 120
        while self._connection is None:
            self._check(cancel_event)
            try:
                accepted = self._accepted.get(timeout=0.05)
            except queue.Empty:
                if time.monotonic() >= deadline:
                    self.close()
                    raise RuntimeError("The CPU worker could not start within 120 seconds.") from None
                continue
            if isinstance(accepted, BaseException):
                self.close()
                raise RuntimeError("The local CPU connection could not be opened.") from accepted
            self._connection = accepted
            self._listener.close()

    def call(self, operation, payload=None, *, audio=None, cancel_event=None, event=None):
        with self._lock:
            self._connect(cancel_event)
            self._check(cancel_event)
            frame = _encode({"operation": operation, "payload": payload or {}, "audio": audio is not None})
            if len(frame) > MAX_FRAME or (audio is not None and len(audio) > MAX_FRAME):
                raise ValueError("CPU inference input is too large for one operation")
            try:
                self._connection.send_bytes(frame)
                if audio is not None:
                    self._connection.send_bytes(audio)
                while True:
                    self._check(cancel_event)
                    if not self._connection.poll(0.05):
                        continue
                    response = json.loads(self._connection.recv_bytes(MAX_FRAME))
                    if response.get("event"):
                        if response["event"] == "identity":
                            self._worker_pid = int(response["value"])
                        elif event:
                            event(response["event"], response.get("value"))
                    elif "error" in response:
                        raise RuntimeError(response["error"])
                    else:
                        return response["result"]
            except (OSError, EOFError) as error:
                self._check(cancel_event)
                raise RuntimeError("The CPU worker disconnected. The requested model was not replaced; "
                                   "check OS virtual memory and free disk space.") from error

    def transcribe(self, source, options, progress_callback=None, *, conversation_pair=()):
        import numpy as np
        array = isinstance(source, np.ndarray)
        payload = {"source": None if array else str(source), "options": options_payload(options)}
        payload["conversation_pair"] = list(conversation_pair)
        payload["options"].update(target_language=None, recover_model_errors=False)

        def event(kind, value):
            if kind == "progress" and progress_callback:
                progress_callback(float(value))
            elif kind == "activity" and options.activity_callback:
                options.activity_callback(value)

        return self.call("transcribe", payload,
                         audio=np.asarray(source, dtype="<f4").tobytes() if array else None,
                         cancel_event=options.cancel_event, event=event)

    def close(self):
        self._closed = True
        process = self._process
        if process is not None and process.poll() is None:
            # Windows venv redirectors and frozen bootloaders can create an
            # extra process. Stop only descendants of our own Popen handle.
            import psutil
            try:
                children = psutil.Process(process.pid).children(recursive=True)
            except psutil.Error:
                children = []
            for child in reversed(children):
                try:
                    child.terminate()
                except psutil.Error:
                    pass
            try:
                process.terminate()
                process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1.5)
            except OSError:
                pass
            _, survivors = psutil.wait_procs(children, timeout=1.5)
            for child in survivors:
                try:
                    child.kill()
                except psutil.Error:
                    pass
        if self._connection is not None:
            self._connection.close()
        self._listener.close()
        # Accept may have finished just before close, without an RPC consuming it.
        try:
            pending = self._accepted.get_nowait()
            if not isinstance(pending, BaseException):
                pending.close()
        except queue.Empty:
            pass
        if self._temporary is not None:
            self._temporary.cleanup()


def _cpu_profile(values):
    from src.hardware import HardwareProfile
    profile = HardwareProfile(**values)
    for field in ("nvidia_detected", "ctranslate_cuda", "torch_cuda", "apple_silicon", "mlx_available", "torch_mps"):
        setattr(profile, field, False)
    profile.gpu_vram_gb = profile.reclaimable_vram_gb = 0
    profile.gpu_vram_free_gb = 0
    return profile


def run_worker(address):
    """Internal entrypoint, dispatched before creating a GUI or instance lock."""
    secret = os.environ.pop(AUTH_ENV, "")
    if not secret:
        return 2
    connection = Client(address, family="AF_PIPE" if os.name == "nt" else "AF_UNIX",
                        authkey=base64.b64decode(secret, validate=True))
    connection.send_bytes(_encode({"event": "identity", "value": os.getpid()}))
    import psutil
    # Watch both the owning app and any Windows launcher between app and worker.
    parents = [psutil.Process(int(os.environ.pop(PARENT_ENV))), psutil.Process(os.getppid())]

    def watch_parent():
        while True:
            time.sleep(2)
            if not all(parent.is_running() for parent in parents):
                os._exit(0)

    threading.Thread(target=watch_parent, daemon=True, name="cpu-worker-parent").start()
    engine = translator = None

    def emit(kind, value):
        connection.send_bytes(_encode({"event": kind, "value": value}))

    try:
        while True:
            request = json.loads(connection.recv_bytes(MAX_FRAME))
            audio = connection.recv_bytes(MAX_FRAME) if request.get("audio") else None
            payload = request["payload"]
            try:
                operation = request["operation"]
                if operation == "ping":
                    result = {"pid": os.getpid(), "cpu_only": os.environ.get("CUDA_VISIBLE_DEVICES") == ""}
                elif operation == "load_asr":
                    from dataclasses import asdict

                    from src.transcriber import TranscriberEngine, TranscriptionOptions
                    engine = TranscriberEngine(_cpu_profile(payload["hardware"]), isolated_cpu=False)
                    options = TranscriptionOptions(**payload["options"])
                    options.target_language = None
                    result = asdict(engine.load_model(payload["model"], "cpu-virtual",
                        lambda *values: emit("load_status", list(values)), options))
                elif operation == "transcribe":
                    import numpy as np

                    from src.transcriber import TranscriptionOptions
                    if engine is None:
                        raise RuntimeError("CPU speech model is not loaded")
                    options = TranscriptionOptions(**payload["options"])
                    options.activity_callback = lambda value: emit("activity", value)
                    from src.translation import ConversationRouter
                    pair = payload.get("conversation_pair", [])
                    engine.translator.router = ConversationRouter(pair[0], pair[1]) if len(pair) == 2 else None
                    source = np.frombuffer(audio, dtype="<f4").copy() if audio is not None else payload["source"]
                    result = engine._transcribe(source, options, lambda value: emit("progress", value))
                elif operation == "load_translation":
                    from src.translation import TranslationEngine
                    translator = TranslationEngine(payload.get("cache"), isolated_cpu=False)
                    translator.configure(payload["model"], payload.get("cache"))
                    translator.load(_cpu_profile(payload["hardware"]), allow_download=payload["allow_download"],
                                    allow_cpu_virtual_memory=True)
                    result = {"device": translator.device, "model": translator.model_id}
                elif operation == "translate":
                    if translator is None:
                        raise RuntimeError("CPU translation model is not loaded")
                    translator.glossary = payload.get("glossary", "")
                    text = translator.translate(payload["text"], payload["target"])
                    result = {"text": text, "index": translator.last_index}
                else:
                    raise ValueError("Unknown CPU operation")
                connection.send_bytes(_encode({"result": result}))
            except Exception as error:
                connection.send_bytes(_encode({"error": f"{type(error).__name__}: {error}"}))
    except (EOFError, OSError):
        return 0
    finally:
        connection.close()
