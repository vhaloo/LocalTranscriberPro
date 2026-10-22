# Validation 3.3.1 — 2026-10-21

## Line reading and retained desktop functions

201 local tests pass. Source CI passes on all three systems: 201 tests on Windows; 200 passed and one Windows-only test skipped on macOS/Linux. Ruff, compilation, dependency consistency, release documentation and the complete language inventory pass. [Source CI](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39704303950).

Real Tk integration performs 23 silent speech dispatches across nine scenario groups: original/translation/third-language logical Unicode, audience filters and newly arriving languages, every task, both layouts, confidence on/off, selection, double-clicks, scrolling, disabled reading and edited-text readback. The normal transcript occupies 174 pixels at 1320×990. Existing paired revision, worker overlays, live language commands, reviewed exports and confidential autosave suppression also pass real Tk checks.

Windows mouse clicks invoke local speech from both windows with Num Lock enabled. This catches the native Windows modifier-bit difference that synthetic events initially missed. Regression checks cover this case, independent live/general settings, matching each line's language despite a manually selected foreign voice, missing-voice refusal, replacement and owned microphone pause/resume. Completion feedback retains playback errors. Three new screenshots use isolated illustrative Arabic/French/English text; no private conversation is published.

## Exact native packages

All five packages contain application code from `c9c490b29b79c8cb39d87c8dcf221ffab1761187`. The Windows installers use the repaired preflight from `af140fb41ae1351ddbd350032419c4219c889cbf` and pass full installation/installed-runtime checks in CI. Later documentation and QA-helper changes do not alter packaged code or requirements.

| Package | Bytes | Native build |
|---|---:|---|
| Linux x86-64 experimental AppImage | 770,577,600 | [39697802275](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39697802275) |
| Linux x86-64 experimental archive | 765,609,809 | [39697802275](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39697802275) |
| Windows x64, CPU | 431,497,289 | [39704298614](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39704298614) |
| Windows x64, CUDA + CPU | 2,105,611,824 | [39704295979](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39704295979) |
| macOS arm64 experimental DMG | 593,087,640 | [39697799456](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39697799456) |

Each native build passes CPU recognition, bundled French/English synthesis and isolated HTTP import. The first macOS attempt passed application checks but failed while creating its DMG with `Resource busy`; the second attempt succeeds. [Independent container inspection and delivery](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39708260328) verifies the mounted ad-hoc-signed arm64 DMG and extracted Linux containers, checks source parity and reruns recognition/voice/import checks. Every asset is below 2 GiB. Remote asset digests, SHA-256 and the Ed25519 manifest bind the five exact inspected files to the release.

macOS/Linux remain experimental. These checks do not establish physical microphone, speaker, display or GPU compatibility on those systems. Native Windows Authenticode and Apple notarization are not provisioned.

## Local Windows upgrade

The actual per-user installation was upgraded from 3.3.0 to 3.3.1 without elevation or a Windows restart. The application is installed on the fixed E: volume because C: had insufficient free installation space; Desktop and Start Menu shortcuts target the new location. Settings, models and transcripts retain their existing locations. The registry reports 3.3.1; every one of 55 application modules and five catalogues matches the release source. Installed executable SHA-256: `7ae5166515cf83d5d5ff99a424be297f7109d76dcd3639d90470f9e4171332e2`.

Before first GUI launch, settings, recovery and SQLite bytes match the checkpoint; database integrity and all 78 historical sessions are preserved. All 249 existing output files match their saved hashes. Existing model caches, including the optional MADLAD 7B path, remain available. The verified 3.3.0 installer and small source/data checkpoints are retained for rollback.

Six installed executable checks pass: Tiny CPU recognition, bundled French and English synthesis, isolated HTTP import, Tiny CUDA recognition, and French-to-English legacy Whisper translation on CUDA with the correct English text-language metadata. No unexpected backend substitution is accepted as proof. These are execution checks, not human translation or voice-quality certification.

## Model quality and coverage

This patch changes line reading and text/language association. It adds no new ASR/NMT model and does not relabel historical measurements. [Complete 3.3.0 validation](VALIDATION_3.3.0.md) retains prior larger-model, controlled-conversation, YouTube and installation evidence. [Expanded language diagnostics](LANGUAGE_DIAGNOSTICS_3.3.md) and the complete README catalogue retain their original model/corpus scope. Voice coverage is narrower than recognition/translation coverage; no reliability percentage is invented for unmeasured languages.
