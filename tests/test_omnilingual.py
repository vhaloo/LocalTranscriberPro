from types import SimpleNamespace

import numpy as np

from src.confidence import annotate_recognition
from src.omnilingual import OmnilingualBackend
from src.segments import validate_segments


def test_fasttext_epsilon_and_arabic_variant_do_not_break_saved_transcripts():
    backend = object.__new__(OmnilingualBackend)
    backend.lid = SimpleNamespace(f=SimpleNamespace(predict=lambda *_: [(1.0000100135803223, "__label__ars_Arab")]))
    stream = SimpleNamespace(result=SimpleNamespace(text="مرحبا"), accept_waveform=lambda *_: None)
    backend.recognizer = SimpleNamespace(create_stream=lambda: stream, decode_stream=lambda *_: None)
    language, segments, _ = backend.transcribe_chunk(np.zeros(16000, dtype=np.float32), SimpleNamespace(language=None))
    assert language == "ar"
    result = annotate_recognition(dict(segments=segments, language=language, language_probability=backend.language_probability))
    assert validate_segments(result["segments"])[0]["language_probability"] == 1.0
