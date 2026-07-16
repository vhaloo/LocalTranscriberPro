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


def test_unsafe_manual_model_is_replaced_by_largest_safe_choice():
    hardware = profile(ram_gb=4, available_ram_gb=2, disk_free_gb=20)
    compatibility = hardware.model_compatibility("large-v3", "cpu")
    assert not compatibility.supported
    assert compatibility.reason_code == "ram"
    assert hardware.resolve_model("large-v3", "cpu") == "tiny"


def test_busy_machine_temporarily_disables_models_that_need_free_memory():
    hardware = profile(ram_gb=32, available_ram_gb=2, disk_free_gb=20)
    compatibility = hardware.model_compatibility("large-v3", "cpu")
    assert not compatibility.supported
    assert compatibility.temporary
    assert compatibility.reason_code == "available_ram"
    assert hardware.recommended_model("cpu") == "small"


def test_forced_gpu_model_is_blocked_when_vram_is_too_small():
    hardware = profile(
        ram_gb=32,
        available_ram_gb=20,
        gpu_name="Small NVIDIA GPU",
        gpu_vram_gb=4,
        gpu_vram_free_gb=4,
        nvidia_detected=True,
        ctranslate_cuda=True,
    )
    compatibility = hardware.model_compatibility("large-v3", "cuda")
    assert not compatibility.supported
    assert compatibility.reason_code == "vram"
    assert hardware.model_compatibility("medium", "cuda").supported


def test_first_download_needs_enough_free_storage():
    hardware = profile(ram_gb=4, available_ram_gb=2, disk_free_gb=0.2)
    compatibility = hardware.model_compatibility("tiny", "cpu", model_downloaded=False)
    assert not compatibility.supported
    assert compatibility.reason_code == "disk"
    assert hardware.model_compatibility("tiny", "cpu", model_downloaded=True).supported


def test_apple_mlx_route_does_not_depend_on_cpu_backend_probe():
    hardware = profile(
        os_name="Darwin",
        architecture="arm64",
        ram_gb=16,
        available_ram_gb=10,
        apple_silicon=True,
        mlx_available=True,
        cpu_backend_available=False,
    )
    compatibility = hardware.model_compatibility("large-v3", "metal")
    assert compatibility.supported
    assert compatibility.device == "metal"
