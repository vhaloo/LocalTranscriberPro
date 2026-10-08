from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np

import src.diarizer as module


def test_fragmented_clustering_is_not_reported_as_hundreds_of_people(monkeypatch):
    diarizer = module.Diarizer()
    diarizer.enabled = True
    diarizer.load_model = lambda: True
    diarizer.classifier = SimpleNamespace(encode_batch=lambda _: SimpleNamespace(
        squeeze=lambda: SimpleNamespace(numpy=lambda: np.ones(4))))
    monkeypatch.setattr(module, "torch", SimpleNamespace(no_grad=nullcontext,
        from_numpy=lambda _: SimpleNamespace(unsqueeze=lambda _: None)), raising=False)
    monkeypatch.setattr(module, "iter_audio_chunks", lambda _: [(0, np.ones(48 * 16000, dtype="float32"))])
    monkeypatch.setattr(module, "AgglomerativeClustering", lambda **_: SimpleNamespace(
        fit_predict=lambda values: np.arange(len(values))), raising=False)
    segments = [{"start": index * 2, "end": index * 2 + 1.8, "text": "Original sentence"}
                for index in range(22)]
    result = diarizer.process("test.wav", segments)
    assert diarizer.last_warning == "diarization_uncertain"
    assert all("speaker" not in item for item in result)
    assert [item["text"] for item in result] == [item["text"] for item in segments]


def test_single_reliable_embedding_keeps_speaker_feature(monkeypatch):
    diarizer = module.Diarizer()
    diarizer.enabled = True
    diarizer.load_model = lambda: True
    diarizer.classifier = SimpleNamespace(encode_batch=lambda _: SimpleNamespace(
        squeeze=lambda: SimpleNamespace(numpy=lambda: np.ones(4))))
    monkeypatch.setattr(module, "torch", SimpleNamespace(no_grad=nullcontext,
        from_numpy=lambda _: SimpleNamespace(unsqueeze=lambda _: None)), raising=False)
    monkeypatch.setattr(module, "iter_audio_chunks", lambda _: [(0, np.ones(2 * 16000, dtype="float32"))])
    result = diarizer.process("test.wav", [{"start": 0, "end": 2, "text": "Bonjour"}])
    assert result[0]["speaker"] == "Speaker 1"
    assert not diarizer.last_warning
