import hashlib

import pytest

from src.local_assets import prepare_assets
from src.speech_output import CATALOG, LocalSpeechOutput


def test_offline_model_verification_rejects_same_size_corruption(tmp_path):
    data = b"correct weights"
    files = {"weights.bin": {"size": len(data), "hash": hashlib.sha256(data).hexdigest(), "algorithm": "sha256"}}
    path = tmp_path / "weights.bin"
    path.write_bytes(data)
    prepare_assets(tmp_path, "test/model", "revision", files, False)
    path.write_bytes(b"changed weights")
    with pytest.raises(RuntimeError, match="checksum"):
        prepare_assets(tmp_path, "test/model", "revision", files, False)


def test_missing_voice_never_downloads_in_offline_mode(tmp_path):
    engine = LocalSpeechOutput(tmp_path)
    engine.bundled = tmp_path / "absent-bundle"
    with pytest.raises(RuntimeError, match="not prepared"):
        engine.prepare("ht", allow_download=False)
    assert not engine.ready("ht")
    assert not engine.supports("und")


def test_priority_voice_metadata_is_pinned_and_licenses_are_visible():
    assert len(CATALOG["voices"]) == 47
    assert CATALOG["voices"]["ht"]["license"] == "CC-BY-NC-4.0"
    assert CATALOG["voices"]["pa"]["backend"] == "mms"
    assert all(len(voice["revision"]) == 40 for voice in CATALOG["voices"].values())
