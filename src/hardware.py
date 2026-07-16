"""Cross-platform hardware discovery and crash-resistant model admission."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import psutil
from platformdirs import user_cache_dir

from src.models import AUTO_MODEL_ID, MODEL_CATALOG, ModelSpec, get_model

HardwareStatusCallback = Callable[[str, float], None]


@dataclass(frozen=True)
class ModelCompatibility:
    model_id: str
    supported: bool
    device: str
    reason_code: str = "ready"
    temporary: bool = False
    required: float = 0.0
    detected: float = 0.0


@dataclass
class HardwareProfile:
    os_name: str
    os_version: str
    architecture: str
    cpu_name: str
    cpu_threads: int
    ram_gb: float
    available_ram_gb: float = 0.0
    swap_gb: float = 0.0
    disk_free_gb: float = 1000.0
    gpu_name: str = ""
    gpu_vram_gb: float = 0.0
    gpu_vram_free_gb: float = 0.0
    nvidia_driver: str = ""
    nvidia_detected: bool = False
    ctranslate_cuda: bool = False
    torch_cuda: bool = False
    apple_silicon: bool = False
    mlx_available: bool = False
    torch_mps: bool = False
    cpu_backend_available: bool = True
    cpu_compute_types: tuple[str, ...] = ()

    @property
    def effective_available_ram_gb(self) -> float:
        return self.available_ram_gb if self.available_ram_gb > 0 else self.ram_gb

    @property
    def effective_free_vram_gb(self) -> float:
        return self.gpu_vram_free_gb if self.gpu_vram_free_gb > 0 else self.gpu_vram_gb

    @property
    def gpu_available(self) -> bool:
        return self.ctranslate_cuda or self.torch_cuda or self.mlx_available or self.torch_mps

    @property
    def best_device(self) -> str:
        if self.nvidia_detected and (self.ctranslate_cuda or self.torch_cuda):
            return "cuda"
        if self.apple_silicon and (self.mlx_available or self.torch_mps):
            return "metal"
        return "cpu"

    @property
    def display_device(self) -> str:
        if self.best_device == "cuda":
            return self.gpu_name or "NVIDIA GPU"
        if self.best_device == "metal":
            return self.gpu_name or "Apple Silicon"
        return "CPU"

    @staticmethod
    def normalize_device(device_mode: str) -> str:
        value = (device_mode or "auto").lower()
        if "cuda" in value or "nvidia" in value:
            return "cuda"
        if "mps" in value or "metal" in value or "apple" in value:
            return "metal"
        if "cpu" in value or "processeur" in value:
            return "cpu"
        return "auto"

    def _disk_check(self, spec: ModelSpec, model_downloaded: bool) -> ModelCompatibility | None:
        if model_downloaded or self.disk_free_gb >= spec.download_space_gb:
            return None
        return ModelCompatibility(
            spec.model_id,
            False,
            "",
            "disk",
            required=spec.download_space_gb,
            detected=self.disk_free_gb,
        )

    def _cpu_compatibility(self, spec: ModelSpec) -> ModelCompatibility:
        if not self.cpu_backend_available:
            return ModelCompatibility(spec.model_id, False, "cpu", "cpu_runtime")
        if self.ram_gb < spec.ram_gb:
            return ModelCompatibility(
                spec.model_id, False, "cpu", "ram", required=spec.ram_gb, detected=self.ram_gb
            )
        if self.effective_available_ram_gb < spec.available_ram_gb:
            return ModelCompatibility(
                spec.model_id,
                False,
                "cpu",
                "available_ram",
                temporary=True,
                required=spec.available_ram_gb,
                detected=self.effective_available_ram_gb,
            )
        return ModelCompatibility(spec.model_id, True, "cpu")

    def _cuda_compatibility(self, spec: ModelSpec) -> ModelCompatibility:
        if not self.nvidia_detected or not (self.ctranslate_cuda or self.torch_cuda):
            return ModelCompatibility(spec.model_id, False, "cuda", "gpu_runtime")
        if self.ram_gb < spec.gpu_system_ram_gb:
            return ModelCompatibility(
                spec.model_id,
                False,
                "cuda",
                "ram",
                required=spec.gpu_system_ram_gb,
                detected=self.ram_gb,
            )
        host_available = min(2.0, spec.available_ram_gb)
        if self.effective_available_ram_gb < host_available:
            return ModelCompatibility(
                spec.model_id,
                False,
                "cuda",
                "available_ram",
                temporary=True,
                required=host_available,
                detected=self.effective_available_ram_gb,
            )
        if self.gpu_vram_gb < spec.vram_gb:
            return ModelCompatibility(
                spec.model_id,
                False,
                "cuda",
                "vram",
                required=spec.vram_gb,
                detected=self.gpu_vram_gb,
            )
        if self.effective_free_vram_gb < spec.vram_gb:
            return ModelCompatibility(
                spec.model_id,
                False,
                "cuda",
                "available_vram",
                temporary=True,
                required=spec.vram_gb,
                detected=self.effective_free_vram_gb,
            )
        return ModelCompatibility(spec.model_id, True, "cuda")

    def _metal_compatibility(self, spec: ModelSpec) -> ModelCompatibility:
        if not self.apple_silicon or not (self.mlx_available or self.torch_mps):
            return ModelCompatibility(spec.model_id, False, "metal", "gpu_runtime")
        if self.ram_gb < spec.ram_gb:
            return ModelCompatibility(
                spec.model_id,
                False,
                "metal",
                "ram",
                required=spec.ram_gb,
                detected=self.ram_gb,
            )
        if self.effective_available_ram_gb < spec.available_ram_gb:
            return ModelCompatibility(
                spec.model_id,
                False,
                "metal",
                "available_ram",
                temporary=True,
                required=spec.available_ram_gb,
                detected=self.effective_available_ram_gb,
            )
        return ModelCompatibility(spec.model_id, True, "metal")

    def model_compatibility(
        self,
        model_id: str,
        device_mode: str = "auto",
        model_downloaded: bool = False,
    ) -> ModelCompatibility:
        spec = get_model(model_id)
        disk_problem = self._disk_check(spec, model_downloaded)
        if disk_problem:
            return disk_problem

        device = self.normalize_device(device_mode)
        if device == "cpu":
            return self._cpu_compatibility(spec)
        if device == "cuda":
            return self._cuda_compatibility(spec)
        if device == "metal":
            return self._metal_compatibility(spec)

        checks: list[ModelCompatibility] = []
        if self.nvidia_detected:
            checks.append(self._cuda_compatibility(spec))
        if self.apple_silicon:
            checks.append(self._metal_compatibility(spec))
        checks.append(self._cpu_compatibility(spec))
        for check in checks:
            if check.supported:
                return check
        temporary = next((check for check in checks if check.temporary), None)
        return temporary or checks[-1]

    def safe_models(
        self,
        device_mode: str = "auto",
        cached_model_ids: Iterable[str] = (),
    ) -> list[str]:
        cached = set(cached_model_ids)
        return [
            spec.model_id
            for spec in MODEL_CATALOG
            if self.model_compatibility(spec.model_id, device_mode, spec.model_id in cached).supported
        ]

    def recommended_model(
        self,
        device_mode: str = "auto",
        cached_model_ids: Iterable[str] = (),
    ) -> str:
        cached = set(cached_model_ids)
        candidates = sorted(
            (spec for spec in MODEL_CATALOG if spec.multilingual),
            key=lambda spec: spec.quality_rank,
            reverse=True,
        )
        for spec in candidates:
            if self.model_compatibility(spec.model_id, device_mode, spec.model_id in cached).supported:
                return spec.model_id
        return "tiny"

    def fast_recommended_model(
        self,
        device_mode: str = "auto",
        cached_model_ids: Iterable[str] = (),
    ) -> str:
        cached = set(cached_model_ids)
        for model_id in ("large-v3-turbo", "medium", "small", "base", "tiny"):
            if self.model_compatibility(model_id, device_mode, model_id in cached).supported:
                return model_id
        return self.recommended_model(device_mode, cached)

    def has_safe_model(self, device_mode: str = "auto", cached_model_ids: Iterable[str] = ()) -> bool:
        return bool(self.safe_models(device_mode, cached_model_ids))

    def resolve_model(
        self,
        requested: str,
        device_mode: str = "auto",
        cached_model_ids: Iterable[str] = (),
    ) -> str:
        cached = set(cached_model_ids)
        if requested == AUTO_MODEL_ID:
            return self.recommended_model(device_mode, cached)
        compatibility = self.model_compatibility(requested, device_mode, requested in cached)
        if compatibility.supported:
            return requested
        return self.recommended_model(device_mode, cached)

    def compute_type(self, device: str) -> str:
        if device == "cuda":
            return "float16" if self.gpu_vram_gb >= 10 else "int8_float16"
        return "int8"

    def refresh_resources(self) -> None:
        memory = psutil.virtual_memory()
        self.available_ram_gb = memory.available / 1024**3
        self.swap_gb = psutil.swap_memory().total / 1024**3
        self.disk_free_gb = _cache_disk_free_gb()
        if self.nvidia_detected:
            _, total, free, driver = _nvidia_details()
            if total:
                self.gpu_vram_gb = total
            if free:
                self.gpu_vram_free_gb = free
            if driver:
                self.nvidia_driver = driver

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cpu_name() -> str:
    name = platform.processor().strip()
    if name:
        return name
    if platform.system() == "Windows":
        return os.environ.get("PROCESSOR_IDENTIFIER", "CPU")
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return result.stdout.strip() or "CPU"
    except (OSError, subprocess.SubprocessError):
        return "CPU"


def _nvidia_details() -> tuple[str, float, float, str]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        first = result.stdout.strip().splitlines()[0]
        name, total, free, driver = [part.strip() for part in first.rsplit(",", 3)]
        return name, float(total) / 1024.0, float(free) / 1024.0, driver
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return "", 0.0, 0.0, ""


def _cache_disk_free_gb() -> float:
    cache = Path(user_cache_dir("LocalTranscriberPro", "Vhaloo"))
    target = next((path for path in (cache, *cache.parents) if path.exists()), Path.home())
    try:
        return shutil.disk_usage(target).free / 1024**3
    except OSError:
        return 0.0


def detect_hardware(status_callback: HardwareStatusCallback | None = None) -> HardwareProfile:
    def report(stage: str, progress: float) -> None:
        if status_callback:
            status_callback(stage, progress)

    report("hardware_memory", 0.26)
    machine = platform.machine().lower()
    apple_silicon = platform.system() == "Darwin" and machine in {"arm64", "aarch64"}
    memory = psutil.virtual_memory()
    ram_gb = memory.total / 1024**3
    available_ram_gb = memory.available / 1024**3
    swap_gb = psutil.swap_memory().total / 1024**3
    disk_free_gb = _cache_disk_free_gb()

    report("hardware_gpu", 0.38)
    gpu_name, gpu_vram, gpu_vram_free, nvidia_driver = _nvidia_details()

    report("hardware_engine", 0.50)
    ct2_cuda = False
    cpu_backend_available = False
    cpu_compute_types: tuple[str, ...] = ()
    try:
        import ctranslate2

        cpu_compute_types = tuple(sorted(ctranslate2.get_supported_compute_types("cpu")))
        cpu_backend_available = bool(cpu_compute_types)
        ct2_cuda = ctranslate2.get_cuda_device_count() > 0
    except (ImportError, RuntimeError, OSError):
        pass

    report("hardware_acceleration", 0.62)
    torch_cuda = False
    torch_mps = False
    try:
        import torch

        torch_cuda = bool(torch.cuda.is_available())
        torch_mps = bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
        if torch_cuda and not gpu_name:
            gpu_name = torch.cuda.get_device_name(0)
            properties = torch.cuda.get_device_properties(0)
            gpu_vram = properties.total_memory / 1024**3
            gpu_vram_free = gpu_vram
    except (ImportError, RuntimeError, OSError):
        pass

    mlx_available = False
    if apple_silicon:
        try:
            import mlx_whisper  # noqa: F401

            mlx_available = True
        except (ImportError, RuntimeError, OSError):
            pass

    if apple_silicon and not gpu_name:
        gpu_name = f"Apple {platform.machine()}"

    report("hardware_ready", 0.70)
    return HardwareProfile(
        os_name=platform.system(),
        os_version=platform.release(),
        architecture=platform.machine(),
        cpu_name=_cpu_name(),
        cpu_threads=psutil.cpu_count(logical=True) or 1,
        ram_gb=ram_gb,
        available_ram_gb=available_ram_gb,
        swap_gb=swap_gb,
        disk_free_gb=disk_free_gb,
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram,
        gpu_vram_free_gb=gpu_vram_free,
        nvidia_driver=nvidia_driver,
        nvidia_detected=bool(gpu_name) and not apple_silicon,
        ctranslate_cuda=ct2_cuda,
        torch_cuda=torch_cuda,
        apple_silicon=apple_silicon,
        mlx_available=mlx_available,
        torch_mps=torch_mps,
        cpu_backend_available=cpu_backend_available,
        cpu_compute_types=cpu_compute_types,
    )
