"""Reviewable settings plans; no model, microphone or network operations."""
from __future__ import annotations

from dataclasses import dataclass

from src.models import AUTO_FAST_MODEL_ID, AUTO_MODEL_ID, AUTO_MULTILINGUAL_MODEL_ID
from src.settings import bounded_int
from src.translation_languages import LANGUAGE_BY_CODE

PROFILES = {"best": AUTO_MODEL_ID, "fast": AUTO_FAST_MODEL_ID, "coverage": AUTO_MULTILINGUAL_MODEL_ID}
TASKS = ("files", "universal", "conference", "dictation", "link")


@dataclass
class SetupAnswers:
    preset: str = "files"
    profile: str = "best"
    ui_language: str = "auto"
    spoken_language: str = "auto"
    translate: bool = False
    target: str = "fr"
    partner: str = "auto"
    third: str = "none"
    microphone: str = "auto"
    font_size: int = 22
    keep_audio: bool = True
    speakers: bool = False
    click_speech: bool = False
    advanced: bool = False
    chunk_seconds: int = 30
    effort: int = 8

    @classmethod
    def from_settings(cls, settings):
        task = settings.get("preset", "files")
        model = settings.get("model", AUTO_MODEL_ID)
        profile = next((name for name, value in PROFILES.items() if value == model), "keep")
        if settings.get("device", "auto") != "auto":
            profile = "keep"
        return cls(preset=task, profile=profile, ui_language=settings.get("ui_language", "auto"),
                   spoken_language=settings.get("spoken_language", "auto"),
                   translate=task == "universal" or settings.get("translate", False),
                   target=settings.get("translation_target", "fr"),
                   partner=settings.get("conversation_partner", "auto"), third=settings.get("translation_third", "none"),
                   microphone=settings.get("microphone", "auto"), font_size=settings.get("conversation_font_size", 22),
                   keep_audio=settings.get("keep_recording_audio", True), speakers=settings.get("speaker_detection", False),
                   click_speech=settings.get("speech_click_live" if task == "universal" else "speech_click", task == "universal"),
                   advanced=settings.get("ui_mode", "simple") == "advanced",
                   chunk_seconds=settings.get("chunk_seconds", 30), effort=settings.get("beam_size", 8))


def setup_plan(answers: SetupAnswers) -> dict:
    """Only preferences shown in the wizard may be changed by its Apply action."""
    if answers.preset not in TASKS or answers.profile not in {*PROFILES, "keep"}:
        raise ValueError("Invalid task or model profile")
    if answers.ui_language not in {"auto", "fr", "en"}:
        raise ValueError("Invalid interface language")
    if answers.spoken_language != "auto" and answers.spoken_language not in LANGUAGE_BY_CODE:
        raise ValueError("Invalid spoken language")
    if answers.target not in LANGUAGE_BY_CODE or answers.partner not in {"auto", *LANGUAGE_BY_CODE}:
        raise ValueError("Invalid conversation language")
    if answers.third not in {"none", *LANGUAGE_BY_CODE}:
        raise ValueError("Invalid third language")
    if answers.preset == "universal" and answers.partner == answers.target:
        raise ValueError("setup_invalid_languages")
    result = {
        "preset": answers.preset, "ui_language": answers.ui_language,
        "ui_mode": "advanced" if answers.advanced else "simple",
        "spoken_language": "auto" if answers.preset == "universal" else answers.spoken_language,
        "translate": answers.preset == "universal" or answers.translate,
        "translation_target": answers.target, "conversation_partner": answers.partner,
        "translation_third": answers.third, "microphone": answers.microphone,
        "conversation_font_size": bounded_int(answers.font_size, 22, 14, 48),
        "keep_recording_audio": bool(answers.keep_audio),
        "speaker_detection": bool(answers.speakers) if answers.preset != "universal" else False,
        "speech_click_live" if answers.preset == "universal" else "speech_click": bool(answers.click_speech),
        "guided_setup_done": True,
        "chunk_seconds": bounded_int(answers.chunk_seconds, 30, 5, 60),
        "beam_size": bounded_int(answers.effort, 8, 1, 10),
    }
    if answers.profile in PROFILES:
        result.update(model=PROFILES[answers.profile], device="auto",
                      simple_quality="fast" if answers.profile == "fast" else "best")
    return result
