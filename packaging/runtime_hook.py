"""Prepare native AI library search paths before application imports."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

_DLL_DIRECTORY_HANDLES: list[object] = []


if getattr(sys, "frozen", False) and platform.system() == "Windows":
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    native_directories = (
        bundle_root / "torch" / "lib",
        bundle_root / "torchaudio" / "lib",
        bundle_root / "ctranslate2",
    )
    available = [str(path) for path in native_directories if path.is_dir()]
    if available:
        os.environ["PATH"] = os.pathsep.join(available + [os.environ.get("PATH", "")])
        for directory in available:
            try:
                _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(directory))
            except (AttributeError, FileNotFoundError, OSError):
                pass
