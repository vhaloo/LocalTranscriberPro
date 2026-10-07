"""Model catalogue and conservative runtime requirements.

The figures are deliberately safety-oriented. They describe a complete desktop
session (application, decoder and model), rather than only the weight tensor.
That lets the hardware layer prevent choices that are likely to exhaust memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log


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
    family: str = "whisper"
    repository: str = ""
    revision: str = ""
    languages: tuple[str, ...] = ()
    auto_gpu_only: bool = False

    @property
    def multilingual_score(self) -> float | None:
        """Editorial relative index, never a measured recognition percentage."""
        if not self.multilingual:
            return None
        return round(max(0.0, min(10.0, self.quality_rank / 120 * 10)), 1)

    @property
    def relative_speed_score(self) -> float:
        """Indicative logarithmic index of the catalogue's runtime estimates."""
        factor = max(0.015, min(1.8, self.speed_factor))
        return round(1 + 9 * log(1.8 / factor) / log(1.8 / 0.015), 1)

    def supports(self, language: str | None = None, task: str = "transcribe") -> bool:
        if task == "translate" and (not self.translation or not self.multilingual):
            return False
        if language in {None, "", "auto"}:
            return True
        if not self.multilingual and language != "en":
            return False
        return not self.languages or language in self.languages

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
    ModelSpec(
        "qwen3-asr-1.7b", 6.2, 20.0, 10.0, 7.5, 1.8,
        translation=False, quality_rank=120, family="qwen",
        repository="Qwen/Qwen3-ASR-1.7B", revision="7278e1e70fe206f11671096ffdd38061171dd6e5",
        languages=tuple("zh en yue ar de fr es pt id it ko ru th vi ja tr hi ms nl sv da fi pl cs fil fa el hu mk ro".split()),
        auto_gpu_only=True,
    ),
    ModelSpec(
        "qwen3-asr-0.6b", 2.9, 12.0, 6.0, 5.5, 0.8,
        translation=False, quality_rank=105, family="qwen",
        repository="Qwen/Qwen3-ASR-0.6B", revision="5eb144179a02acc5e5ba31e748d22b0cf3e303b0",
        languages=tuple("zh en yue ar de fr es pt id it ko ru th vi ja tr hi ms nl sv da fi pl cs fil fa el hu mk ro".split()),
        auto_gpu_only=True,
    ),
    ModelSpec(
        "parakeet-tdt-0.6b-v3", 0.64, 4.0, 2.0, 0.0, 0.015,
        translation=False, quality_rank=98, family="parakeet",
        repository="csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",
        revision="2bda32ec70b097a55adaa07d9a7173915b43cc78",
        languages=tuple("bg hr cs da nl en et fi fr de el hu it lv lt mt pl pt ro ru sk sl es sv uk".split()),
    ),
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
AUTO_FAST_MODEL_ID = "auto-fast"
ALIGNER_REPOSITORY = "Qwen/Qwen3-ForcedAligner-0.6B"
ALIGNER_REVISION = "c7cbfc2048c462b0d63a45797104fc9db3ad62b7"


def get_model(model_id: str) -> ModelSpec:
    # Auto is a profile, never a downloadable model. Reject invalid saved IDs.
    if model_id in {AUTO_MODEL_ID, AUTO_FAST_MODEL_ID, "large"}:
        return MODEL_BY_ID["large-v3"]
    if model_id == "turbo":
        return MODEL_BY_ID["large-v3-turbo"]
    try:
        return MODEL_BY_ID[model_id]
    except KeyError as error:
        raise ValueError(f"Unknown speech model: {model_id}") from error


def ranked_models() -> tuple[ModelSpec, ...]:
    """Multilingual accuracy first; English-only checkpoints remain available."""
    return tuple(sorted(MODEL_CATALOG, key=lambda spec: (not spec.multilingual, -spec.quality_rank)))


def model_label(model_id: str, language: str = "en") -> str:
    if model_id == AUTO_MODEL_ID:
        return "Qualité maximale sûre (Auto)" if language == "fr" else "Safest maximum quality (Auto)"
    if model_id == AUTO_FAST_MODEL_ID:
        return "Rapidité (Auto)" if language == "fr" else "Fast transcription (Auto)"
    spec = get_model(model_id)
    notes = {
        "qwen3-asr-1.7b": ("précision multilingue 2026", "2026 multilingual accuracy"),
        "qwen3-asr-0.6b": ("multilingue compact 2026", "2026 compact multilingual"),
        "parakeet-tdt-0.6b-v3": ("25 langues, CPU rapide", "25 languages, fast CPU"),
        "large-v3": ("multilingue, traduction", "multilingual, translation"),
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
    if spec.family == "parakeet":
        if language == "fr":
            return f"CPU : {spec.ram_gb:g} Go RAM • aucun GPU requis • téléchargement : {spec.size_gb:g} Go"
        return f"CPU: {spec.ram_gb:g} GB RAM • no GPU required • download: {spec.size_gb:g} GB"
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
    return [model_label(AUTO_MODEL_ID, language), model_label(AUTO_FAST_MODEL_ID, language)] + [
        model_label(item.model_id, language) for item in ranked_models()
    ]


def model_capability_text(model_id: str, language: str = "en") -> str:
    spec = get_model(model_id)
    if not spec.multilingual:
        return "Anglais uniquement" if language == "fr" else "English only"
    coverage = (f"{len(spec.languages)} langues" if language == "fr" else f"{len(spec.languages)} languages") if spec.languages else (
        "Multilingue" if language == "fr" else "Multilingual"
    )
    if spec.translation:
        coverage += " • traduction vers l’anglais" if language == "fr" else " • English translation"
    return coverage


def model_id_from_label(label: str, language: str = "en") -> str:
    for model_id in (AUTO_MODEL_ID, AUTO_FAST_MODEL_ID, *MODEL_BY_ID):
        if model_label(model_id, language) == label:
            return model_id
    return label if label in MODEL_BY_ID else AUTO_MODEL_ID


def mlx_repository(model_id: str) -> str:
    """Return the conventional MLX Community repository for Apple Silicon."""
    normalized = "large-v3-turbo" if model_id == "turbo" else model_id
    return f"mlx-community/whisper-{normalized}-mlx"
