# Building and releasing

## Supported build environment

- Python 3.12, 64-bit
- Windows x64, macOS 12+ or Linux x86-64
- Git and enough disk space for PyTorch and packaging (25+ GB recommended)
- Node >=22 on the build machine; its runtime and exact-version license are included in desktop packages

## Local validation

```text
python -m pip install -r requirements-dev.txt
python -m compileall -q main.py src tests
python -m ruff check main.py src tests
python -m pytest
```

`requirements-dev.txt` includes the pinned modern ASR engines. Install `requirements-diarization.txt` to include speaker labeling. On Apple Silicon, install `requirements-macos.txt` to include MLX.

## Windows

`scripts/build_windows.ps1` creates the PyInstaller application folder. Inno Setup 6 then compiles `packaging/windows/installer.iss` into a per-user installer.

For direct PyInstaller builds, run `python scripts/prepare_js_runtime.py` first. The installer includes Node and the yt-dlp EJS solver, so online-video users need no separate JavaScript setup. [yt-dlp's official EJS guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS) documents this dependency. Public video access can still depend on YouTube's availability, regional restrictions and server policies.

## macOS

The build workflow creates `Local Transcriber Pro.app`, adds the microphone usage description, applies an ad-hoc signature for artifact integrity, and packages it in a DMG. Production distribution should replace ad-hoc signing with Developer ID signing and notarization.

## Linux

The build workflow creates an AppImage and a portable tar archive. The AppImage contains the application runtime; model files remain external and are downloaded to the user's cache on first use.

## Release procedure

1. Ensure the validation workflow is green on the release commit.
2. Create an annotated `v3.x.y` tag.
3. Push the tag.
4. The desktop build workflow packages all three systems, generates `SHA256SUMS.txt`, and creates the public GitHub release.
5. Download each artifact and smoke-test launch before marking the release as the recommended version.

The version 1 rollback point is the immutable `archive-v1.1-before-v2.0` tag.

## Windows GPU build

Install a compatible PyTorch/torchaudio wheel before the diarization pack (the current tested pair is `2.11.0+cu128` for both). Install `openai-whisper==20250625` for the compatibility fallback. Run `python -m pip check` before packaging. The spec ships Nagisa Python sources because its Japanese preprocessing uses sibling module imports; omitting them silently forces Qwen to fall back.

After building, exercise the real frozen stack with `LocalTranscriberPro.exe --smoke-test sample.wav --model auto-best --device auto --language fr --diagnostic-output report.json`. Inspect the reported backend and fallback reason; nonempty text alone does not prove the requested engine worked. Add `--task translate`, `--diarize` or `--expect-silence` for those checks.

The updater requires the exact asset name `LocalTranscriberPro-X.Y.Z-Windows-x64-Setup.exe` and a same-release `SHA256SUMS.txt`. Pre-releases and draft releases are ignored. Publish only after Windows installation/upgrade/relaunch testing and platform-specific validation. Local packaging does not publish a GitHub release.
