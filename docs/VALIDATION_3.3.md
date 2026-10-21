# Validation 3.3.0 — 2026-10-21

This release preserves all previous desktop functions and adds conversation review, audience display, typed replies, provisional live text, confidential sessions, offline preparation and signed manifests. The evidence below was collected on 21 October 2026 before stable publication.

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

The optional pinned MADLAD 7B model passed offline French/Arabic and Haitian Creole translation in the development runtime on this Windows machine. This verifies execution, not superiority of meaning over MADLAD 3B. Its relocated 8.33 GB cache was checked against the pinned hash and registered as the new optional cache setting. TranslateGemma access required external model authorization; Omnilingual 3B/7B lacked a native fairseq2n Windows wheel. Neither is silently installed or advertised as a validated automatic backend.

A two-second physical input-stream check received 32,768 samples with no overflow, without retaining or transcribing microphone audio. End-to-end ASR/translation/voice and installation checks are recorded below.

## Source and live conversation evidence

- 185 local regression tests pass, with Ruff, Python compilation, dependency consistency, release-document and complete-language-inventory checks.
- Actual Tk integration uses isolated settings/history. It verifies a 208-pixel transcript area in the normal 1320×990 layout, audience filtering, edits surviving worker snapshots, live language commands, final reviewed exports and confidential-mode autosave suppression.
- Controlled French synthesized speech and a public Jordanian Arabic test clip pass through the real recorder, neural VAD, recognition and MADLAD pipeline with network connections blocked. No ambient sound is captured or played. The Qwen 0.6B/CUDA run finalizes all 23.35 seconds, forms the French/Arabic pair, routes both directions, adds English and shows provisional text. An automatic-profile run with word timings selects Whisper large-v3 CPU alongside CUDA translation and finalizes all 23.12 seconds in four turns. Its previews are discarded when final audio is waiting: provisional display is best effort, not a latency guarantee.
- The same checks caught and fixed stale resource readings after MT loading, unscored Qwen language labels preventing pair formation and a possible unsupported live model switch. Qwen/Parakeet can now use the same pinned GlotLID text-language detector; missing/ambiguous hints retain manual confirmation. Combined ASR/MT memory reservation has explicit regression coverage.
- Paired edits preserve translations explicitly corrected with the original, while unchanged old translations are invalidated. Typed replies read their own destination text even when another turn finishes concurrently, and update existing completed exports. Logical Unicode survives manual bilingual TXT export.

These are execution and regression checks, not human certification of translation meaning. The controlled clips are not a representative multilingual conversation study.

## Expanded language diagnostics

[The complete 3.3 table](LANGUAGE_DIAGNOSTICS_3.3.md) publishes 280 scored Omnilingual clips across 35 groups and 168 scored Qwen 0.6B clips across 21 declared-coverage groups. The other 112 Qwen entries are explicitly outside its catalogue. Each scored group contains eight held-out clips. Only aggregate counters and input hashes are published.

Additional Whisper CPU runs were partial and are not presented as a balanced complete comparison. The optional CUDA int8_float16 diagnostic was refused by its actual free-VRAM guard while other applications remained open. It did not change the production automatic-model policy. The historical complete 70-clip comparison stays separately labelled; no 0.6B results are relabelled as Qwen 1.7B and no semantic reliability percentages are invented. Normalized language-route agreement does not certify Cantonese/Mandarin dialect identification.

## Exact native packages

All packages contain application source from `42b4a396c33929720e9ea0d32b69bb184d931404`. Subsequent documentation and diagnostic-output-folder changes do not alter `main.py`, `src`, the five packaged catalogues or runtime requirements.

| Package | Bytes | Native build |
|---|---:|---|
| Windows x64, CUDA + CPU | 2,105,748,466 | [39675495845](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39675495845) |
| Windows x64, CPU | 431,699,835 | [39675501078](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39675501078) |
| macOS arm64 experimental DMG | 591,513,496 | [39675505769](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39675505769) |
| Linux x86-64 experimental AppImage | 770,704,576 | [39675510704](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39675510704) |
| Linux x86-64 experimental archive | 765,743,458 | Same Linux build |

Native frozen CPU recognition, French/English bundled voices and isolated HTTP import pass in these builds. [Container inspection and draft delivery](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39680415074) mounts and verifies the ad-hoc-signed arm64 DMG, extracts and compares Linux containers, checks frozen source parity and reruns recognition/voices/HTTP import. All five exact assets remain below GitHub's 2 GiB limit. Remote asset sizes/digests and SHA-256 match the inspected files. Their Ed25519 manifest/signature verifies against the public key compiled into 3.3. Native Authenticode and Apple notarization are not provisioned.

## Local Windows upgrade and execution

The actual per-user installation was upgraded from 3.2.0 to 3.3.0 without elevation or Windows restart. The registry reports 3.3.0. Every one of 54 application modules and five catalogues matches the checked source; the installed executable SHA-256 is `d4973ffeb6ccef81bc1cefbee8b7217b487b813f2c88907cca4367135a947030`. The program folder occupies 5,340,784,017 bytes including its uninstaller, excluding model caches.

Before first launch, settings, editor recovery and SQLite bytes were unchanged; SQLite integrity and its 78 historical sessions match the checkpoint. All 249 pre-existing output files match their hashes. The optional 7B cache path was subsequently added as one new setting while preserving every existing setting value. The prior verified installer and small data/source checkpoints remain available for rollback.

Eleven installed executable checks pass: Tiny CPU, Tiny CUDA, Parakeet CPU, Qwen 0.6B CPU with word alignment, a 75-second stereo/gapped Qwen transcription with late timestamps, Whisper large-v3 CPU English translation, silence suppression, Omnilingual universal translation with the French/Arabic pair and English third language, bundled French and English synthesis, and isolated HTTP media import. The universal native check uses MADLAD 3B on CUDA. No unexpected backend substitution is accepted as proof of the requested model.

An additional installed public YouTube import of a short reference video succeeds on 21 October 2026, including download, conversion and Tiny CPU recognition. Temporary job audio is cleaned up. This does not guarantee future site access, restricted videos or every provider; explicit authentication and local-file alternatives remain available. No browser cookies were read for this test.

Source CI passes on all three systems: 185 tests on Windows; 184 passed and one Windows-only test skipped on macOS/Linux. macOS/Linux remain experimental: no physical microphone/GPU or human semantic-translation certification is claimed.
