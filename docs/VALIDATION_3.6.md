# Validation 3.6.0 — 2026-11-05

## Scope

On-demand preparation of one selected recognizer, automatic full-accuracy CPU paging for small 64-bit computers, model retention after failed loads, per-model download/cancel/delete and offline MLX preparation. All previous user functions remain. No new per-language accuracy percentage is claimed.

## Source and desktop checks

- **283 tests pass on Windows; 281 pass with two Windows-only skips on macOS/Linux.** Compilation, Ruff, current release documentation and the complete language inventory pass.
- Real Tk fixtures cover five tasks at 1320×990 and 1024×768, model previews and the low-memory route, with zero model loads/downloads from navigation. On Windows, transcript heights remain 449/227 px in universal mode and 654/432 px in file mode at those two sizes.
- The UI fixture repeats Tiny download/delete using an isolated cache and a download transport stub; it verifies callbacks and no inference initialization. The real source/installed worker also exercises cached large-v3 preparation without requesting inference or adding catalogue models.
- Real large-v3 CPU recognition passes on OpenAI's public JFK audio. A simulated 4 GB profile retains full large-v3 with MADLAD French translation offline. Native model-load cancellation completes in the owned process while the parent remains usable. These are functional checks, not low-memory hardware or language-quality benchmarks.
- Six new Windows screenshots show the real interface with illustrative text. The memory example uses simulated hardware; no private conversation is published.

## Native package checks

The application/installer source was frozen at `0a816c8db06378fcd0bff71b9b74909dfafedd12`. Each native build runs six checks: Tiny CPU transcription, French and English bundled voices, controlled HTTP audio import, isolated CPU paging transcription and the native translation tokenizer in its owned worker. SentencePiece is pinned to the tested 0.2.2 runtime; Windows wheel sidecar DLLs are explicitly collected and exposed to native loading.

| Build | Evidence | Native checks |
|---|---|---|
| windows | [Run 41985860920](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41985860920) | 6/6 |
| windows_cpu | [Run 41985871757](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41985871757) | 6/6 |
| macos | [Run 41985882891](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41985882891) | 6/6 |
| linux | [Run 41985893623](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41985893623) | 6/6 |

The full and CPU Windows installers are also actually installed in CI, with source parity and the same six checks. Their preflight covers a simulated 2 GB machine. The exact macOS DMG and Linux archive/AppImage are inspected/extracted and exercised again in [package verification run 41990800011](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41990800011). That yields **48 successful native checks across eight build/installed/container groups**. Five binary assets are matched to SHA-256 and an Ed25519-signed manifest before delivery.

## Installed Windows and update checks

The verified full installer is installed at `E:\LocalTranscriberPro\Application`. All **62 source modules and five catalogues** match the candidate; the installed executable hash matches CI's actual installation. **13 local installed-runtime checks** pass: the six baseline checks, CUDA Tiny, legacy English translation, automatic large-v3, explicitly retained CPU large-v3, offline French translation, the download-only worker and large-v3 recognition with a simulated 4 GB profile. Existing cached models are reused; the catalogue set is unchanged.

The signed Windows update workflow is exercised with the actual installer: a real 60-second inactivity wait, signature/hash verification, `/WAITPID`, `/AUTOUPDATE`, the existing installation directory and relaunch of the installed executable. Only the release-query/HTTP transport uses a local fixture of the same verified assets, simulating a 3.5 client; the installer and lifecycle are real. Separate public-release checks verify actual URLs, manifest/signature, screenshots, current-version silence and preservation of the CPU-only update flavour.

All **84 existing sessions and 279 existing output files** are preserved. Prior settings, recovery content, shortcuts and session timestamps are checked after installation/relaunch; date comparisons use parsed instants. User data and models remain outside the replaced runtime.

## Limits

Virtual memory cannot force allocation beyond the OS commit limit; the app never changes swap/pagefile settings. Low-memory profiles are simulations, not physically constrained 2/4 GB machines. Large models can be extremely slow or fail for insufficient memory/disk. These checks establish functional behavior, not accuracy for every language/dialect. macOS/Linux remain experimental: physical installation, microphones, GPU and genuinely exhausted-memory environments are unverified. Apple notarization and Windows Authenticode are not provided; integrity uses SHA-256 and Ed25519 release manifests.
