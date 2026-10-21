# Validation 3.3.0 — 2026-10-21

This release preserves all previous desktop functions and adds conversation review, audience display, typed replies, provisional live text, confidential sessions, offline preparation and signed manifests. Validation is in progress on the release branch; this document is completed with final evidence before publication.

## Scope and methodology

- Original recordings and references from FLEURS, Casablanca and CMU stay in ignored local evaluation folders. No private conversation or licensed dataset audio is bundled or published.
- The expanded held-out manifest contains 280 clips, eight per 35 language/corpus groups. This is a diagnostic sample, not population-level reliability or human interpretation certification.
- ASR diagnostics block network connections during model loading and inference. A fallback aborts the requested-model comparison instead of being scored under the wrong model name.
- Character/word error rates measure normalized text against references. They are not percentages of correct meaning. No semantic-translation reliability percentage is invented.
- Functional UI tests use illustrative Arabic/French/English text and isolated settings/history. Real screenshots identify this demonstration.
- macOS/Linux packages remain experimental. CI cannot establish physical microphone, display or GPU compatibility on untested machines.

## New regression coverage

Stable turn IDs, review overlays during capture, atomic language commands, preserved prior routing, selective retranslation, stale-result rejection, provisional scheduling, numeric review, encrypted Unicode round trips, tamper/wrong-password rejection and Ed25519 manifest binding are covered alongside retained tests.

## Native checks

The optional pinned MADLAD 7B model passed offline French/Arabic and Haitian Creole translation on this Windows machine. This verifies execution, not superiority of meaning over MADLAD 3B. TranslateGemma access required external model authorization; Omnilingual 3B/7B lacked a native fairseq2n Windows wheel. Neither is silently installed or advertised as a validated automatic backend.

A two-second physical input-stream check received 32,768 samples with no overflow, without retaining or transcribing microphone audio. End-to-end ASR/translation/voice and install checks are recorded separately below when complete.
