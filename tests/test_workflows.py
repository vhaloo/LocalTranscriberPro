import json
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
import soundfile as sf

from src.editing import apply_text_edits
from src.estimator import TimeEstimator
from src.exports import write_bundle
from src.media import RecordingSpool, iter_audio_chunks
from src.segments import shift_segments, validate_segments
from src.settings import SettingsStore
from src.transcript_format import TranscriptFormat, format_transcript
from src.utils import atomic_write_text, create_srt_content

SEGMENTS = [{"start": 0., "end": 2., "text": "Bonjour Marie."},
            {"start": 2., "end": 4., "text": "Le lac est bleu."}]


@pytest.mark.parametrize("layout", ["blocks", "lines"])
def test_editor_correction_reaches_every_export_without_changing_timing(tmp_path, layout):
    options = TranscriptFormat(mode=layout)
    before = format_transcript(SEGMENTS, options)
    after = before.replace("Marie", "Valentin")
    edited = apply_text_edits(SEGMENTS, before, after)
    base = tmp_path / "edited"
    write_bundle(base, edited, options)
    for suffix in (".txt", ".srt", ".vtt", ".json", ".csv"):
        content = base.with_suffix(suffix).read_text(encoding="utf-8-sig")
        assert "Valentin" in content
        assert "Marie" not in content
    assert edited[0]["end"] == 2
    assert edited[1]["text"] == SEGMENTS[1]["text"]


def test_appending_editor_text_is_not_lost():
    before = format_transcript(SEGMENTS)
    edited = apply_text_edits(SEGMENTS, before, before + " Merci.")
    assert edited[-1]["text"].endswith("Merci.")


def test_complete_editor_rewrite_keeps_every_word_in_structured_exports(tmp_path):
    edited_text = "Un autre contenu intégralement réécrit et vérifié."
    edited = apply_text_edits(SEGMENTS, format_transcript(SEGMENTS), edited_text)
    write_bundle(tmp_path / "rewrite", edited)
    for suffix in (".srt", ".vtt", ".json", ".csv"):
        assert edited_text in (tmp_path / ("rewrite" + suffix)).read_text(encoding="utf-8-sig")
    assert edited[0]["start"] == 0 and edited[-1]["end"] == 4


def test_segment_and_word_timing_are_shifted_together():
    values = [{"start": 1, "end": 3, "text": "Hello", "words": [{"start": 1, "end": 2, "word": "Hello"}]}]
    shifted = shift_segments(values, 10)
    assert shifted[0]["words"][0]["start"] == 11
    assert values[0]["start"] == 1


def test_decoding_stereo_48khz_is_bounded_and_preserves_timeline(tmp_path):
    path = tmp_path / "stereo.wav"
    audio = np.zeros((51 * 48000, 2), dtype=np.float32)
    sf.write(path, audio, 48000)
    chunks = list(iter_audio_chunks(str(path)))
    assert all(len(chunk) <= 25 * 16000 for _, chunk in chunks)
    assert sum(len(chunk) for _, chunk in chunks) == 51 * 16000
    assert chunks[-1][0] + len(chunks[-1][1]) / 16000 == 51


def test_recording_spool_is_readable_before_recording_finishes(tmp_path):
    spool = RecordingSpool(tmp_path / "recording.wav")
    try:
        spool.append(np.ones(16000, dtype=np.float32) * 0.1)
        assert sf.info(spool.path).duration == 1
        spool.append(np.zeros(16000, dtype=np.float32))
    finally:
        spool.close()
    assert sf.info(spool.path).duration == 2


def test_concurrent_atomic_saves_never_mix_or_truncate_content(tmp_path):
    path = tmp_path / "session.json"
    contents = [json.dumps({"id": value, "text": "é" * 1000}) for value in range(12)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda value: atomic_write_text(path, value), contents))
    assert path.read_text(encoding="utf-8") in contents
    assert not list(tmp_path.glob("*.tmp"))


def test_srt_numbers_remain_contiguous_after_empty_segments():
    content = create_srt_content([{"start": 0, "end": 1, "text": ""}, *SEGMENTS])
    assert content.startswith("1\n")
    assert "\n\n2\n" in content


def test_settings_repair_malformed_values_but_preserve_user_output(tmp_path):
    path = tmp_path / "settings.json"
    output = str(tmp_path / "My work")
    path.write_text(json.dumps({"model": "evil/repo", "beam_size": "bad", "chunk_seconds": -200,
                               "ui_mode": [], "translate": "false", "output_folder": output,
                               "window_geometry": "broken", "benchmarks": []}), encoding="utf-8")
    settings = SettingsStore(path)
    assert settings.get("output_folder") == output
    assert settings.get("beam_size") == 8
    assert settings.get("chunk_seconds") == 5
    assert settings.get("translate") is False
    assert settings.get("model") == "auto-best"


@pytest.mark.parametrize("values", [[1], [{"text": "bad", "start": float("nan"), "end": 2}],
                                    [{"text": "bad", "start": 4, "end": 2}], [{"text": ["bad"]}]])
def test_malformed_recovery_data_cannot_crash_the_editor(values):
    with pytest.raises((ValueError, TypeError)):
        validate_segments(values)


def test_malformed_performance_history_does_not_break_next_transcription():
    estimator = TimeEstimator({"large-v3:cuda": "bad", "tiny:cpu": float("nan"), "small:cpu": 2.0})
    assert estimator.estimate(10, "large-v3", "cuda").seconds > 0
    assert estimator.estimate(10, "small", "cpu").seconds == 20


def test_backlogged_microphone_preserves_overflow_and_final_tail():
    import queue

    from src.audio import AudioRecorder

    recorder = AudioRecorder()
    recorder.audio_queue = queue.Queue(maxsize=1)
    recorder.audio_queue.put(np.zeros((16000, 1)))
    recorder.recording = True
    recorder.chunk_duration_samples = 16000
    audio = np.arange(19200, dtype=np.float32).reshape(-1, 1)
    recorder.audio_callback(audio, len(audio), None, None)
    assert not recorder.recording
    assert recorder.capture_error
    recorder.stop()
    np.testing.assert_array_equal(recorder.overflow_chunk, audio)


def test_model_replacement_waits_for_inference_to_finish():
    import threading

    from src.transcriber import TranscriberEngine, TranscriptionOptions

    engine = object.__new__(TranscriberEngine)
    engine._load_lock = threading.RLock()
    engine.model_name = None
    from types import SimpleNamespace

    engine.current_status = None
    engine.translator = SimpleNamespace(unload=lambda: None)
    entered, release, replaced = threading.Event(), threading.Event(), threading.Event()

    def inference(*_args):
        entered.set()
        assert release.wait(5)
        return {}

    engine._transcribe_locked = inference
    engine._load_model_unlocked = lambda *_args: replaced.set()
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(engine._transcribe, np.zeros(16000), TranscriptionOptions(), None)
        assert entered.wait(5)
        second = executor.submit(engine.load_model, "tiny")
        assert not replaced.wait(0.05)
        release.set()
        first.result(timeout=5)
        second.result(timeout=5)
    assert replaced.is_set()


def test_batch_continues_after_corrupt_audio_and_keeps_completed_exports(tmp_path):
    import threading
    from types import SimpleNamespace

    from src.gui import TranscriberApp

    appended, completed = [], []
    def transcribe(filepath, *_args, **_kwargs):
        if filepath == "corrupt.wav":
            raise ValueError("Corrupt audio")
        return {"segments": [{"start": 0, "end": 2, "text": filepath}], "duration": 2}

    def save(segments, stem):
        base = tmp_path / stem
        write_bundle(base, segments)
        return base.with_suffix(".txt")

    harness = SimpleNamespace(
        hardware=SimpleNamespace(resolve_model=lambda *_args: "tiny"),
        engine=SimpleNamespace(cached_model_ids=lambda: set(), load_model=lambda *_args: SimpleNamespace(
            model_id="tiny", device="cpu", backend="faster-whisper"), transcribe_file=transcribe),
        t=lambda key, **_values: key, _safe_ui=lambda callback, *args: callback(*args),
        _set_status=lambda *_args: None, _engine_load_status=lambda *_args: None,
        transcribe_options=lambda *_args: None, transcript_data=[], cancel_event=threading.Event(),
        _set_progress=lambda *_args: None, _prepare_segments=lambda segments, _: segments,
        _append_segments=appended.extend, save_result_bundle=save,
        estimator=SimpleNamespace(observe=lambda *_args: None),
        _finish_batch=lambda *args: completed.append(args), _fail_job=lambda error: pytest.fail(str(error)),
    )
    TranscriberApp._batch_worker(harness, ["first.wav", "corrupt.wav", "last.wav"], [2, 2, 2],
                                 {"model": "tiny", "device": "cpu", "cleanup": False,
                                  "speaker": False, "smart_subtitles": False})
    assert completed[0][2:] == (2, ["corrupt.wav"])
    assert appended[1]["start"] == 3
    assert (tmp_path / "first.json").is_file() and (tmp_path / "last.srt").is_file()
    assert not (tmp_path / "corrupt.txt").exists()


def test_incomplete_whisper_cache_cannot_bypass_download_space_check(tmp_path):
    from src.hardware import HardwareProfile
    from src.transcriber import TranscriberEngine

    engine = TranscriberEngine(HardwareProfile("Windows", "11", "AMD64", "Test", 8, 16))
    engine.model_cache = tmp_path
    engine.cache_roots = lambda: [tmp_path]
    snapshot = tmp_path / "models--Systran--faster-whisper-large-v3" / "snapshots" / "revision"
    snapshot.mkdir(parents=True)
    assert "large-v3" not in engine.cached_model_ids()
    for name in ("model.bin", "config.json", "tokenizer.json"):
        (snapshot / name).write_text("test")
    assert "large-v3" in engine.cached_model_ids()
    assert not engine.delete_model_file(tmp_path)
    assert not engine.delete_model_file(snapshot / "config.json")


def test_packaged_youtube_runtime_does_not_depend_on_user_path(tmp_path, monkeypatch):
    import sys

    from src.youtube_utils import javascript_runtimes

    folder = tmp_path / "js-runtime"
    folder.mkdir()
    (folder / "node.exe").write_bytes(b"runtime")
    (folder / "node").write_bytes(b"runtime")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr("src.youtube_utils.shutil.which", lambda _: pytest.fail("Must use bundled runtime"))
    assert str(folder) in javascript_runtimes()["node"]["path"]
