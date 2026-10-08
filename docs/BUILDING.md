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
python -m ruff check main.py src tests scripts
python scripts/check_release_docs.py
python -m pytest
```

`requirements-dev.txt` includes the pinned modern ASR engines. Install `requirements-diarization.txt` to include speaker labeling. On Apple Silicon, install `requirements-macos.txt` to include MLX.

## Windows

Keep the tested `av==18.0.0` pin from `requirements.txt`. [PyAV 19 removed `metadata_errors`](https://github.com/PyAV-Org/PyAV/releases/tag/v19.0.0), which faster-whisper 1.2.1 still passes when decoding audio. Unconstrained fresh installations failed frozen transcription checks on macOS/Linux; the delivered Windows 3.1.0 installer already contains PyAV 18.0.0. Real WAV/FLAC decoder tests now catch this dependency break before packaging.

`scripts/build_windows.ps1` creates the PyInstaller application folder. Inno Setup 6 then compiles `packaging/windows/installer.iss` into a per-user installer.

For direct PyInstaller builds, run `python scripts/prepare_js_runtime.py` and `python scripts/prepare_default_voices.py` first. The installer includes Node and the yt-dlp EJS solver, so online-video users need no separate JavaScript setup. [yt-dlp's official EJS guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS) documents this dependency. Public video access can still depend on YouTube's availability, regional restrictions and server policies.

## macOS

The build workflow creates `Local Transcriber Pro.app`, adds the microphone usage description, applies an ad-hoc signature for artifact integrity, and packages it in a DMG. Production distribution should replace ad-hoc signing with Developer ID signing and notarization.

The experimental 3.1.0 DMG is arm64 for Apple Silicon, built on macOS 14. No Intel package is provided. See [experimental distribution instructions](EXPERIMENTAL_DESKTOP_3.1.md).

## Linux

The build workflow creates an AppImage and a portable tar archive. The AppImage contains the application runtime; model files remain external and are downloaded to the user's cache on first use.

The experimental 3.1.0 packages target x86-64 and are built on Ubuntu 24.04 with a CPU PyTorch runtime. Other distributions and GPU inference are unverified.

## Release procedure

1. Update the code/project/installer/macOS versions, README download/title, changelog, current validation and conversation guides.
2. Capture the real updated interface with illustrative data, save the screenshot under `docs/images`, and update `current-release.json` with version and SHA-256. Do not publish private transcripts.
3. Run `scripts/check_release_docs.py`, Ruff and tests. CI rejects stale versions, download links, documentation or screenshot metadata.
4. Build the native package, run `scripts/verify_frozen_source.py` and `scripts/validate_frozen.py`, then test installation/upgrade/relaunch and data preservation on the target OS. Keep reports and a rollback checkpoint.
5. Create an annotated `v3.x.y` tag. The desktop workflow builds native packages and tests frozen CPU ASR plus bundled voices; it creates a **draft** release with checksums. It preserves an existing verified release rather than overwriting its assets.
6. Publish stable platform assets after installation and runtime verification. An explicitly authorized experimental platform distribution may be published earlier with `experimental` filenames/labels, architecture, checksums and precise validation limits. Before making a release latest, check exact filenames and hashes, README screenshots and updater discovery. Windows 3.1.0 remains stable; macOS/Linux 3.1.0 are experimental and physical installation validation is not claimed.

`experimental-package-check.yml` can check successful desktop-build artifacts directly: mount and verify the final Mac DMG/signature, extract the Linux AppImage, compare its executable to the portable archive, verify packaged source/catalogues and run offline CPU ASR plus bundled voices. These checks improve experimental release confidence without claiming GUI, microphone, GPU or physical installation validation.

The version 1 rollback point is the immutable `archive-v1.1-before-v2.0` tag.

## Windows GPU build

Install a compatible PyTorch/torchaudio wheel before the diarization pack (the current tested pair is `2.11.0+cu128` for both). Install `openai-whisper==20250625` for the compatibility fallback. Run `python -m pip check` before packaging. The spec ships Nagisa Python sources because its Japanese preprocessing uses sibling module imports; omitting them silently forces Qwen to fall back.

After building, exercise the real frozen stack with `LocalTranscriberPro.exe --smoke-test sample.wav --model auto-best --device auto --language fr --diagnostic-output report.json`. Inspect the reported backend and fallback reason; nonempty text alone does not prove the requested engine worked. Add `--task translate`, `--diarize` or `--expect-silence` for those checks.

The updater requires the exact asset name `LocalTranscriberPro-X.Y.Z-Windows-x64-Setup.exe` and a same-release `SHA256SUMS.txt`. Pre-releases and draft releases are ignored. Publish only after Windows installation/upgrade/relaunch testing and platform-specific validation. Local packaging does not publish a GitHub release.

Every GitHub asset must be under 2 GiB. Verify the installer size before upload. Do not publish an oversized or renamed older binary. For local builds, `AppSource` can override the Inno source directory when using a fresh output path to avoid stale/locked native files.

Pass the resolved absolute `AppSource` path when the checkout path is long. Unresolved `packaging/windows/../../...` prefixes can push otherwise valid filenames over the compiler's Windows path limit. The native bundle's files must remain complete; shortening the source path is preferable to deleting dependencies.
