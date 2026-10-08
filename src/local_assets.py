"""Pinned, verified ordinary model files; no Hub access once prepared."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.jobs import check_cancelled
from src.utils import atomic_write_text


def prepare_assets(folder: Path, repository: str, revision: str, files: dict,
                   allow_download=True, cancel_event=None, receipt_folder=None):
    folder.mkdir(parents=True, exist_ok=True)
    receipt_path = (receipt_folder or folder) / "verified-assets.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        receipt = {}
    missing = []
    for name, spec in files.items():
        check_cancelled(cancel_event)
        path = folder / name
        if not path.is_file() or path.stat().st_size != spec["size"]:
            missing.append(name)
    if missing:
        if not allow_download:
            raise RuntimeError("Local model not prepared: " + repository)
        from huggingface_hub import snapshot_download

        snapshot_download(repository, revision=revision, local_dir=folder, allow_patterns=missing, max_workers=8)
    for name, spec in files.items():
        check_cancelled(cancel_event)
        path = folder / name
        signature = [path.stat().st_size, path.stat().st_mtime_ns, spec["hash"]]
        if signature[0] != spec["size"]:
            raise RuntimeError("Incomplete model file: " + name)
        if receipt.get(name) != signature:
            if spec["algorithm"] == "git-sha1":
                digest = hashlib.sha1(usedforsecurity=False)
                digest.update(f"blob {spec['size']}\0".encode())
                digest.update(path.read_bytes())
                actual = digest.hexdigest()
            else:
                with path.open("rb") as handle:
                    actual = hashlib.file_digest(handle, "sha256").hexdigest()
            if actual != spec["hash"]:
                raise RuntimeError("Model checksum mismatch: " + name)
        receipt[name] = signature
    atomic_write_text(receipt_path, json.dumps(receipt))
    return folder
