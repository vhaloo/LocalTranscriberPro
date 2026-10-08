"""Pinned local model downloads and precise cache admission."""

from __future__ import annotations

import json
from pathlib import Path

from src.models import ALIGNER_REPOSITORY, ALIGNER_REVISION, MODEL_CATALOG, ModelSpec

MODEL_PATTERNS = ["*.json", "*.safetensors", "*.txt", "*.model", "*.tiktoken"]
PARAKEET_FILES = ["encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"]


def snapshot(root: Path, repository: str, revision: str, patterns: list[str]) -> Path:
    from huggingface_hub import snapshot_download

    # A fully cached pinned revision works without contacting the Hub.
    try:
        cached = Path(snapshot_download(repository, revision=revision, cache_dir=root, local_files_only=True))
        if snapshot_complete(cached, patterns):
            return cached
    except (OSError, ValueError):
        pass
    return Path(snapshot_download(repository, revision=revision, cache_dir=root, allow_patterns=patterns))


def snapshot_complete(path: Path, patterns: list[str]) -> bool:
    try:
        if patterns == PARAKEET_FILES:
            return all((path / name).is_file() and (path / name).stat().st_size > 0 for name in patterns)
        if not (path / "config.json").is_file():
            return False
        index = path / "model.safetensors.index.json"
        if index.exists():
            shards = set(json.loads(index.read_text(encoding="utf-8"))["weight_map"].values())
            return bool(shards) and all((path / name).is_file() for name in shards)
        return any(path.glob("*.safetensors"))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def modern_model_path(root: Path, spec: ModelSpec) -> Path:
    patterns = PARAKEET_FILES if spec.family == "parakeet" else MODEL_PATTERNS
    return snapshot(root, spec.repository, spec.revision, patterns)


def aligner_path(root: Path) -> Path:
    return snapshot(root, ALIGNER_REPOSITORY, ALIGNER_REVISION, MODEL_PATTERNS)


def complete_modern_ids(root: Path) -> set[str]:
    found: set[str] = set()
    for spec in MODEL_CATALOG:
        if not spec.repository:
            continue
        path = root / ("models--" + spec.repository.replace("/", "--")) / "snapshots" / spec.revision
        patterns = PARAKEET_FILES if spec.family == "parakeet" else MODEL_PATTERNS
        if snapshot_complete(path, patterns):
            if spec.family == "qwen":
                align = root / ("models--" + ALIGNER_REPOSITORY.replace("/", "--")) / "snapshots" / ALIGNER_REVISION
                if not snapshot_complete(align, MODEL_PATTERNS):
                    continue
            found.add(spec.model_id)
    return found
