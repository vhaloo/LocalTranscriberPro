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
        self.audio_queue = queue.Queue()
        self.stream = None
        self.monitor_stream = None
        self.monitoring = False
        self.monitor_device_index = None
        self.monitor_error = ""
        self.device_index = None
        self.audio_buffer = []
        self.buffer_sample_count = 0
        self.chunk_duration_samples = 0
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

    def start(self, device_index, chunk_duration):
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
        self.audio_queue = queue.Queue()
        self.recording = True
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
            logging.error(f"Error starting stream: {e}")
            raise

    def audio_callback(self, indata, frames, time, status):
        if status:
            pass  # Ignore overflows for UI smoothness

        if self.recording and not self.paused:
            self._update_visuals(indata, frames)

            with self.lock:
                self.audio_buffer.append(indata.copy())
                self.buffer_sample_count += frames

                if self.buffer_sample_count >= self.chunk_duration_samples:
                    full_data = np.concatenate(self.audio_buffer)
                    chunk = full_data[: self.chunk_duration_samples]
                    remainder = full_data[self.chunk_duration_samples :]
                    self.audio_queue.put(chunk)
                    self.audio_buffer = [remainder] if len(remainder) > 0 else []
                    self.buffer_sample_count = len(remainder)

    def pause(self):
        self.paused = True
        self._clear_visuals()

    def resume(self):
        self.paused = False

    def stop(self):
        if not self.recording and self.stream is None:
            return
        self.recording = False
        self._clear_visuals()
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        with self.lock:
            if self.audio_buffer:
                remaining_data = np.concatenate(self.audio_buffer)
                if len(remaining_data) > int(SAMPLE_RATE * 0.1):
                    self.audio_queue.put(remaining_data)
                self.audio_buffer = []
                self.buffer_sample_count = 0

    def available_seconds(self):
        with self.lock:
            return self.buffer_sample_count / SAMPLE_RATE

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
