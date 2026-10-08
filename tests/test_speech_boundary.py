import queue
from types import SimpleNamespace

import numpy as np

from src.audio import AudioRecorder
from src.speech_boundary import FRAME, SpeechSegmenter


def detector(frame):
    return 1.0 if float(np.mean(frame)) > 0.1 else 0.0


def test_end_of_turn_triggers_early_and_preserves_every_sample():
    segmenter = SpeechSegmenter(detector)
    source = np.concatenate((np.ones(FRAME * 32), np.zeros(FRAME * 24), np.ones(123))).astype("float32")
    chunks = []
    for start in range(0, source.size, 1024):
        chunks.extend(segmenter.feed(source[start:start + 1024]))
    assert len(chunks) == 1
    assert 1.7 < chunks[0].size / 16000 < 2
    np.testing.assert_array_equal(np.concatenate([*chunks, segmenter.finish()]), source)


def test_short_hesitation_does_not_split_but_long_speech_is_bounded():
    segmenter = SpeechSegmenter(detector, maximum_seconds=3)
    source = np.concatenate((np.ones(FRAME * 32), np.zeros(FRAME * 8), np.ones(FRAME * 80)))
    chunks = segmenter.feed(source)
    assert len(chunks) == 1
    assert chunks[0].size <= 3 * 16000 + FRAME
    np.testing.assert_array_equal(np.concatenate([*chunks, segmenter.finish()]), source)


def test_silence_alone_is_bounded_and_never_lost():
    segmenter = SpeechSegmenter(detector, maximum_seconds=2)
    source = np.zeros(70000, dtype="float32")
    chunks = segmenter.feed(source)
    assert len(chunks) == 2
    np.testing.assert_array_equal(np.concatenate([*chunks, segmenter.finish()]), source)


def test_auxiliary_vad_failure_retains_the_entire_block():
    def broken(_):
        raise RuntimeError("VAD failure")
    segmenter = SpeechSegmenter(broken)
    source = np.arange(2000, dtype="float32")
    chunks = segmenter.feed(source)
    assert segmenter.detector_error == "VAD failure"
    np.testing.assert_array_equal(np.concatenate([*chunks, segmenter.finish()]), source)


def test_streaming_recorder_pause_stop_and_backlog_conserve_audio(monkeypatch):
    monkeypatch.setattr("src.speech_boundary.StreamingVoiceDetector", lambda: detector)
    monkeypatch.setattr("src.audio.sd.InputStream", lambda **_: SimpleNamespace(
        start=lambda: None, stop=lambda: None, close=lambda: None))
    recorder = AudioRecorder()
    recorder.start(None, 12, smart_splits=True)
    first = np.ones((16000, 1), dtype="float32")
    second = np.full((17001, 1), 0.25, dtype="float32")
    recorder.audio_callback(first, len(first), None, None)
    recorder.pause()
    recorder.audio_callback(np.zeros((1024, 1)), 1024, None, None)  # intentionally paused
    recorder.resume()
    recorder.audio_callback(second, len(second), None, None)
    recorder.stop()
    chunks = []
    while not recorder.audio_queue.empty():
        chunks.append(recorder.audio_queue.get_nowait())
    assert not recorder.segmenting and not recorder.recording
    np.testing.assert_array_equal(np.concatenate(chunks), np.concatenate((first, second)).reshape(-1))


def test_smart_backlog_preserves_overflow_in_capture_order(monkeypatch):
    monkeypatch.setattr("src.speech_boundary.StreamingVoiceDetector", lambda: detector)
    monkeypatch.setattr("src.audio.sd.InputStream", lambda **_: SimpleNamespace(
        start=lambda: None, stop=lambda: None, close=lambda: None))
    recorder = AudioRecorder()
    recorder.start(None, 1, smart_splits=True)
    recorder.audio_queue = queue.Queue(maxsize=1)
    source = np.linspace(0.15, 0.3, 55001, dtype="float32")
    recorder.audio_callback(source.reshape(-1, 1), len(source), None, None)
    recorder.stop()
    assert recorder.capture_error
    result = np.concatenate((recorder.audio_queue.get_nowait(), recorder.overflow_chunk))
    np.testing.assert_array_equal(result, source)
