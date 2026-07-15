# Building and releasing

## Supported build environment

- Python 3.12, 64-bit
- Windows x64, macOS 12+ or Linux x86-64
- Git and enough disk space for PyTorch and packaging (10+ GB recommended)

## Local validation

```text
python -m pip install -r requirements-dev.txt
python -m compileall -q main.py src tests
python -m ruff check main.py src tests
python -m pytest
```

Install `requirements-diarization.txt` to include speaker labeling. On Apple Silicon, install `requirements-macos.txt` to include MLX.

## Windows

`scripts/build_windows.ps1` creates the PyInstaller application folder. Inno Setup 6 then compiles `packaging/windows/installer.iss` into a per-user installer.

## macOS

The build workflow creates `Local Transcriber Pro.app`, adds the microphone usage description, applies an ad-hoc signature for artifact integrity, and packages it in a DMG. Production distribution should replace ad-hoc signing with Developer ID signing and notarization.

## Linux

The build workflow creates an AppImage and a portable tar archive. The AppImage contains the application runtime; model files remain external and are downloaded to the user's cache on first use.

## Release procedure

1. Ensure the validation workflow is green on the release commit.
2. Create an annotated `v2.x.y` tag.
3. Push the tag.
4. The desktop build workflow packages all three systems, generates `SHA256SUMS.txt`, and creates the public GitHub release.
5. Download each artifact and smoke-test launch before marking the release as the recommended version.

The version 1 rollback point is the immutable `archive-v1.1-before-v2.0` tag.
