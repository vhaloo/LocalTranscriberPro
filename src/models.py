"""Model catalogue and conservative runtime requirements.

The figures are deliberately safety-oriented. They describe a complete desktop
session (application, decoder and model), rather than only the weight tensor.
That lets the hardware layer prevent choices that are likely to exhaust memory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    size_gb: float
    ram_gb: float
    available_ram_gb: float
    vram_gb: float
    speed_factor: float
    multilingual: bool = True
    translation: bool = True
    quality_rank: int = 0

    @property
    def download_space_gb(self) -> float:
        """Free space required for a safe first download and final cache."""
        return max(0.35, self.size_gb * 1.35 + 0.25)

    @property
    def gpu_system_ram_gb(self) -> float:
        """Host RAM still required when the model itself runs on a GPU."""
        return max(4.0, min(8.0, self.ram_gb * 0.65))


# Every official OpenAI Whisper checkpoint remains represented. The memory
# floors include headroom for the GUI, decoding and the operating system.
MODEL_CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec("large-v3", 3.10, 12.0, 5.0, 7.0, 1.00, quality_rank=100),
    ModelSpec("large-v3-turbo", 1.62, 8.0, 3.0, 5.0, 0.22, translation=False, quality_rank=96),
    ModelSpec("large-v2", 3.10, 12.0, 5.0, 7.0, 1.05, quality_rank=94),
    ModelSpec("large-v1", 3.10, 12.0, 5.0, 7.0, 1.08, quality_rank=91),
    ModelSpec("medium", 1.53, 8.0, 3.0, 4.0, 0.52, quality_rank=82),
    ModelSpec(
        "medium.en", 1.53, 8.0, 3.0, 4.0, 0.48, multilingual=False, quality_rank=84
    ),
    ModelSpec("small", 0.49, 5.0, 1.6, 2.0, 0.27, quality_rank=70),
    ModelSpec(
        "small.en", 0.49, 5.0, 1.6, 2.0, 0.25, multilingual=False, quality_rank=72
    ),
    ModelSpec("base", 0.15, 4.5, 1.0, 1.0, 0.15, quality_rank=55),
    ModelSpec("base.en", 0.15, 4.5, 1.0, 1.0, 0.14, multilingual=False, quality_rank=58),
    ModelSpec("tiny", 0.08, 3.5, 0.65, 0.8, 0.09, quality_rank=40),
    ModelSpec("tiny.en", 0.08, 3.5, 0.65, 0.8, 0.08, multilingual=False, quality_rank=43),
)

MODEL_BY_ID = {item.model_id: item for item in MODEL_CATALOG}
AUTO_MODEL_ID = "auto-best"


def get_model(model_id: str) -> ModelSpec:
    return MODEL_BY_ID.get(model_id, MODEL_BY_ID["large-v3"])


def model_label(model_id: str, language: str = "en") -> str:
    if model_id == AUTO_MODEL_ID:
        return "Qualité maximale sûre (Auto)" if language == "fr" else "Safest maximum quality (Auto)"
    spec = get_model(model_id)
    notes = {
        "large-v3": ("meilleure précision", "best accuracy"),
        "large-v3-turbo": ("très rapide", "very fast"),
        "tiny": ("PC 4 Go", "4 GB PC"),
        "tiny.en": ("anglais, PC 4 Go", "English, 4 GB PC"),
    }
    note = notes.get(model_id)
    suffix = f" — {note[0 if language == 'fr' else 1]}" if note else ""
    unit = "Go" if language == "fr" else "GB"
    return f"{model_id} (~{spec.size_gb:g} {unit}){suffix}"


def model_requirement_text(model_id: str, language: str = "en") -> str:
    spec = get_model(model_id)
    if language == "fr":
        return (
            f"CPU : {spec.ram_gb:g} Go RAM • GPU : {spec.vram_gb:g} Go VRAM • "
            f"téléchargement : {spec.size_gb:g} Go"
        )
    return (
        f"CPU: {spec.ram_gb:g} GB RAM • GPU: {spec.vram_gb:g} GB VRAM • "
        f"download: {spec.size_gb:g} GB"
    )


def model_choices(language: str) -> list[str]:
    return [model_label(AUTO_MODEL_ID, language)] + [
        model_label(item.model_id, language) for item in MODEL_CATALOG
    ]


def model_id_from_label(label: str, language: str = "en") -> str:
    for model_id in (AUTO_MODEL_ID, *MODEL_BY_ID):
        if model_label(model_id, language) == label:
            return model_id
    return label if label in MODEL_BY_ID else AUTO_MODEL_ID


def mlx_repository(model_id: str) -> str:
    """Return the conventional MLX Community repository for Apple Silicon."""
    normalized = "large-v3-turbo" if model_id == "turbo" else model_id
    return f"mlx-community/whisper-{normalized}-mlx"
