"""Model catalogue and hardware-aware defaults for Local Transcriber Pro."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    size_gb: float
    ram_gb: float
    vram_gb: float
    speed_factor: float
    multilingual: bool = True
    translation: bool = True
    quality_rank: int = 0


# Every official OpenAI Whisper checkpoint remains selectable. ``large-v3`` is
# deliberately first: it is the maximum-accuracy local default. Turbo is newer
# and much faster, but is a pruned large-v3 with a small accuracy trade-off.
MODEL_CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec("large-v3", 3.10, 10.0, 7.0, 1.00, quality_rank=100),
    ModelSpec("large-v3-turbo", 1.62, 6.0, 5.0, 0.22, translation=False, quality_rank=96),
    ModelSpec("large-v2", 3.10, 10.0, 7.0, 1.05, quality_rank=94),
    ModelSpec("large-v1", 3.10, 10.0, 7.0, 1.08, quality_rank=91),
    ModelSpec("medium", 1.53, 5.0, 4.0, 0.52, quality_rank=82),
    ModelSpec("medium.en", 1.53, 5.0, 4.0, 0.48, multilingual=False, quality_rank=84),
    ModelSpec("small", 0.49, 2.5, 2.0, 0.27, quality_rank=70),
    ModelSpec("small.en", 0.49, 2.5, 2.0, 0.25, multilingual=False, quality_rank=72),
    ModelSpec("base", 0.15, 1.2, 1.0, 0.15, quality_rank=55),
    ModelSpec("base.en", 0.15, 1.2, 1.0, 0.14, multilingual=False, quality_rank=58),
    ModelSpec("tiny", 0.08, 0.8, 0.8, 0.09, quality_rank=40),
    ModelSpec("tiny.en", 0.08, 0.8, 0.8, 0.08, multilingual=False, quality_rank=43),
)

MODEL_BY_ID = {item.model_id: item for item in MODEL_CATALOG}
AUTO_MODEL_ID = "auto-best"


def get_model(model_id: str) -> ModelSpec:
    return MODEL_BY_ID.get(model_id, MODEL_BY_ID["large-v3"])


def model_label(model_id: str, language: str = "en") -> str:
    if model_id == AUTO_MODEL_ID:
        return "Qualité maximale (Auto)" if language == "fr" else "Maximum quality (Auto)"
    spec = get_model(model_id)
    notes = {
        "large-v3": ("meilleure précision", "best accuracy"),
        "large-v3-turbo": ("très rapide", "very fast"),
        "tiny": ("PC 4 Go", "4 GB PC"),
        "tiny.en": ("anglais, PC 4 Go", "English, 4 GB PC"),
    }
    note = notes.get(model_id)
    suffix = f" — {note[0 if language == 'fr' else 1]}" if note else ""
    return f"{model_id} (~{spec.size_gb:g} Go){suffix}"


def model_choices(language: str) -> list[str]:
    return [model_label(AUTO_MODEL_ID, language)] + [
        model_label(item.model_id, language) for item in MODEL_CATALOG
    ]


def model_id_from_label(label: str, language: str = "en") -> str:
    for model_id in (AUTO_MODEL_ID, *MODEL_BY_ID):
        if model_label(model_id, language) == label:
            return model_id
    # Also accept a raw id, which keeps saved settings forward compatible.
    return label if label in MODEL_BY_ID else AUTO_MODEL_ID


def mlx_repository(model_id: str) -> str:
    """Return the conventional MLX Community repository for Apple Silicon."""
    normalized = "large-v3-turbo" if model_id == "turbo" else model_id
    return f"mlx-community/whisper-{normalized}-mlx"
