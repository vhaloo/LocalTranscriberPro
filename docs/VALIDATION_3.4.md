# Validation 3.4.0 — 2026-10-30

## Source, interface and model policy

The frozen application commit is `77ce96cd7cc924de9d33993a39cc016b4af2dc6a`. Later release documentation does not change the application, packaging definition or runtime requirements. The installed Windows executable matches its CI-installed executable byte for byte; all **58 source modules and 5 catalogues** match the release source.

**219 tests pass locally and on Windows CI.** macOS arm64 and Linux x86-64 pass 218 tests with one platform-specific test skipped. Ruff, compilation, release-documentation checks and the generated full language inventory pass. [Three-platform source validation](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41149882497).

Actual Tk checks cover all five tasks at 1320×990 and 1024×768, closed-at-start settings, numeric normalization, literal/bounded/logical-Arabic search, current-match preservation, F11/Escape and a language rebuild with the audience window open. Empty guidance never enters transcript/export text. Windows live transcript height is 449/227 pixels and file height is 654/432; Linux's Xvfb run measures 452/230 and 657/435. These controlled layouts are not a promise for every DPI, font or desktop environment.

Twenty-three silent speech dispatches across nine scenario groups retain selection, language mapping, filtering and microphone-pause ownership. Real Windows UI clicks complete French playback in the main transcript and English playback from the audience display. Paired review, worker overlays, private autosave suppression, final exports and reading restoration pass. Ten current screenshots show the actual Windows interface with isolated demonstration text; no private conversation is published.

The source auto-best route transcribes the controlled public 11-second sample offline with full **Whisper large-v3**, faster-whisper CPU int8, no substituted model and completed progress, reporting 12.734 seconds of recognition time. GPU memory was occupied by other applications; admission retained the full checkpoint on CPU. The default is a local OpenAI provider preference; the other recognizers, speed and maximum-coverage profiles remain available. This is an execution check, not a multilingual accuracy or speed benchmark.

Cross-platform validation exposed a native macOS crash when the old cleanup path entered PyTorch's MPS allocator before any Metal model had used it. Cleanup now enters that allocator only for an actual admitted PyTorch Metal model. CPU/MLX and unavailable-MPS regression cases pass, followed by fresh macOS source and packaged CPU tests. Physical Metal acceleration remains unverified.

## Native packages and exact assets

All four platform/flavor builds succeed from the frozen app source:

- [windows: 41149882127](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41149882127)
- [windows_cpu: 41149884578](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41149884578)
- [macos: 41149887166](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41149887166)
- [linux: 41149889732](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41149889732)

Each native executable passes CPU Tiny recognition, bundled French and English offline voice synthesis, and an isolated local HTTP audio import followed by offline recognition and temporary-file cleanup. Windows full and CPU installers also pass the real installer preflight, silent CI installation, installed-source parity and those four checks again.

[Container verification and exact draft attachment](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41153202997) verifies the mounted macOS DMG, its ad-hoc signature and arm64 architecture, plus the extracted Linux AppImage and portable archive. Their contained applications pass source parity and the same native checks. Each of the five exact distribution assets is under GitHub's 2 GiB limit:

| Asset | Exact bytes | Decimal GB |
|---|---:|---:|
| `LocalTranscriberPro-3.4.0-Linux-x86_64-experimental.AppImage` | 774,292,672 | 0.774 |
| `LocalTranscriberPro-3.4.0-Linux-x86_64-experimental.tar.gz` | 769,176,923 | 0.769 |
| `LocalTranscriberPro-3.4.0-Windows-x64-CPU-Setup.exe` | 432,981,649 | 0.433 |
| `LocalTranscriberPro-3.4.0-Windows-x64-Setup.exe` | 2,107,112,368 | 2.107 |
| `LocalTranscriberPro-3.4.0-macOS-arm64-experimental.dmg` | 594,519,563 | 0.595 |

SHA-256 values agree between downloaded artifacts, GitHub asset digests and the release checksum file. The existing maintainer Ed25519 key signs a manifest covering all five assets; the application's independent public-key verifier accepts every entry. The signature does not supply Windows Authenticode or Apple notarization.

## Local Windows upgrade and user data

The full verified installer upgrades **`E:\LocalTranscriberPro\Application`** to **3.4.0**, with exit code zero. Its native wizard/hardware preflight succeeds before copying. The installed full-runtime marker retains CUDA support. Runtime files total approximately 5.34 decimal GB before model caches. Both official Desktop/Start-menu shortcuts point to this executable.

**Seven actual installed-runtime checks pass:** Tiny CPU, French voice, English voice, controlled HTTP import, Tiny CUDA, legacy French-to-English CUDA translation, and auto-best full large-v3 on CPU. Requested engines/models are checked explicitly; silent substitutions are rejected. The large-v3 check reports 12.891 seconds for the public 11-second sample, with no model fallback.

A fresh pre-installation checkpoint verifies SQLite integrity and preserves **82 existing sessions and 269 existing output files**. Settings, recovery and history files remain byte-identical through the installer and CLI checks; history also matches its logical SQLite dump. These checks precede the user's next normal GUI launch, which may legitimately migrate the settings schema. No existing transcript or model cache is pruned. Local retention keeps the five newest version sets after successful publication.

## Scope and limits

macOS arm64 and Linux x86-64 remain **experimental distributions**. Automated native CPU/voice/container checks and a Linux source GUI check do not establish physical microphone, speaker, GPU or installation reliability on those systems. macOS is ad-hoc signed and not notarized; no Intel Mac package is provided. macOS/Linux updates remain manual replacement from the release page. Windows keeps its verified signed-manifest updater and preserves full/CPU flavor selection.

No recognition/translation weights or language catalogue changed in this interface/default-policy release. Historical [3.3 language diagnostics](LANGUAGE_DIAGNOSTICS_3.3.md) and [3.3.1 validation](VALIDATION_3.3.md) retain their original scope. No per-language semantic reliability percentages are invented. Relative catalogue scores remain editorial guides; model confidence captions are uncalibrated and optional.
