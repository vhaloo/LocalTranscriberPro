import argparse
import json
import logging
import os
import platform
import sys
from pathlib import Path

import certifi

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

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
        source = args.smoke_test
        if args.youtube_test:
            from src.youtube_utils import download_youtube_audio

            source = download_youtube_audio(args.youtube_test, Path(args.diagnostic_output).resolve().parent / "youtube-qa")
        hardware = detect_hardware()
        engine = TranscriberEngine(hardware)
        options = TranscriptionOptions(language=args.language, task=args.task, beam_size=5, vad_filter=True,
                                       target_language=args.target_language, conversation=args.conversation,
                                       partner_language=args.partner_language, third_language=args.third_language,
                                       offline=args.offline, overlap_separation=args.overlap)
        engine.load_model(args.model, args.device, options=options)
        engine.reset_translation_session(options)
        progress: list[float] = []
        result = engine.transcribe_file(
            source,
            options,
            progress.append,
        )
        if args.diarize:
            result["segments"] = Diarizer().process(source, result.get("segments", []))
        payload = {
            "success": not bool(result.get("text", "").strip()) if args.expect_silence else bool(result.get("text", "").strip()),
            "hardware": hardware.as_dict(),
            "status": engine.current_status.__dict__,
            "text": result.get("text", ""),
            "segments": result.get("segments", []),
            "language": result.get("language"),
            "duration": result.get("duration"),
            "processing_seconds": result.get("processing_seconds"),
            "translation_device": result.get("translation_device"),
            "conversation_pair": result.get("conversation_pair", []),
            "progress_completed": bool(progress and progress[-1] == 1.0),
        }
    except Exception as exc:  # The JSON report is the frozen-app diagnostic surface.
        payload["error"] = f"{type(exc).__name__}: {exc}"
    output = Path(args.diagnostic_output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if payload.get("success") else 2


def run_voice_smoke_test(args: argparse.Namespace) -> int:
    import numpy as np
    import soundfile as sf

    from src.speech_output import LocalSpeechOutput

    output = Path(args.diagnostic_output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"success": False, "language": args.voice_test}
    try:
        audio, rate = LocalSpeechOutput().synthesize(
            args.voice_text, args.voice_test, allow_download=not args.offline)
        payload.update(success=bool(len(audio) and np.isfinite(audio).all() and np.max(np.abs(audio)) > 0),
                       sample_rate=rate, samples=len(audio), duration=len(audio) / rate)
        sf.write(str(output.with_suffix(".wav")), audio, rate)
    except Exception as error:
        payload["error"] = f"{type(error).__name__}: {error}"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if payload["success"] else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--smoke-test")
    parser.add_argument("--youtube-test")
    parser.add_argument("--diagnostic-output")
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--language", default=None)
    parser.add_argument("--task", choices=("transcribe", "translate"), default="transcribe")
    parser.add_argument("--target-language")
    parser.add_argument("--conversation", action="store_true")
    parser.add_argument("--partner-language")
    parser.add_argument("--third-language")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--overlap", action="store_true")
    parser.add_argument("--voice-test")
    parser.add_argument("--voice-text", default="Bonjour. Hello.")
    parser.add_argument("--expect-silence", action="store_true")
    parser.add_argument("--diarize", action="store_true")
    args, _ = parser.parse_known_args()
    if (args.smoke_test or args.youtube_test or args.voice_test) and not args.diagnostic_output:
        parser.error("--diagnostic-output is required with --smoke-test")
    return args


def main() -> int:
    setup_logging()
    args = parse_args()
    if args.voice_test:
        return run_voice_smoke_test(args)
    if args.smoke_test or args.youtube_test:
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
            report("preloading_model", 0.76)
            from src.transcriber import TranscriberEngine

            engine = TranscriberEngine(hardware)
            preloaded_status = None
            # Downloads and model initialization belong to the cancellable,
            # visible desktop workflow, never to an uncloseable startup screen.

            report("interface", 0.92)
            from src.gui import TranscriberApp

            report("ready", 0.98)
            return hardware, engine, preloaded_status, TranscriberApp

        try:
            hardware, engine, preloaded_status, app_class = splash.run(prepare)
            app = app_class(
                hardware=hardware,
                engine=engine,
                preloaded_status=preloaded_status,
            )
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
