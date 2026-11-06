"""Cache-only model preparation and bounded removal preserve unrelated data."""
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.model_store import ModelStore
from src.models import ALIGNER_REPOSITORY, get_model


def store(tmp_path):
    return ModelStore(tmp_path / "models", omnilingual_root=tmp_path / "omnilingual")


@pytest.mark.parametrize("nested", [False, True])
def test_windows_reparse_guards_do_not_depend_on_python_is_junction(tmp_path, monkeypatch, nested):
    selected = store(tmp_path)
    root = model_files(selected.root / "models--Systran--faster-whisper-tiny")
    suspect = root / "linked-folder" if nested else root
    if nested:
        suspect.mkdir()
    original_stat = Path.lstat
    def metadata(path):
        actual = original_stat(path)
        return SimpleNamespace(st_mode=actual.st_mode, st_file_attributes=0x400) if path == suspect else actual
    monkeypatch.setattr(Path, "is_junction", lambda _path: False, raising=False)
    monkeypatch.setattr(Path, "lstat", metadata)
    assert selected.delete_path(root) is False
    assert (root / "model.bin").is_file()


def model_files(path):
    path.mkdir(parents=True)
    (path / "model.bin").write_bytes(b"example test weights")
    return path


def test_download_only_the_requested_checkpoint_without_inference(tmp_path, monkeypatch):
    selected = store(tmp_path)
    calls = []
    def download(model, **options):
        calls.append((model, options))
        return str(tmp_path / "prepared")
    monkeypatch.setattr("faster_whisper.utils.download_model", download)
    monkeypatch.setattr("faster_whisper.WhisperModel", lambda *_args, **_kwargs: pytest.fail("Download initialized inference"))
    assert selected.download("large-v3") == str(tmp_path / "prepared")
    assert calls == [("large-v3", {"cache_dir": str(tmp_path / "models")})]


@pytest.mark.parametrize("model", ["auto-best", "unknown", "untrusted/remote-code"])
def test_only_explicit_catalogue_ids_can_reach_a_downloader(tmp_path, model):
    with pytest.raises(ValueError):
        store(tmp_path).download(model)


def test_download_retains_disk_checks_without_needing_ram_or_gpu(tmp_path, monkeypatch):
    monkeypatch.setattr("src.model_store.available_bytes", lambda *_: 0)
    monkeypatch.setattr("faster_whisper.utils.download_model", lambda *_args, **_kwargs: pytest.fail("Disk guard bypassed"))
    with pytest.raises(OSError, match="GB free"):
        store(tmp_path).download("large-v3")


def test_delete_model_keeps_other_checkpoints_shared_aligner_and_transcripts(tmp_path):
    selected = store(tmp_path)
    qwen = model_files(selected.root / ("models--" + get_model("qwen3-asr-1.7b").repository.replace("/", "--")))
    compact = model_files(selected.root / ("models--" + get_model("qwen3-asr-0.6b").repository.replace("/", "--")))
    aligner = model_files(selected.root / ("models--" + ALIGNER_REPOSITORY.replace("/", "--")))
    transcript = tmp_path / "conversation.txt"
    transcript.write_text("Original conversation")
    assert [row["path"] for row in selected.model_entries("qwen3-asr-1.7b")] == [str(qwen)]
    assert selected.delete_path(qwen)
    assert not qwen.exists() and compact.exists() and aligner.exists()
    assert transcript.read_text() == "Original conversation"


@pytest.mark.parametrize("target", [".", "whisper-transcripts", "models--Systran--faster-whisper-tiny/snapshots"])
def test_roots_arbitrary_names_and_subdirectories_are_not_deletion_targets(tmp_path, target):
    selected = store(tmp_path)
    folder = selected.root / target
    folder.mkdir(parents=True)
    (folder / "original.txt").write_text("Keep")
    assert not selected.delete_path(folder)
    assert (folder / "original.txt").read_text() == "Keep"


def test_model_deletion_unlinks_hardlinks_without_deleting_the_other_name(tmp_path):
    selected = store(tmp_path)
    model = model_files(selected.root / "models--Systran--faster-whisper-tiny")
    original = tmp_path / "original.bin"
    os.link(model / "model.bin", original)
    assert selected.delete_path(model)
    assert original.read_bytes() == b"example test weights"


def test_omni_and_shared_language_detector_are_managed_separately(tmp_path):
    selected = store(tmp_path)
    omni = model_files(selected.omnilingual_root / "1b-v2")
    lid = model_files(selected.omnilingual_root / "glotlid")
    assert len(selected.entries()) == 2
    assert selected.delete_path(omni)
    assert lid.exists()
    assert selected.entries()[0]["shared"] is True


def test_directory_junction_inside_model_blocks_deletion(tmp_path, monkeypatch):
    selected = store(tmp_path)
    model = model_files(selected.root / "models--Systran--faster-whisper-tiny")
    junction = model / "outside"
    junction.mkdir()
    monkeypatch.setattr(Path, "is_junction", lambda value: value == junction, raising=False)
    assert not selected.delete_path(model)
    assert (model / "model.bin").is_file()


@pytest.mark.skipif(os.name != "nt", reason="Windows DOS read-only cache attributes")
def test_readonly_windows_model_files_and_folders_can_be_removed(tmp_path):
    selected = store(tmp_path)
    model = model_files(selected.root / "models--Systran--faster-whisper-tiny")
    for path in [model / "model.bin", model]:
        path.chmod(stat.S_IREAD)
    assert selected.delete_path(model)
    assert not model.exists()
