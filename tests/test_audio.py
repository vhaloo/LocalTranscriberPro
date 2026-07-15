from types import SimpleNamespace

import numpy as np

from src.audio import AudioRecorder


class FakeInputStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False
        self.closed = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def close(self):
        self.closed = True


def test_level_monitor_updates_visuals_without_recording(monkeypatch):
    created = []

    def make_stream(**kwargs):
        stream = FakeInputStream(**kwargs)
        created.append(stream)
        return stream

    monkeypatch.setattr("src.audio.sd", SimpleNamespace(InputStream=make_stream))
    recorder = AudioRecorder()

    assert recorder.start_monitor(7)
    signal = np.full((512, 1), 0.1, dtype=np.float32)
    created[0].kwargs["callback"](signal, len(signal), None, None)

    amplitude, waveform = recorder.get_visual_state()
    assert recorder.monitoring
    assert amplitude > 0
    assert waveform.shape == (50,)
    assert recorder.audio_queue.empty()

    recorder.stop_monitor()
    assert created[0].closed
    assert not recorder.monitoring
    assert recorder.get_visual_state()[0] == 0


def test_level_monitor_reports_device_errors(monkeypatch):
    def fail_stream(**_kwargs):
        raise RuntimeError("microphone denied")

    monkeypatch.setattr("src.audio.sd", SimpleNamespace(InputStream=fail_stream))
    recorder = AudioRecorder()

    assert not recorder.start_monitor()
    assert "denied" in recorder.monitor_error
    assert not recorder.monitoring
