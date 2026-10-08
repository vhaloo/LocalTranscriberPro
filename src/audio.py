import logging
import queue
import threading

import numpy as np
import sounddevice as sd

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1


class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.paused = False
        self.audio_queue = queue.Queue(maxsize=128)
        self.stream = None
        self.monitor_stream = None
        self.monitoring = False
        self.monitor_device_index = None
        self.monitor_error = ""
        self.device_index = None
        self.audio_buffer = []
        self.buffer_sample_count = 0
        self.chunk_duration_samples = 0
        self.capture_error = ""
        self.overflow_chunk = None
        self.smart_splits = False
        self.segmenting = False
        self.segmenter = None
        self.segment_thread = None
        self.raw_queue = queue.Queue(maxsize=128)
        self.raw_overflow = None
        self.segment_stop = threading.Event()
        self.segment_snapshot = {}
        self.lock = threading.Lock()
        self.visual_lock = threading.Lock()

        # Visualizer Data
        self.current_amplitude = 0.0
        self.wave_data = np.zeros(50, dtype=np.float32)  # Last 50 samples for graph

    def get_devices(self):
        """Returns a list of input devices."""
        try:
            devices = sd.query_devices()
            input_devices = []
            default_idx = sd.default.device[0]
            sel = None
            for i, d in enumerate(devices):
                if d["max_input_channels"] > 0:
                    name = f"{i}: {d['name']}"
                    input_devices.append(name)
                    if i == default_idx:
                        sel = name
            return input_devices, sel
        except Exception as e:
            logging.error(f"Failed to query devices: {e}")
            return [], None

    def start(self, device_index, chunk_duration, smart_splits=False):
        logging.info(f"Starting recorder on device {device_index} with chunk {chunk_duration}s")
        if self.recording:
            raise RuntimeError("Recorder is already running")
        if chunk_duration <= 0:
            raise ValueError("Chunk duration must be positive")
        self.stop_monitor()
        self.device_index = device_index
        self.chunk_duration_samples = int(SAMPLE_RATE * chunk_duration)
        self.audio_buffer = []
        self.buffer_sample_count = 0
        # A previous recording can leave a sentinel or unprocessed audio in the
        # queue. Every session must start from a clean boundary.
        self.audio_queue = queue.Queue(maxsize=128)
        self.recording = True
        self.capture_error = ""
        self.overflow_chunk = None
        self.smart_splits = smart_splits
        self.segment_snapshot = {}
        if smart_splits:
            from src.speech_boundary import SpeechSegmenter, StreamingVoiceDetector

            try:
                self.segmenter = SpeechSegmenter(StreamingVoiceDetector(), maximum_seconds=chunk_duration)
            except Exception:
                self.recording = False
                raise
            self.raw_queue = queue.Queue(maxsize=128)
            self.raw_overflow = None
            self.segment_stop.clear()
            self.segmenting = True
            self.segment_thread = threading.Thread(target=self._segment_audio, daemon=True, name="speech-boundaries")
            self.segment_thread.start()
        self.paused = False
        self._clear_visuals()

        try:
            self.stream = sd.InputStream(
                device=self.device_index,
                channels=CHANNELS,
                samplerate=SAMPLE_RATE,
                callback=self.audio_callback,
                blocksize=1024,  # Smaller blocksize for faster UI updates
            )
            self.stream.start()
            logging.info("Stream started successfully")
        except Exception as e:
            self.recording = False
            self.segment_stop.set()
            if self.segment_thread:
                self.segment_thread.join(timeout=5)
            if self.stream is not None:
                self.stream.close()
                self.stream = None
            logging.error(f"Error starting stream: {e}")
            raise

    def audio_callback(self, indata, frames, time, status):
        if status:
            # PortAudio drops samples on overflow. Surface it in diagnostics.
            logging.warning("Microphone capture status: %s", status)

        if self.recording and not self.paused:
            self._update_visuals(indata, frames)

            if self.smart_splits:
                # PortAudio only copies/enqueues. Neural VAD runs in its own
                # CPU thread and cannot block microphone delivery.
                try:
                    self.raw_queue.put_nowait(indata.copy())
                except queue.Full:
                    self.raw_overflow = indata.copy()
                    self.capture_error = "Speech segmentation could not keep up. Captured audio was preserved."
                    self.recording = False
                    self.segment_stop.set()
                return

            with self.lock:
                self.audio_buffer.append(indata.copy())
                self.buffer_sample_count += frames

                if self.buffer_sample_count >= self.chunk_duration_samples:
                    full_data = np.concatenate(self.audio_buffer)
                    chunk = full_data[: self.chunk_duration_samples]
                    remainder = full_data[self.chunk_duration_samples :]
                    try:
                        self.audio_queue.put_nowait(chunk)
                    except queue.Full:
                        self.overflow_chunk = chunk
                        self.capture_error = "The transcription engine cannot keep up with the microphone. Captured audio was preserved."
                        self.recording = False
                    self.audio_buffer = [remainder] if len(remainder) > 0 else []
                    self.buffer_sample_count = len(remainder)

    def pause(self):
        self.paused = True
        self._clear_visuals()
        if self.smart_splits:
            # A marker flushes the current phrase before the pause; it is not
            # audio and never changes the duration of the retained WAV.
            try:
                self.raw_queue.put_nowait(None)
            except queue.Full:
                pass

    def resume(self):
        self.paused = False

    def stop(self):
        if not self.recording and self.stream is None and not self.audio_buffer and not self.segmenting:
            return
        self.recording = False
        self._clear_visuals()
        if self.stream:
            stream, self.stream = self.stream, None
            try:
                stream.stop()
            finally:
                stream.close()

        if self.smart_splits:
            self.segment_stop.set()
            if self.segment_thread:
                self.segment_thread.join(timeout=5)
            if self.segmenting:
                raise RuntimeError("Speech segmentation is still finishing; captured audio remains in memory")

        with self.lock:
            if self.audio_buffer:
                remaining_data = np.concatenate(self.audio_buffer)
                if len(remaining_data) > 0:
                    try:
                        self.audio_queue.put_nowait(remaining_data)
                    except queue.Full:
                        self.overflow_chunk = (remaining_data if self.overflow_chunk is None else
                                               np.concatenate((self.overflow_chunk, remaining_data)))
                self.audio_buffer = []
                self.buffer_sample_count = 0

    def available_seconds(self):
        if self.smart_splits:
            return self.segment_snapshot.get("seconds", 0.0)
        with self.lock:
            return self.buffer_sample_count / SAMPLE_RATE

    def _queue_segment(self, audio):
        if audio.size == 0:
            return
        if self.overflow_chunk is None:
            try:
                self.audio_queue.put_nowait(audio)
                return
            except queue.Full:
                self.capture_error = "The transcription engine cannot keep up with the microphone. Captured audio was preserved."
                self.recording = False
                self.segment_stop.set()
        self.overflow_chunk = audio if self.overflow_chunk is None else np.concatenate((self.overflow_chunk, audio))

    def _segment_audio(self):
        try:
            while not self.segment_stop.is_set() or not self.raw_queue.empty():
                try:
                    block = self.raw_queue.get(timeout=0.05)
                except queue.Empty:
                    continue
                if block is None:
                    self._queue_segment(self.segmenter.finish())
                else:
                    for chunk in self.segmenter.feed(block):
                        self._queue_segment(chunk)
                    if self.segmenter.detector_error:
                        self.capture_error = f"Speech boundary detection failed: {self.segmenter.detector_error}"
                        self.recording = False
                        self.segment_stop.set()
                self.segment_snapshot = self.segmenter.snapshot()
            if self.raw_overflow is not None:
                for chunk in self.segmenter.feed(self.raw_overflow):
                    self._queue_segment(chunk)
                self.raw_overflow = None
            self._queue_segment(self.segmenter.finish())
        except Exception as error:
            logging.exception("Streaming speech boundary detection failed")
            self.capture_error = f"Speech boundary detection failed: {error}"
            self.recording = False
            # VAD is auxiliary: retain unprocessed samples for WAV recovery.
            self._queue_segment(self.segmenter.finish())
            while not self.raw_queue.empty():
                pending = self.raw_queue.get_nowait()
                if pending is not None:
                    self._queue_segment(np.asarray(pending).reshape(-1))
            if self.raw_overflow is not None:
                self._queue_segment(np.asarray(self.raw_overflow).reshape(-1))
                self.raw_overflow = None
        finally:
            self.segmenting = False

    def sampling_state(self):
        snapshot = dict(self.segment_snapshot) if self.smart_splits else {
            "state": "listening", "seconds": self.available_seconds(),
            "maximum_seconds": self.chunk_duration_samples / SAMPLE_RATE if self.chunk_duration_samples else 30,
            "silence": 0.0,
        }
        return dict(snapshot, pending=self.audio_queue.qsize(), paused=self.paused)

    def start_monitor(self, device_index=None) -> bool:
        """Open a lightweight level-only stream when not recording."""
        if self.recording:
            return False
        if self.monitoring and self.monitor_device_index == device_index and self.monitor_stream:
            return True
        self.stop_monitor()
        self.monitor_device_index = device_index
        self.monitor_error = ""
        try:
            self.monitor_stream = sd.InputStream(
                device=device_index,
                channels=CHANNELS,
                samplerate=SAMPLE_RATE,
                callback=self._monitor_callback,
                blocksize=512,
            )
            self.monitor_stream.start()
            self.monitoring = True
            logging.info("Microphone level monitor started on device %s", device_index)
            return True
        except Exception as error:
            self.monitor_stream = None
            self.monitoring = False
            self.monitor_error = str(error)
            self._clear_visuals()
            logging.warning("Microphone level monitor could not start: %s", error)
            return False

    def stop_monitor(self) -> None:
        stream = self.monitor_stream
        self.monitor_stream = None
        self.monitoring = False
        if stream:
            try:
                stream.stop()
                stream.close()
            except Exception:
                logging.exception("Could not close microphone level monitor")
        self._clear_visuals()

    def _monitor_callback(self, indata, frames, time, status) -> None:
        if self.monitoring:
            self._update_visuals(indata, frames)

    def _update_visuals(self, indata, frames: int) -> None:
        try:
            values = np.asarray(indata, dtype=np.float32)
            if values.ndim > 1:
                values = values[:, 0]
            rms = float(np.sqrt(np.mean(np.square(values)))) if values.size else 0.0
            amplitude = min(rms * 6.0, 1.0)
            step = max(1, values.size // 50)
            downsampled = values[::step][:50]
            if downsampled.size < 50:
                downsampled = np.pad(downsampled, (0, 50 - downsampled.size))
            with self.visual_lock:
                self.current_amplitude = amplitude
                self.wave_data = np.asarray(downsampled, dtype=np.float32)
        except (ValueError, TypeError, FloatingPointError):
            pass

    def _clear_visuals(self) -> None:
        with self.visual_lock:
            self.current_amplitude = 0.0
            self.wave_data = np.zeros(50, dtype=np.float32)

    def get_visual_state(self) -> tuple[float, np.ndarray]:
        with self.visual_lock:
            return float(self.current_amplitude), self.wave_data.copy()
