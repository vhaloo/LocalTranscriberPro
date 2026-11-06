# Validation 3.7.0 — 2026-11-06

## Scope

Guided setup, purpose-based settings, contextual help, system-following interface language and preservation of manual choices. All prior recognition, conversation, speech, media, export, privacy, model-management and update functions remain. Model dependencies and language-quality claims are unchanged.

## Source and UI evidence

The release candidate adds pure policy coverage for settings migration, system-locale detection, the three automatic model priorities, manual-choice retention, language validation and bounds. A real Tk fixture checks all 63 core setting controls have contextual help, wizard Back/Cancel do not change preferences or text, the explicit level-only microphone test releases on navigation, busy application is rejected, reviewed application retains the conversation and does not call recording/inference, and restart retains chosen languages, profile, font and accessibility preferences. Translation preferences save without preparation.

Real workspace fixtures cover all five tasks at 1320×990 and 1024×768. Live transcript heights measure 468/246 px; file mode measures 626/404 px with the spoken-language selector visible. These layouts are measured on Windows at the tested scale. Seven genuine Windows screenshots use isolated demonstration data. The 4 GB catalogue is a simulated profile, not a physical low-memory benchmark.

Source tests, native packages, signed assets, installed runtime, update lifecycle and data-preservation results will be recorded here after the corresponding release gates finish. A draft document does not assert that pending release checks passed.

## Limits

The interface supports French and English; other system display languages fall back to English. Recognition, translation and voice languages have separate coverage. A level test verifies input amplitude only. Model scores remain indicative and confidence is uncalibrated; no new semantic reliability percentage is claimed. Virtual memory cannot exceed OS allocation limits. macOS/Linux remain experimental for physical installation, microphones, display and GPU behavior. SHA-256/Ed25519 integrity does not provide Windows Authenticode or Apple notarization.
