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
python scripts/generate_language_readme.py --check
python -m pytest
```

`requirements-dev.txt` includes the pinned modern ASR engines. Install `requirements-diarization.txt` to include speaker labeling. On Apple Silicon, install `requirements-macos.txt` to include MLX.

## Windows

Keep the tested `av==18.0.0` pin from `requirements.txt`. [PyAV 19 removed `metadata_errors`](https://github.com/PyAV-Org/PyAV/releases/tag/v19.0.0), which faster-whisper 1.2.1 still passes when decoding audio. Unconstrained fresh installations failed frozen transcription checks on macOS/Linux; the delivered Windows 3.1.0 installer already contains PyAV 18.0.0. Real WAV/FLAC decoder tests now catch this dependency break before packaging.

`scripts/build_windows.ps1` creates the PyInstaller application folder. Inno Setup 6 then compiles `packaging/windows/installer.iss` into a per-user installer.

For direct PyInstaller builds, run `python scripts/prepare_js_runtime.py` and `python scripts/prepare_default_voices.py` first. The installer includes Node and the yt-dlp EJS solver, so online-video users need no separate JavaScript setup. [yt-dlp's official EJS guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS) documents this dependency. Public video access can still depend on YouTube's availability, regional restrictions and server policies.

## macOS

The build workflow creates `Local Transcriber Pro.app`, adds the microphone usage description, applies an ad-hoc signature for artifact integrity, and packages it in a DMG. Production distribution should replace ad-hoc signing with Developer ID signing and notarization.

The experimental 3.4.0 DMG is arm64 for Apple Silicon, built on macOS 14. No Intel package is provided. See [experimental distribution instructions](EXPERIMENTAL_DESKTOP_3.4.md).

## Linux

The build workflow creates an AppImage and a portable tar archive. The AppImage contains the application runtime; model files remain external and are downloaded to the user's cache on first use.

The experimental 3.2.0 packages target x86-64 and are built on Ubuntu 24.04 with a CPU PyTorch runtime. Other distributions and GPU inference are unverified.

## Release procedure

1. Update the code/project/installer/macOS versions, README download/title, changelog, current validation and conversation guides. After changing language/model/voice catalogues, refresh the sourced documentation snapshots as needed and run `python scripts/generate_language_readme.py` to update every embedded README list. Keep unmeasured reliability explicitly labelled.
2. Capture the real updated interface with illustrative data, save the screenshot under `docs/images`, and update `current-release.json` with version and SHA-256. Do not publish private transcripts.
3. Run `scripts/check_release_docs.py`, `scripts/generate_language_readme.py --check`, Ruff and tests. CI rejects stale versions, download links, language inventories, documentation or screenshot metadata.
4. Build the native package, run `scripts/verify_frozen_source.py` and `scripts/validate_frozen.py`, then test installation/upgrade/relaunch and data preservation on the target OS. Keep reports and a rollback checkpoint.
5. Create an annotated `v3.x.y` tag. The desktop workflow builds native packages and tests frozen CPU ASR plus bundled voices; it creates a **draft** release with checksums. It preserves an existing verified release rather than overwriting its assets.
6. Publish stable platform assets after installation and runtime verification. An explicitly authorized experimental platform distribution may be published earlier with `experimental` filenames/labels, architecture, checksums and precise validation limits. Before making a release latest, check exact filenames and hashes, README screenshots and updater discovery. Windows 3.2.0 remains stable; macOS/Linux 3.2.0 are experimental and physical installation validation is not claimed.

`experimental-package-check.yml` can check successful desktop-build artifacts directly: mount and verify the final Mac DMG/signature, extract the Linux AppImage, compare its executable to the portable archive, verify packaged source/catalogues and run offline CPU ASR plus bundled voices. These checks improve experimental release confidence without claiming GUI, microphone, GPU or physical installation validation.

The version 1 rollback point is the immutable `archive-v1.1-before-v2.0` tag.

## Local build file retention

Keep one current source checkout, its working development environment, a verified current installer and at most five versioned rollback sets in total, including the current version. The installed application, prepared model/voice caches, transcripts, settings, history and recovery data are separate from temporary packaging output and must be preserved.

After a successful verified installation and publication, old `build/` output, superseded unpacked applications in `dist/`, duplicate installer downloads, old update installers and extracted inspection copies can be removed. Keep small installation/data checkpoints and validation reports. Before removing an artifact, confirm its exact path, its role and the retained installer or published asset; do not follow junctions or symlinks into model caches or the development environment. Preserve uncommitted or unique source changes before consolidating checkouts.

The current build path is `scripts/build_windows.ps1`, `packaging/LocalTranscriberPro.spec`, the Inno Setup definition and the native desktop workflow. Previous 0.x/1.x application copies and standalone/download installer builders are available through Git history or archived releases; they are no longer shipped beside the current source.

## Windows GPU build

Install a compatible PyTorch/torchaudio wheel before the diarization pack (the current tested pair is `2.11.0+cu128` for both). Install `openai-whisper==20250625` for the compatibility fallback. Run `python -m pip check` before packaging. The spec ships Nagisa Python sources because its Japanese preprocessing uses sibling module imports; omitting them silently forces Qwen to fall back.

After building, exercise the real frozen stack with `LocalTranscriberPro.exe --smoke-test sample.wav --model auto-best --device auto --language fr --diagnostic-output report.json`. Inspect the reported backend and fallback reason; nonempty text alone does not prove the requested engine worked. Add `--task translate`, `--diarize` or `--expect-silence` for those checks.

The updater requires the exact asset name `LocalTranscriberPro-X.Y.Z-Windows-x64-Setup.exe` (or `-CPU-Setup.exe` for that installed flavor), a same-release `SHA256SUMS.txt` and valid `release-manifest.json`/`release-manifest.sig`. Pre-releases and draft releases are ignored. Publish only after Windows installation/upgrade/relaunch testing and platform-specific validation. Local packaging does not publish a GitHub release.

## Separate CPU packages and release signing — 3.3

`desktop-build.yml` supports `windows`, `windows-cpu`, `macos`, `linux` and `all`. The CPU job uses CPU PyTorch wheels and sets `LTP_CPU_ONLY=1` before PyInstaller; the spec writes the matching runtime marker, and Inno's `CPUOnly` definition creates the distinct installer filename. The full Windows package retains CUDA. For a local build on another disk, `scripts/build_windows.ps1 -OutputRoot E:\LocalTranscriberPro-build` keeps large build/dist output off the system drive.

After native checks, `experimental-package-check.yml` can inspect Mac/Linux containers and attach all five exact package artifacts to an existing empty draft, using their completed run IDs. It verifies sizes and hashes before and after upload and will not replace a conflicting asset or publish the draft. Download the resulting exact packages, verify them against `SHA256SUMS.txt`, then run:

```text
python scripts/sign_release.py VERIFIED_PACKAGE_FOLDER --key PRIVATE_KEY_PATH --version 3.4.0
```

The raw 32-byte Ed25519 private key must remain outside Git, logs, artifacts and packaged files. The verifier's public key must match that key before building. Upload only the resulting public manifest and signature, with the matching checksum manifest. Do not regenerate a key during a retry. Check all published asset bytes against the signed manifest after publication. Independent update signatures do not supply Authenticode or Apple notarization; those need separately provisioned certificates.

Every GitHub asset must be under 2 GiB. Verify the installer size before upload. Do not publish an oversized or renamed older binary. For local builds, `AppSource` can override the Inno source directory when using a fresh output path to avoid stale/locked native files.

Pass the resolved absolute `AppSource` path when the checkout path is long. Unresolved `packaging/windows/../../...` prefixes can push otherwise valid filenames over the compiler's Windows path limit. The native bundle's files must remain complete; shortening the source path is preferable to deleting dependencies.

## Video import validation (3.2)

The bundled yt-dlp nightly is pinned in requirements. Changes must preserve EJS and the bundled JavaScript runtime. `main.py --video-worker` dispatches before logging/GUI/model initialization; JSONL file IPC is required because windowed Windows executables have no stdout. `validate_frozen.py` runs an actual packaged HTTP import against a local server, followed by Tiny CPU offline recognition and temporary-job cleanup, in addition to direct ASR and bundled voices. Public-site tests are recorded separately because site access is time-dependent.

Before release, compare `catalogue_budget()` and the installer/README estimates with actual installed and asset sizes. Keep GB decimal and distinguish files, installation headroom, cache duplication and unlimited recordings. The storage inspector never follows links or deletes data. Independent engine updates must remain restricted to the official yt-dlp nightly repository and verified metadata/checksums.


## Workspace regression checks (3.4)

Run `python scripts/qa_workspace.py` with isolated data and no model/microphone load; Linux CI uses Xvfb. It checks all tasks at 1320×990 and 1024×768, settings, literal/bounded/Arabic search, reading restoration and language rebuild with the audience open. Also retain `qa_click_speech.py`, `qa_conversation33.py` and the original GUI self-check. Native source and installed-runtime checks complement these UI tests. Keep at most the five most recent verified local versions after a successful upgrade; never prune the active runtime, model caches or current user data.
