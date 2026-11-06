# Validation 3.7.0 — 2026-11-06

## Scope

Guided setup, purpose-based settings, contextual help, system-following interface language and preservation of manual choices. All prior recognition, conversation, speech, media, export, privacy, model-management and update functions remain. Model dependencies and language-quality claims are unchanged.

## Source and UI evidence

The release candidate adds pure policy coverage for settings migration, system-locale detection, the three automatic model priorities, manual-choice retention, language validation and bounds. A real Tk fixture checks all 63 core setting controls have contextual help, wizard Back/Cancel do not change preferences or text, the explicit level-only microphone test releases on navigation, busy application is rejected, reviewed application retains the conversation and does not call recording/inference, and restart retains chosen languages, profile, font and accessibility preferences. Translation preferences save without preparation.

Real workspace fixtures cover all five tasks at 1320×990 and 1024×768. Live transcript heights measure 468/246 px; file mode measures 626/404 px with the spoken-language selector visible. These layouts are measured on Windows at the tested scale. Seven genuine Windows screenshots use isolated demonstration data. The 4 GB catalogue is a simulated profile, not a physical low-memory benchmark.

**306 source tests pass on Windows; 304 pass with two Windows-only skips on macOS/Linux.** Compilation, Ruff, release documentation and the full language inventory pass. Linux CI exercises workspace, model management, quiet updates and guided setup on Xvfb. Additional Windows fixtures verify 23 silent per-line speech dispatches, all five tasks, audience language filtering, revision preservation, live language commands and private-session saving rules. No private conversation is used.

## Native package checks

Application/installer inputs are frozen at `306ca962978462ab9542c6c53a1de15408743012`. Native runs below share byte-identical application, installer and dependency inputs; later commits change workflows, tests and documentation. The macOS build runs at `769e8902ad377d5c2244d6c3ef0778d1358a6a47` using **macOS 15 arm64**, after the hosted macOS 14 runner retirement. Source CI at `b2cc6082571da028072ccce531f9b66316d6736e` also verifies all 15 retained settings toggles remain present in the settings pages. Every native build checks Tiny CPU transcription, French and English bundled voices, controlled HTTP audio import, isolated CPU paging and the native translation tokenizer in its owned worker. SentencePiece remains pinned to the validated 0.2.2 runtime with explicit Windows sidecar DLL collection.

| Build | Evidence | Native checks |
|---|---|---|
| windows | [Run 42211483379](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/42211483379) | 6/6 |
| windows_cpu | [Run 42206632724](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/42206632724) | 6/6 |
| linux | [Run 42206669166](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/42206669166) | 6/6 |
| macos | [Run 42207132344](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/42207132344) | 6/6 |

Both Windows installers are actually installed in CI and checked for source parity plus the same six runtime cases. Their installer preflight includes a simulated 2 GB profile. The exact macOS DMG and Linux AppImage/archive are mounted/extracted and exercised again in [verification run 42215987315](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/42215987315). **48 native checks pass across eight build/installed/container groups.** Five binary assets are verified against SHA-256 and an Ed25519-signed release manifest.

## Actual installed Windows and updates

The verified full installer replaces the existing runtime at `E:\LocalTranscriberPro\Application`. All **67 source modules and five catalogues** match the candidate. Its executable hash matches CI's installed executable. **13 local installed-runtime checks** pass: six baseline cases, CUDA Tiny, legacy English translation, automatic large-v3, explicitly retained CPU large-v3, offline French translation, download-only native preparation and full large-v3 recognition under a simulated 4 GB profile. Whisper large-v3 was absent from the current cache and was explicitly prepared through the installed cache-only worker before offline tests. No other recognizer was requested. The later model-store check reuses those weights and confirms its cached model set is unchanged. The actual installed GUI, settings and guided setup are also checked; cancelling the wizard preserves preferences and data.

The real signed Windows update lifecycle passes with **79.563 seconds of inactivity**, `/WAITPID`, `/AUTOUPDATE`, the existing installation directory and relaunch. A local transport exposes the same verified assets while the query simulates a 3.6 client; installer bytes, lifecycle and resulting installed application are real. Public URL/manifest/signature/image checks and current-version/CPU-flavour updater checks are separate final gates.

All **84 existing sessions and 279 output files** are preserved. Prior preferences are compared field by field through settings schema 9→10; recovery and shortcuts are verified. SQLite uses integrity and logical-content/date-instant comparisons after GUI relaunch, because raw page/header bytes can legitimately change. Models and user data remain outside the replaced runtime.

## Limits

The interface supports French and English; other system display languages fall back to English. Recognition, translation and voice languages have separate coverage. A level test verifies input amplitude only. Model scores remain indicative and confidence is uncalibrated; no new semantic reliability percentage is claimed. Virtual memory cannot exceed OS allocation limits. macOS/Linux remain experimental for physical installation, microphones, display and GPU behavior. SHA-256/Ed25519 integrity does not provide Windows Authenticode or Apple notarization.
