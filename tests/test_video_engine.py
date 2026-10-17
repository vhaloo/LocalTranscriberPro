import hashlib
import io
import json
import threading

import pytest

from src import video_engine
from src.jobs import JobCancelled


def release(data=b"verified package"):
    version = "2026.10.10.233141"
    filename = video_engine.engine_filename()
    prefix = f"https://github.com/{video_engine.REPOSITORY}/releases/download/{version}/"
    return {"tag_name": version, "assets": [
        {"name": filename, "size": len(data), "browser_download_url": prefix + filename},
        {"name": "SHA2-256SUMS", "size": 1000, "browser_download_url": prefix + "SHA2-256SUMS"},
    ]}


def downloads(monkeypatch, data, *, expected=None):
    update = video_engine.parse_engine_release(release(data))
    digest = hashlib.sha256(data).hexdigest() if expected is None else expected
    manifest = f"{digest}  {update.filename}\n".encode()
    monkeypatch.setattr(video_engine, "_open", lambda url: io.BytesIO(manifest if url == update.checksum_url else data))
    return update


def test_verified_engine_rejects_tampering_before_it_can_be_launched(tmp_path, monkeypatch):
    update = downloads(monkeypatch, b"official package")
    target = video_engine.install_engine(update, tmp_path)
    assert video_engine.prepared_engine(tmp_path) == (target, update.version)
    target.write_bytes(b"modified package")
    assert video_engine.prepared_engine(tmp_path) is None
    target.write_bytes(b"official package")
    receipt = tmp_path / "verified-engine.json"
    payload = json.loads(receipt.read_text("utf-8"))
    payload["repository"] = "other/repository"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    assert video_engine.prepared_engine(tmp_path) is None


def test_checksum_failure_preserves_previous_engine_and_removes_own_partial(tmp_path, monkeypatch):
    update = downloads(monkeypatch, b"old official package")
    target = video_engine.install_engine(update, tmp_path)
    old_receipt = (tmp_path / "verified-engine.json").read_bytes()
    update = downloads(monkeypatch, b"corrupted new package", expected="0" * 64)
    with pytest.raises(ValueError, match="SHA-256"):
        video_engine.install_engine(update, tmp_path)
    assert target.read_bytes() == b"old official package"
    assert (tmp_path / "verified-engine.json").read_bytes() == old_receipt
    assert not list(tmp_path.glob("*.part"))
    assert video_engine.prepared_engine(tmp_path) is not None


def test_engine_update_cancel_cleans_partial_without_installing(tmp_path, monkeypatch):
    update = downloads(monkeypatch, b"package")
    cancel = threading.Event()
    with pytest.raises(JobCancelled):
        video_engine.install_engine(update, tmp_path, progress=lambda _: cancel.set(), cancel_event=cancel)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("change", ["repository", "oversize", "draft", "tag", "checksums"])
def test_engine_metadata_rejects_untrusted_or_incomplete_release(change):
    payload = release()
    if change == "repository":
        payload["assets"][0]["browser_download_url"] = "https://github.com/other/repo/releases/download/v1/yt-dlp.exe"
    elif change == "oversize":
        payload["assets"][0]["size"] = video_engine.MAX_ENGINE_BYTES + 1
    elif change == "draft":
        payload["draft"] = True
    elif change == "tag":
        payload["tag_name"] = "../../other"
    else:
        payload["assets"].pop()
    with pytest.raises(ValueError):
        video_engine.parse_engine_release(payload)

