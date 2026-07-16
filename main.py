import argparse
import json
import logging
import os
import platform
import sys
from pathlib import Path

import certifi

from src.utils import setup_logging

# --- Fix 0: macOS Finder Crash Fix (Redirect Stdout/Stderr) ---
# GUI apps launched from Finder have no stdout/stderr. Writing to them causes a crash.
if getattr(sys, "frozen", False) and platform.system() == "Darwin":
    log_dir = os.path.join(os.path.expanduser("~"), "Library", "Logs", "LocalTranscriberPro")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Redirect stdout/stderr to a log file
    log_file = os.path.join(log_dir, "app_debug.log")
    sys.stdout = open(log_file, "w")
    sys.stderr = sys.stdout

# Use a current CA bundle. TLS verification is intentionally never disabled.
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# --- Fix 2: macOS Environment (PATH for FFmpeg) ---
if platform.system() == "Darwin":
    # Finder launch doesn't inherit .zshrc/.bashrc PATH.
    # We must explicitly add Homebrew paths to find ffmpeg.
    homebrew_paths = [
        "/opt/homebrew/bin",  # Apple Silicon
        "/usr/local/bin",  # Intel
        os.path.expanduser("~/bin"),
    ]

    current_path = os.environ.get("PATH", "")
    new_paths = []
    for p in homebrew_paths:
        if p not in current_path and os.path.exists(p):
            new_paths.append(p)

    if new_paths:
        # Prepend to ensure we find our tools first
        os.environ["PATH"] = ":".join(new_paths) + ":" + current_path

if platform.system() == "Windows":
    # Keep text and controls crisp on high-DPI displays.
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass

def run_packaged_smoke_test(args: argparse.Namespace) -> int:
    """Exercise the frozen inference stack without opening the interface."""
    from src.diarizer import Diarizer
    from src.hardware import detect_hardware
    from src.transcriber import TranscriberEngine, TranscriptionOptions

    payload: dict[str, object] = {"success": False}
    try:
        hardware = detect_hardware()
        engine = TranscriberEngine(hardware)
        status = engine.load_model(args.model, args.device)
        progress: list[float] = []
        result = engine.transcribe_file(
            args.smoke_test,
            TranscriptionOptions(language=args.language, beam_size=5, vad_filter=True),
            progress.append,
        )
        if args.diarize:
            result["segments"] = Diarizer().process(args.smoke_test, result.get("segments", []))
        payload = {
            "success": bool(result.get("text", "").strip()),
            "hardware": hardware.as_dict(),
            "status": status.__dict__,
            "text": result.get("text", ""),
            "segments": result.get("segments", []),
            "language": result.get("language"),
            "duration": result.get("duration"),
            "processing_seconds": result.get("processing_seconds"),
            "progress_completed": bool(progress and progress[-1] == 1.0),
        }
    except Exception as exc:  # The JSON report is the frozen-app diagnostic surface.
        payload["error"] = f"{type(exc).__name__}: {exc}"
    output = Path(args.diagnostic_output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if payload.get("success") else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--smoke-test")
    parser.add_argument("--diagnostic-output")
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--language", default=None)
    parser.add_argument("--diarize", action="store_true")
    args, _ = parser.parse_known_args()
    if args.smoke_test and not args.diagnostic_output:
        parser.error("--diagnostic-output is required with --smoke-test")
    return args


def main() -> int:
    setup_logging()
    args = parse_args()
    if args.smoke_test:
        return run_packaged_smoke_test(args)

    # This module only uses the Python standard library, so it can paint a
    # responsive window before importing the much larger AI and GUI stacks.
    from src.startup import (
        SingleInstanceLock,
        StartupSplash,
        notify_already_running,
        notify_startup_error,
    )

    instance = SingleInstanceLock()
    if not instance.acquire():
        notify_already_running()
        return 0

    try:
        splash = StartupSplash()

        def prepare(report):
            report("libraries", 0.14)
            from src.hardware import detect_hardware

            hardware = detect_hardware(report)
            report("interface", 0.78)
            from src.gui import TranscriberApp

            report("ready", 0.98)
            return hardware, TranscriberApp

        try:
            hardware, app_class = splash.run(prepare)
            app = app_class(hardware=hardware)
            app.mainloop()
            return 0
        except Exception as error:
            logging.exception("Application startup failed")
            notify_startup_error(error)
            return 1
    finally:
        instance.release()


if __name__ == "__main__":
    raise SystemExit(main())
