"""Pinned local model downloads and precise cache admission."""

from __future__ import annotations

import json
from pathlib import Path

from src.models import ALIGNER_REPOSITORY, ALIGNER_REVISION, MODEL_CATALOG, ModelSpec, mlx_repository

MODEL_PATTERNS = ["*.json", "*.safetensors", "*.txt", "*.model", "*.tiktoken"]
PARAKEET_FILES = ["encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"]


def whisper_repository(model_id: str) -> str:
    return ("mobiuslabsgmbh/faster-whisper-large-v3-turbo" if model_id == "large-v3-turbo"
            else "Systran/faster-whisper-" + model_id)


def local_whisper_path(roots, model_id: str, *, mlx: bool = False) -> Path | None:
    """Reuse complete application/shared Hub snapshots, including offline revisions."""
    repository = mlx_repository(model_id) if mlx else whisper_repository(model_id)
    for root in roots:
        folder = Path(root) / ("models--" + repository.replace("/", "--"))
        try:
            snapshots = [folder, *sorted(folder.glob("snapshots/*"), key=lambda item: item.stat().st_mtime, reverse=True)]
            for path in snapshots:
                complete = mlx_snapshot_complete(path) if mlx else all(
                    (path / name).is_file() and (path / name).stat().st_size > 0
                    for name in ("config.json", "model.bin", "tokenizer.json"))
                if complete:
                    return path
        except OSError:
            continue
    return None


def mlx_snapshot_complete(path: Path) -> bool:
    return ((path / "config.json").is_file()
            and any(item.is_file() and item.stat().st_size > 0
                    for pattern in ("*.npz", "*.safetensors") for item in path.glob(pattern)))


def prepare_mlx_model(root: Path, model_id: str, *, allow_download: bool = True) -> Path:
    """Resolve the chosen MLX checkpoint before recording, then use its local path."""
    from huggingface_hub import snapshot_download

    repository = mlx_repository(model_id)
    try:
        cached = Path(snapshot_download(repository, cache_dir=root, local_files_only=True))
        if mlx_snapshot_complete(cached):
            return cached
    except (OSError, ValueError):
        pass
    if not allow_download:
        raise FileNotFoundError(f"Selected MLX model {model_id} is not prepared for offline use")
    folder = Path(snapshot_download(repository, cache_dir=root,
                                   allow_patterns=["*.json", "*.npz", "*.safetensors", "*.tiktoken"]))
    if not mlx_snapshot_complete(folder):
        raise ValueError(f"Incomplete MLX checkpoint: {model_id}")
    return folder


def snapshot(root: Path, repository: str, revision: str, patterns: list[str], *, allow_download: bool = True) -> Path:
    from huggingface_hub import snapshot_download

    # A fully cached pinned revision works without contacting the Hub.
    try:
        cached = Path(snapshot_download(repository, revision=revision, cache_dir=root, local_files_only=True))
        if snapshot_complete(cached, patterns):
            return cached
    except (OSError, ValueError):
        pass
    if not allow_download:
        raise FileNotFoundError(f"Selected model {repository} is not fully prepared for offline use")
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


def modern_model_path(root: Path, spec: ModelSpec, *, allow_download: bool = True) -> Path:
    patterns = PARAKEET_FILES if spec.family == "parakeet" else MODEL_PATTERNS
    return snapshot(root, spec.repository, spec.revision, patterns, allow_download=allow_download)


def aligner_path(root: Path, *, allow_download: bool = True) -> Path:
    return snapshot(root, ALIGNER_REPOSITORY, ALIGNER_REVISION, MODEL_PATTERNS, allow_download=allow_download)


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
