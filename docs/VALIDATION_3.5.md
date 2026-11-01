# Validation 3.5.0 — 2026-11-01

## Source and retained functions

The frozen application commit is `e74c0ab62c608f78aec07c357ff141f96a7676b5`. Later documentation changes do not alter application modules, package definitions or runtime requirements. **253 tests pass locally and on Windows CI**; macOS/Linux pass 252 with one Windows-specific test skipped. Compilation, Ruff, release-documentation checks and the generated language inventory pass. [Three-platform source checks](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41287693144).

Real Tk checks cover all five tasks at 1320×990 and 1024×768, settings, literal/bounded/logical-Arabic search, F11/Escape, a language rebuild with the audience open, revision preservation, private autosave suppression and 23 silent per-line speech dispatches across nine groups. Empty-state guidance remains outside transcript/export text. Twelve current screenshots show the actual Windows interface with illustrative isolated data; the update-dialog screenshot uses a current-version fixture and performs no download. No private conversation is published.

The quiet-updater Tk fixture exercises offline/current startup checks without popups, a visible version/progress badge, background readiness while recording, private-text deferral, visible versus withdrawn settings and final idle handoff. Its transport, final validator and installer are recording stubs; actual signature/installation verification is described separately below.

## CPU virtual memory

Normal CPU/automatic RAM guards remain active. Explicit CPU paging bypasses physical/commit admission thresholds only, retaining runtime, disk, integrity and language/task checks. Unit cases reject silent replacement of the requested checkpoint, retain the chosen model across task changes/restarts, stop owned subprocesses and preserve each separated voice's language/confidence and bidirectional translation. Parent conversation language constraints are passed to the speech worker.

The native source runs Tiny and full Whisper large-v3 on isolated CPU with downloads disabled, and translates the Tiny English sample to French using isolated MADLAD CPU inference. The public 11-second sample reports 13.422 seconds of large-v3 source recognition and 13.735 seconds in the installed executable. These are execution checks, not comparative speed or multilingual quality benchmarks.

A real large-v3 load is cancelled at native initialization in 0.078 seconds; its worker disappears, the parent survives and no model is substituted. IPC uses authenticated local OS pipes/sockets, JSON and raw float32 frames without pickle or new conversation payload files. Windows launcher descendants and parent-exit cleanup are covered. The OS still controls memory commitment/pagefile/swap. No destructive RAM-exhaustion stress test or system-setting change is performed. Private application-file suppression cannot prevent OS paging.

## Native packages and exact assets

All four platform/flavor builds succeed from the frozen source:

- [windows: 41287787409](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41287787409)
- [windows_cpu: 41287790413](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41287790413)
- [macos: 41287793465](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41287793465)
- [linux: 41287796281](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41287796281)

Every native executable passes **five checks**: Tiny CPU recognition, bundled French and English voice synthesis, controlled HTTP import followed by offline recognition/temporary cleanup, and isolated CPU virtual-memory recognition. Windows full/CPU installers additionally pass preflight, silent CI installation, installed-source parity and those five checks again.

The local HTTP fixture now places transient imports in the OS temporary area and retains reports in the workspace. An initial workspace-based run removed the audio and metadata but left a read-only empty job directory; the same installed binary passes cleanup in the standard temporary area. Only the test fixture changed, and the inspected empty directory was removed safely. No application payload remained there.

[Experimental package verification and exact asset attachment](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/41290517536) verifies the mounted macOS DMG, its ad-hoc signature and arm64 architecture, plus the extracted Linux AppImage and portable archive, source parity and the native checks. All five exact assets are under GitHub's 2 GiB limit:

| Asset | Exact bytes | Decimal GB |
|---|---:|---:|
| `LocalTranscriberPro-3.5.0-Linux-x86_64-experimental.AppImage` | 774,292,672 | 0.774 |
| `LocalTranscriberPro-3.5.0-Linux-x86_64-experimental.tar.gz` | 769,182,455 | 0.769 |
| `LocalTranscriberPro-3.5.0-Windows-x64-CPU-Setup.exe` | 433,022,147 | 0.433 |
| `LocalTranscriberPro-3.5.0-Windows-x64-Setup.exe` | 2,107,108,888 | 2.107 |
| `LocalTranscriberPro-3.5.0-macOS-arm64-experimental.dmg` | 593,986,103 | 0.594 |

GitHub asset digests, SHA256SUMS and independently verified Ed25519 manifest entries agree for all five assets. The existing maintainer key is reused. These manifests do not provide Windows Authenticode or Apple notarization.

## Local installation, automatic handoff and user data

The signed full installer upgrades **`E:\LocalTranscriberPro\Application`** to **3.5.0**, with preflight success and installer exit code zero. The actual installed executable matches the CI-installed executable byte for byte; all **60 application modules and 5 catalogues** match the source. Full-runtime files total approximately 5.34 decimal GB before model caches. Both official shortcuts point to this executable.

**Ten actual installed-runtime checks pass:** Tiny CPU, French voice, English voice, controlled HTTP import, isolated Tiny CPU paging, Tiny CUDA, legacy French-to-English CUDA translation, automatic full Whisper large-v3, isolated full large-v3 CPU paging and isolated Tiny + MADLAD French translation. Requested models/devices and completed progress are asserted; silent substitutions are rejected.

A separate real automatic-installation run uses local transport for the exact official signed release files and simulates the previous version's query argument. The updater waits a real 62.2 seconds of app inactivity, downloads and verifies the signed bytes, checks final file/disk eligibility, saves, closes, invokes the actual installer with `/WAITPID` and `/AUTOUPDATE`, installs in the existing custom folder and relaunches the installed executable. The installer/log/new-process evidence confirms the handoff. The transport fixture does not claim that a draft was discoverable through the public endpoint; public update discovery is checked after publication.

The fresh pre-install checkpoint preserves **82 sessions and 269 existing output files**, SQLite integrity/logical content, settings and recovery. Files remain byte-identical through the first installer and CLI checks. The later GUI relaunch migrates settings to schema 9 while retaining every prior preference. Its legacy-history refresh changes the displayed UTC offset for 51 dates across the daylight-saving transition; their instants are identical, as is every other session field. All original output hashes and recovery content are preserved. Model caches and the active development environment remain intact. Local retention keeps the five newest verified version sets after publication.

## Scope and limits

macOS arm64 and Linux x86-64 remain **experimental**. Automated source/native/container checks do not establish physical microphone, speaker, GPU or installation reliability on those systems. macOS is ad-hoc signed, not notarized; no Intel Mac package is supplied. Mac/Linux replacement remains manual from the official release page. Windows idle installation is separately switchable and defers active tasks, visible dialogs or private text.

No ASR/NMT weights or language catalogue changed. Historical [language diagnostics](LANGUAGE_DIAGNOSTICS_3.3.md) and [3.4 validation](VALIDATION_3.4.md) retain their original scope. No per-language semantic-reliability percentages are invented; catalogue scores and model indices retain their documented limits.
