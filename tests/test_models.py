from src.hardware import HardwareProfile
from src.models import AUTO_MODEL_ID, model_id_from_label, model_label


def profile(**values):
    defaults = dict(
        os_name="Windows",
        os_version="11",
        architecture="AMD64",
        cpu_name="Test CPU",
        cpu_threads=8,
        ram_gb=16,
    )
    defaults.update(values)
    return HardwareProfile(**defaults)


def test_model_labels_round_trip_in_both_languages():
    for language in ("en", "fr"):
        label = model_label("large-v3", language)
        assert model_id_from_label(label, language) == "large-v3"
        auto = model_label(AUTO_MODEL_ID, language)
        assert model_id_from_label(auto, language) == AUTO_MODEL_ID


def test_4gb_cpu_machine_gets_tiny_model():
    assert profile(ram_gb=4).recommended_model() == "tiny"


def test_large_gpu_gets_maximum_accuracy_model():
    hardware = profile(
        ram_gb=64,
        gpu_name="RTX 5070",
        gpu_vram_gb=12,
        nvidia_detected=True,
        ctranslate_cuda=True,
    )
    assert hardware.best_device == "cuda"
    assert hardware.recommended_model() == "large-v3"


def test_cpu_with_enough_memory_keeps_quality_first_default():
    assert profile(ram_gb=32).recommended_model() == "large-v3"
