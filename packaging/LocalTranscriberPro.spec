# -*- mode: python ; coding: utf-8 -*-

import os
import platform
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# SPECPATH is the directory containing this spec (repo/packaging).
ROOT = Path(SPECPATH).resolve().parent
datas = []
binaries = []
hiddenimports = [
    "faster_whisper.audio",
    "faster_whisper.vad",
    "speechbrain.inference.speaker",
    "speechbrain.lobes.models.ECAPA_TDNN",
    "speechbrain.processing.features",
    "speechbrain.dataio.encoder",
    "sklearn.cluster",
    "torchaudio.transforms",
    "whisper",
]
hiddenimports += collect_submodules("speechbrain")

# Do not let unrelated software earlier on a developer's PATH provide stale
# Visual C++/Windows debugging DLLs. PyTorch requires a mutually compatible
# runtime set, and the operating-system copies are the authoritative ones.
if platform.system() == "Windows":
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    for native_name in (
        "msvcp140.dll",
        "msvcp140_1.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "vcomp140.dll",
        "dbghelp.dll",
        "dbgcore.dll",
    ):
        native_path = system32 / native_name
        if native_path.exists():
            binaries.append((str(native_path), "."))

# Only collect runtime data. PyInstaller's dedicated hooks discover the code
# and native libraries for torch, sklearn, CTranslate2, PyAV and torchaudio.
# ``collect_all`` would also package their very large internal test suites.
for package in (
    "customtkinter",
    "tkinterdnd2",
    "faster_whisper",
    "imageio_ffmpeg",
    "certifi",
    "whisper",
    "speechbrain",
):
    try:
        datas += collect_data_files(package)
    except Exception:
        # MLX/OpenAI compatibility components are platform-specific and the
        # application retains a tested CTranslate2 fallback.
        pass

icon = ROOT / "assets" / ("icon.ico" if platform.system() == "Windows" else "icon.png")

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "packaging" / "runtime_hook.py")],
    excludes=["tensorflow", "jax", "matplotlib", "notebook", "IPython"],
    noarchive=False,
    optimize=1,
    module_collection_mode={"speechbrain": "py"},
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LocalTranscriberPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=str(ROOT / "entitlements.plist") if platform.system() == "Darwin" else None,
    icon=str(icon) if icon.exists() else None,
)

collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="LocalTranscriberPro",
)

if platform.system() == "Darwin":
    app = BUNDLE(
        collection,
        name="Local Transcriber Pro.app",
        icon=str(icon) if icon.exists() else None,
        bundle_identifier="com.vhaloo.localtranscriberpro",
        version="2.2.0",
        info_plist={
            "NSMicrophoneUsageDescription": "Local Transcriber Pro needs microphone access only when you start a recording.",
            "LSMinimumSystemVersion": "12.0",
            "NSHighResolutionCapable": True,
        },
    )
