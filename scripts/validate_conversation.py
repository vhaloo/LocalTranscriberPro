"""Exercise the real recorder/VAD/live worker with controlled, local audio.

Replaces only the microphone stream: no ambient sound is captured or played.
The selected recognizer, provisional inference, MT, turn boundaries and local
voices are genuine. Public test audio stays outside the source distribution.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.audio import AudioRecorder  # noqa: E402
from src.hardware import detect_hardware  # noqa: E402
from src.media import iter_audio_chunks  # noqa: E402
from src.recording_ui import RecordingMixin  # noqa: E402
from src.session import SessionController, identified  # noqa: E402
from src.speech_output import LocalSpeechOutput  # noqa: E402
from src.transcriber import TranscriberEngine, TranscriptionOptions  # noqa: E402


class Harness(RecordingMixin):
    def __init__(self, audio, model, device):
        self.audio = audio
        self.hardware = detect_hardware()
        self.engine = TranscriberEngine(self.hardware)
        self.recorder = AudioRecorder()
        self.session_controller = SessionController()
        self.session_controller.configure_languages("fr")
        self.cancel_event = threading.Event()
        self.active_recording_base = None
        self.recording_offset = 0.0
        self.preset = "universal"
        self.private_mode = True
        self.previews, self.pairs, self.results = [], [], []
        self.error, self.finished = None, False
        self.decode_trace = []
        transcribe = self.engine.transcribe_audio
        def trace(audio, options):
            started = time.monotonic()
            result = transcribe(audio, options)
            self.decode_trace.append({"provisional": options.target_language is None,
                "input_seconds": len(audio) / 16000, "seconds": round(time.monotonic() - started, 3),
                "result_characters": len(result.get("text", "")), "pending": self.recorder.audio_queue.qsize(),
                "available_seconds_at_return": self.recorder.available_seconds()})
            return result
        self.engine.transcribe_audio = trace
        self.translation_controls = SimpleNamespace(update_candidates=lambda _: None,
            update_pair=lambda pair: self.pairs.append(pair))
        self.options = TranscriptionOptions(target_language="fr", conversation=True, third_language="en",
            offline=True, word_timestamps=False, recover_model_errors=True)
        self.config = dict(model=model, device=device, private=True, conversation=True,
            chunk=12, cleanup=False, speaker=False, keep_audio=False)

    def transcribe_options(self, _config):
        return self.options

    def t(self, key, **_kwargs):
        return key

    def _safe_ui(self, callback, *args):
        callback(*args)

    def _set_status(self, _text):
        pass

    def _engine_load_status(self, *_args):
        pass

    def _recording_started(self):
        pass

    def _show_live_preview(self, text, language=""):
        if text.strip():
            self.previews.append({"characters": len(text), "language": language})

    def _pipeline_activity(self, _stage):
        pass

    def _replace_segments(self, _segments):
        pass

    def _prepare_segments(self, segments, _cleanup):
        return identified(segments)

    def save_result_bundle(self, segments, *_args, **_kwargs):
        self.results = segments
        return None

    def _finish_recording(self, _saved, _backend):
        self.finished = True

    def _fail_recording(self, error):
        self.error = error

    def run(self):
        owner = self
        class ControlledStream:
            def __init__(self, **kwargs):
                self.callback = kwargs["callback"]

            def start(self):
                def feed():
                    for offset in range(0, owner.audio.size, 1024):
                        block = owner.audio[offset:offset + 1024, None]
                        self.callback(block, len(block), None, False)
                        time.sleep(len(block) / 16000)
                    owner.recorder.stop()
                self.thread = threading.Thread(target=feed, name="controlled-audio", daemon=True)
                self.thread.start()

            def stop(self):
                pass

            def close(self):
                pass

        with patch("src.audio.sd.InputStream", ControlledStream):
            self._recording_worker(None, self.config)
        if self.error:
            raise self.error
        assert self.finished and self.results, "Live worker produced no final conversation"
        assert self.recorder.capture_error == "", self.recorder.capture_error
        assert self.previews, "No provisional inference reached the live display"
        assert abs(self.recording_offset - self.audio.size / 16000) < 1 / 16000, "Lost audio samples"
        assert all(item.get("segment_id") for item in self.results)
        assert {item.get("source_language") for item in self.results} >= {"ar", "fr"}
        assert any(set(pair) == {"ar", "fr"} for pair in self.pairs), self.pairs
        assert all(item.get("text") and item.get("third_text") for item in self.results)
        assert not any(item.get("translation_pending") for item in self.results)
        assert self.recorder.audio_queue.empty() or all(item is None for item in self.recorder.audio_queue.queue)
        return {"success": True, "status": self.engine.current_status.__dict__,
            "input_seconds": self.audio.size / 16000, "finalized_seconds": self.recording_offset,
            "previews": self.previews, "turns": len(self.results), "pairs": self.pairs,
            "languages": sorted({item["source_language"] for item in self.results}),
            "destinations": sorted({item["target_language"] for item in self.results}),
            "third_language": "en", "microphone_captured": False, "network_blocked": True,
            "audio_saved": False, "translation_device": self.engine.translator.device, "decode_trace": self.decode_trace}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arabic", required=True, type=Path)
    parser.add_argument("--model", default="qwen3-asr-0.6b")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    connect = socket.socket.connect
    socket.socket.connect = lambda *_: (_ for _ in ()).throw(RuntimeError("Network prohibited during validation"))
    started = time.monotonic()
    harness = None
    try:
        voice, rate = LocalSpeechOutput().synthesize(
            "Nous allons chercher ensemble un logement disponible et vérifier les documents nécessaires pour votre rendez-vous de demain matin à neuf heures.",
            "fr", allow_download=False)
        french = resample_poly(voice, 16000, rate).astype("float32")
        arabic = np.concatenate([audio for _, audio in iter_audio_chunks(str(args.arabic))])
        silence = np.zeros(16000, dtype="float32")
        audio = np.concatenate([french, silence, arabic, silence, french, silence])
        harness = Harness(audio, args.model, args.device)
        result = harness.run()
        result["local_voice_synthesis"] = True
    except Exception as error:
        result = {"success": False, "error": f"{type(error).__name__}: {error}"}
        if harness is not None:
            result.update(decode_trace=harness.decode_trace, previews=harness.previews,
                          final_turns=len(harness.results), pairs=harness.pairs)
    finally:
        socket.socket.connect = connect
    result["elapsed_seconds"] = round(time.monotonic() - started, 2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["success"] else 1)
