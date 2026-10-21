"""Live recording orchestration, separate from application layout."""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from src.audio import SAMPLE_RATE
from src.exports import write_bundle, write_export
from src.jobs import check_cancelled
from src.media import RecordingSpool, TransientSpool
from src.model_policy import conversation_model
from src.models import AUTO_MULTILINGUAL_MODEL_ID, get_model
from src.segments import shift_segments
from src.session import PreviewScheduler, SessionController

RED = "#F06878"

class RecordingMixin:
    def start_recording(self) -> None:
        if self.busy or self.recorder.recording or self.closing:
            return
        if not self._can_start_safely():
            return
        self.stop_speaking(resume=False)
        config = self.job_config()
        microphone = self.microphone_combo.get()
        try:
            device_index = int(microphone.split(":", 1)[0]) if ":" in microphone else None
        except ValueError:
            device_index = None
        self.session_controller = SessionController()
        self.session_controller.configure_languages(config.get("target_language") or self.translation_target, config.get("partner_language"), config.get("third_language"))
        self.current_session_base = None
        self.transcript_data = []
        self.recording_offset = 0.0
        prefix = "Conversation" if self.preset == "universal" else ("Conference" if self.preset == "conference" else "Dictation")
        self.active_recording_base = self._new_output_base(prefix)
        self.render_transcript()
        self._start_job(0)
        if not self._model_is_armed(config):
            self._show_recording_initialization()
        self.worker_thread = threading.Thread(
            target=self._recording_worker,
            args=(device_index, config),
            daemon=True,
            name="live-transcription",
        )
        self.worker_thread.start()

    def _recording_worker(self, device_index: int | None, config: dict[str, Any]) -> None:
        segments_all: list[dict[str, Any]] = []
        spool: RecordingSpool | None = None
        completed = False
        try:
            resolved = self.hardware.resolve_model(
                config["model"], config["device"], self.engine.cached_model_ids()
            )
            self._safe_ui(self._set_status, self.t("progress_loading", model=resolved))
            status = self.engine.load_model(
                config["model"], config["device"], self._engine_load_status, self.transcribe_options(config)
            )
            self.last_engine_status = status
            check_cancelled(self.cancel_event)
            spool = (TransientSpool() if config.get("private") else RecordingSpool(self.active_recording_base.with_suffix(".wav")))
            self.recording_spool = spool
            options = self.transcribe_options(config)
            self.engine.reset_translation_session(options)
            if config.get("conversation"):
                self.recorder.start(device_index, config["chunk"], smart_splits=True)
            else:
                self.recorder.start(device_index, config["chunk"])
            self._safe_ui(self._recording_started)
            scheduler = PreviewScheduler()
            generation = self.session_controller.generation
            while True:
                try:
                    audio = self.recorder.audio_queue.get(timeout=0.25)
                except queue.Empty:
                    if not self.recorder.recording and not self.recorder.segmenting:
                        break
                    if config.get("conversation") and self.recorder.recording and not self.recorder.paused:
                        self._try_provisional(options, scheduler)
                    continue
                if audio is None:
                    break
                generation, language_command = self.session_controller.language_command(generation)
                if language_command:
                    target, partner, third = language_command
                    options = replace(options, target_language=target, partner_language=partner, third_language=third)
                    self.engine.reset_translation_session(options)
                elif options.conversation and self.engine.translator.router is None:
                    self.engine.reset_translation_session(options)
                if config.get("conversation") and config["model"] == AUTO_MULTILINGUAL_MODEL_ID:
                    self._adapt_conversation_model(options)
                flattened = np.asarray(audio, dtype=np.float32).reshape(-1)
                self.last_audio = flattened.copy()
                spool.append(flattened)
                started = time.monotonic()
                result = self.engine.transcribe_audio(flattened, options)
                self._safe_ui(self.translation_controls.update_candidates, result.get("language_candidates") or
                              [{"language": result.get("language"), "probability": result.get("language_probability")}])
                self._live_cost = time.monotonic() - started
                scheduler.reset_turn()
                self._safe_ui(self._show_live_preview, "")
                segments = self._prepare_segments(result.get("segments", []), config["cleanup"])
                shifted = shift_segments(segments, self.recording_offset)
                for item in shifted:
                    if spool.path is not None:
                        item.update(audio_path=str(spool.path), audio_start=item["start"], audio_end=item["end"])
                    item["final_processing_seconds"] = self._live_cost
                segments_all.extend(shifted)
                self.recording_offset += flattened.size / SAMPLE_RATE
                if config.get("conversation"):
                    segments_all = self.engine.translator.complete_conversation(segments_all, self.cancel_event)
                    self._safe_ui(self._replace_segments, list(segments_all))
                    self._safe_ui(self.translation_controls.update_pair, result.get("conversation_pair", []))
                else:
                    self._safe_ui(self._append_segments, shifted)
                self._safe_ui(self._pipeline_activity, "waiting")
                segments_all = self.session_controller.snapshot(segments_all)
                # The worker owns this snapshot. It never depends on whether
                # the UI has already consumed its queued segment event.
                if not config.get("private"):
                    write_export(self.active_recording_base.with_suffix(".json"), segments_all)
                    write_export(self.active_recording_base.with_suffix(".txt"), segments_all, self.transcript_format_options())
                if self.recorder.capture_error:
                    raise RuntimeError(self.recorder.capture_error)
            spool.close()
            segments_all = self.session_controller.snapshot(segments_all)
            if config["speaker"] and segments_all:
                self._safe_ui(self._set_status, self.t("progress_diarizing"))
                segments_all = self.diarizer.process(str(spool.path), segments_all, callback=logging.info, cancel_event=self.cancel_event)
                self._safe_ui(self._replace_segments, segments_all)
            saved = self.save_result_bundle(
                segments_all,
                "Conversation" if config.get("conversation") else ("Conference" if self.preset == "conference" else "Dictation"),
                base_override=self.active_recording_base,
            )
            completed = True
            self._safe_ui(self._finish_recording, saved, (self.engine.current_status or status).backend)
        except Exception as error:
            logging.exception("Live transcription failed")
            self._safe_ui(self._fail_recording, error)
        finally:
            if spool is not None:
                try:
                    if not completed:
                        # Preserve captured backlog after an engine/device failure.
                        self.recorder.stop()
                        while True:
                            try:
                                pending = self.recorder.audio_queue.get_nowait()
                            except queue.Empty:
                                break
                            if pending is not None:
                                spool.append(pending)
                        if self.recorder.overflow_chunk is not None:
                            spool.append(self.recorder.overflow_chunk)
                except (OSError, RuntimeError):
                    logging.exception("Could not flush all pending audio; the existing WAV was preserved")
                finally:
                    spool.close()
                if completed and spool.path is not None and not config.get("keep_audio", True):
                    spool.path.unlink(missing_ok=True)
            self.recording_spool = None

    def _adapt_conversation_model(self, options):
        pair = self.engine.translator.router.pair if self.engine.translator.router else ()
        if len(pair) != 2:
            return
        cached = self.engine.cached_model_ids()
        candidate = conversation_model(pair[0], self.hardware, cached)
        if not all(get_model(candidate).supports(code, "transcribe") for code in pair):
            candidate = "omnilingual-1b-v2"
        if candidate in cached and candidate != self.engine.model_name:
            # Keep translation and routing resident; only replace ASR, between
            # turns. No new model download is initiated during capture.
            with self.engine._load_lock:
                status = self.engine._load_model_unlocked(candidate, "auto", self._engine_load_status,
                                                          replace(options, offline=True))
                self.last_engine_status = status

    def _try_provisional(self, options, scheduler):
        audio = self.recorder.preview_audio()
        seconds = audio.size / SAMPLE_RATE
        now = time.monotonic()
        if not scheduler.due(now, seconds, self.recorder.audio_queue.qsize()):
            return
        try:
            # Provisional text uses a cheap greedy pass. Final turns retain
            # the user's accuracy/beam settings and are always decoded again.
            result = self.engine.transcribe_audio(audio, replace(options, beam_size=1, target_language=None, conversation=False,
                third_language=None, overlap_separation=False, word_timestamps=False, original_callback=None,
                activity_callback=None, recover_model_errors=False))
            # A late provisional result never replaces an already-finalized turn.
            if self.recorder.audio_queue.empty() and self.recorder.available_seconds() >= seconds:
                self._safe_ui(self._show_live_preview, result.get("text", ""), result.get("language") or "")
        except Exception:
            logging.warning("Provisional recognition unavailable; final audio remains queued")
        finally:
            scheduler.completed(time.monotonic(), seconds, time.monotonic() - now)

    def _recording_started(self) -> None:
        self.busy = False
        self._hide_recording_initialization()
        self._set_status(self.t("progress_recording"))
        self.record_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.stop_button.configure(
            state="normal",
            text=self.t("stop_recording"),
            fg_color=RED,
            hover_color="#FF8290",
            border_width=2,
            border_color="#FFD7DC",
        )
        self._set_source_buttons_state("disabled")
        self._pipeline_activity("waiting")

    def toggle_pause(self) -> None:
        self.stop_speaking(resume=False)
        if not self.recorder.recording:
            return
        if self.recorder.paused:
            self.recorder.resume()
            self.pause_button.configure(text=self.t("pause"))
            self._set_status(self.t("progress_recording"))
        else:
            self.recorder.pause()
            self.pause_button.configure(text=self.t("resume"))
            self._set_status(self.t("cancelled"))

    def stop_recording(self) -> None:
        self.stop_speaking(resume=False)
        if not self.recorder.recording:
            return
        self.recorder.stop()
        self.busy = True
        self.pause_button.configure(state="disabled")
        self.stop_button.configure(state="disabled", text=self.t("processing"))
        self._set_status(self.t("processing"))

    def _finish_recording(self, saved: Path | None, backend: str) -> None:
        self._hide_recording_initialization()
        # Completion runs after queued segment callbacks on the UI thread.
        # Commit the latest review overlays once more, so an edit made while
        # stopping cannot be replaced by the worker's earlier export snapshot.
        if self.active_recording_base is not None and not self.private_mode:
            latest = self.session_controller.snapshot(self.transcript_data)
            write_bundle(self.active_recording_base, latest, self.transcript_format_options())
        self.active_recording_base = None
        self.record_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text=self.t("pause"))
        self.stop_button.configure(
            state="disabled",
            text=self.t("stop"),
            fg_color="#60708A",
            border_width=0,
        )
        self._finish_job(saved, backend)
        self.after(250, self._start_microphone_monitor)

    def _fail_recording(self, error: Exception) -> None:
        self._hide_recording_initialization()
        self._save_backup()
        self.active_recording_base = None
        try:
            self.recorder.stop()
        except Exception:
            pass
        self.record_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.stop_button.configure(
            state="disabled",
            text=self.t("stop"),
            fg_color="#60708A",
            border_width=0,
        )
        self._fail_job(error)
        self.after(250, self._start_microphone_monitor)
