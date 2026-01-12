import sounddevice as sd
import numpy as np
import threading
import queue
import logging

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1

class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.paused = False
        self.audio_queue = queue.Queue()
        self.stream = None
        self.device_index = None
        self.audio_buffer = []
        self.buffer_sample_count = 0
        self.chunk_duration_samples = 0
        self.lock = threading.Lock()
        
        # Visualizer Data
        self.current_amplitude = 0.0
        self.wave_data = np.zeros(50, dtype=np.float32) # Last 50 samples for graph

    def get_devices(self):
        """Returns a list of input devices."""
        try:
            devices = sd.query_devices()
            input_devices = []
            default_idx = sd.default.device[0]
            sel = None
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    name = f"{i}: {d['name']}"
                    input_devices.append(name)
                    if i == default_idx: sel = name
            return input_devices, sel
        except Exception as e:
            logging.error(f"Failed to query devices: {e}")
            return [], None

    def start(self, device_index, chunk_duration):
        logging.info(f"Starting recorder on device {device_index} with chunk {chunk_duration}s")
        self.device_index = device_index
        self.chunk_duration_samples = int(SAMPLE_RATE * chunk_duration)
        self.audio_buffer = []
        self.buffer_sample_count = 0
        self.recording = True
        self.paused = False
        self.current_amplitude = 0.0
        self.wave_data = np.zeros(50, dtype=np.float32)
        
        try:
            self.stream = sd.InputStream(
                device=self.device_index,
                channels=CHANNELS,
                samplerate=SAMPLE_RATE,
                callback=self.audio_callback,
                blocksize=1024 # Smaller blocksize for faster UI updates
            )
            self.stream.start()
            logging.info("Stream started successfully")
        except Exception as e:
            logging.error(f"Error starting stream: {e}")
            raise

    def audio_callback(self, indata, frames, time, status):
        if status:
            pass # Ignore overflows for UI smoothness
        
        if self.recording and not self.paused:
            # Visualizer Data
            try:
                # 1. Amplitude (RMS)
                vol = np.linalg.norm(indata) / np.sqrt(frames)
                self.current_amplitude = min(vol * 5, 1.0)
                
                # 2. Waveform (Downsample for UI)
                # Take every Nth sample to fit 50 points
                step = max(1, len(indata) // 50)
                downsampled = indata[::step, 0][:50]
                # Pad if too short
                if len(downsampled) < 50:
                    downsampled = np.pad(downsampled, (0, 50-len(downsampled)))
                self.wave_data = downsampled
            except: pass

            with self.lock:
                self.audio_buffer.append(indata.copy())
                self.buffer_sample_count += frames
                
                if self.buffer_sample_count >= self.chunk_duration_samples:
                    full_data = np.concatenate(self.audio_buffer)
                    chunk = full_data[:self.chunk_duration_samples]
                    remainder = full_data[self.chunk_duration_samples:]
                    self.audio_queue.put(chunk)
                    self.audio_buffer = [remainder] if len(remainder) > 0 else []
                    self.buffer_sample_count = len(remainder)

    def pause(self):
        self.paused = True
        self.current_amplitude = 0.0
        self.wave_data = np.zeros(50)

    def resume(self):
        self.paused = False

    def stop(self):
        self.recording = False
        self.current_amplitude = 0.0
        self.wave_data = np.zeros(50)
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
