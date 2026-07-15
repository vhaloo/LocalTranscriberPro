"""Cross-platform hardware discovery without assuming optional AI packages."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import asdict, dataclass
from typing import Any

import psutil

from src.models import AUTO_MODEL_ID


@dataclass
class HardwareProfile:
    os_name: str
    os_version: str
    architecture: str
    cpu_name: str
    cpu_threads: int
    ram_gb: float
    gpu_name: str = ""
    gpu_vram_gb: float = 0.0
    nvidia_detected: bool = False
    ctranslate_cuda: bool = False
    torch_cuda: bool = False
    apple_silicon: bool = False
    mlx_available: bool = False
    torch_mps: bool = False

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

    def recommended_model(self) -> str:
        """Select the largest safe model, never merely the fastest one."""
        if self.best_device == "cuda":
            if self.gpu_vram_gb >= 7.0 and self.ram_gb >= 12:
                return "large-v3"
            if self.gpu_vram_gb >= 5.0 and self.ram_gb >= 8:
                return "large-v3-turbo"
            if self.gpu_vram_gb >= 4.0:
                return "medium"
            if self.gpu_vram_gb >= 2.0:
                return "small"
            return "base"
        if self.best_device == "metal":
            if self.ram_gb >= 16:
                return "large-v3"
            if self.ram_gb >= 8:
                return "large-v3-turbo"
            return "base"
        # CPU can run large-v3 when memory permits. This is intentionally the
        # maximum-quality default even when it is slow, as requested.
        if self.ram_gb >= 16:
            return "large-v3"
        if self.ram_gb >= 8:
            return "medium"
        if self.ram_gb >= 5:
            return "small"
        return "tiny"

    def resolve_model(self, requested: str) -> str:
        return self.recommended_model() if requested == AUTO_MODEL_ID else requested

    def compute_type(self, device: str) -> str:
        if device == "cuda":
            return "float16" if self.gpu_vram_gb >= 10 else "int8_float16"
        return "int8"

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


def _nvidia_details() -> tuple[str, float]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        first = result.stdout.strip().splitlines()[0]
        name, memory = [part.strip() for part in first.rsplit(",", 1)]
        return name, float(memory) / 1024.0
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return "", 0.0


def detect_hardware() -> HardwareProfile:
    machine = platform.machine().lower()
    apple_silicon = platform.system() == "Darwin" and machine in {"arm64", "aarch64"}
    gpu_name, gpu_vram = _nvidia_details()

    ct2_cuda = False
    try:
        import ctranslate2

        ct2_cuda = ctranslate2.get_cuda_device_count() > 0
    except (ImportError, RuntimeError, OSError):
        pass

    torch_cuda = False
    torch_mps = False
    try:
        import torch

        torch_cuda = bool(torch.cuda.is_available())
        torch_mps = bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
        if torch_cuda and not gpu_name:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
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

    return HardwareProfile(
        os_name=platform.system(),
        os_version=platform.release(),
        architecture=platform.machine(),
        cpu_name=_cpu_name(),
        cpu_threads=psutil.cpu_count(logical=True) or 1,
        ram_gb=psutil.virtual_memory().total / 1024**3,
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram,
        nvidia_detected=bool(gpu_name) and not apple_silicon,
        ctranslate_cuda=ct2_cuda,
        torch_cuda=torch_cuda,
        apple_silicon=apple_silicon,
        mlx_available=mlx_available,
        torch_mps=torch_mps,
    )
