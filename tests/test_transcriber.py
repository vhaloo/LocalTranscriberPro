from src.hardware import HardwareProfile
from src.models import AUTO_MODEL_ID
from src.transcriber import EngineStatus, TranscriberEngine


def test_preloaded_engine_reports_when_recording_is_armed():
    hardware = HardwareProfile(
        os_name="Windows",
        os_version="11",
        architecture="AMD64",
        cpu_name="Test CPU",
        cpu_threads=4,
        ram_gb=16,
        available_ram_gb=10,
    )
    engine = TranscriberEngine(hardware)
    engine.model = object()
    engine.model_name = "large-v3"
    engine.device = "cpu"
    engine.backend = "faster-whisper"
    engine.current_status = EngineStatus(
        model_id="large-v3",
        requested_device="cpu",
        device="cpu",
        backend="faster-whisper",
        compute_type="int8",
        requested_model_id=AUTO_MODEL_ID,
    )

    assert engine.is_ready(AUTO_MODEL_ID, "cpu")
    assert not engine.is_ready("large-v3", "cpu")
    assert engine.load_model(AUTO_MODEL_ID, "cpu") is engine.current_status
