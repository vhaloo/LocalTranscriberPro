# Validation 3.2.0 — 2026-10-17

Version 3.2 preserves the recognition/translation models, language catalogues and decoding policy from 3.1. The new work targets help, storage inspection, online-media acquisition and packaging verification. The [35-group multilingual diagnostics from 3.1](VALIDATION_3.1.md) remain historical small-sample measurements; they were not rerun or relabelled as new reliability percentages.

## Source and UI checks

- All 159 Windows tests passed locally in 19.96 seconds, with Ruff, compilation and `pip check` also passing. The [three-platform source CI](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39056964623) passed on Windows, macOS and Linux. Source checks cover the retained features and new real-worker HTTP audio import, stalled-server cancellation, unreadable audio, owned-job cleanup, cookie export preservation and URL validation.
- Engine checks cover official repository/tag/assets, announced size, SHA-256, cancellation, retained previous files on failure and re-verification before launch.
- Storage checks cover custom paths, hardlink deduplication, bounded scans and skipping directory links, including links passed as the scan root.
- The actual French interface was opened with isolated settings/history and illustrative Arabic/French/English text. Reading enlargement, selected speech lines, font limits, clipboard content and editable-text/confidence preservation passed the GUI self-check. Storage and video panels were inspected; current screenshots are in `docs/images`.
- Version, README download links, changelog, current guides, screenshot hashes and the complete generated language inventory are release gates. No semantic reliability percentages were invented.

## Real online import, 17 October 2026

| Case | Result | Temporary audio |
|---|---|---|
| Public YouTube clip, included yt-dlp 2026.10.10.233141 | Passed; decodable audio | 309,156 bytes, M4A; 5.95 s |
| Same clip, independently updated official engine | Passed; decodable audio | 309,156 bytes, M4A; 9.28 s |
| Public direct HTTPS FLAC sample | Passed; decodable audio | 1,152,693 bytes; 4.86 s |
| Vimeo sample URL, no cookies | Authentication/verification requested; actionable error shown | No retained temporary audio |

The optional official Windows engine was downloaded as 17,842,237 bytes, matched the same-release SHA-256 manifest and passed re-verification before use. The test left no owned temporary jobs. These are acquisition/decoding checks, not speech-quality or all-site benchmarks. Internet conditions, content availability, authentication, geoblocking and server verification can change. The Vimeo sample required authentication/verification without cookies; authenticated Vimeo access was not validated. Other extractors are not individually certified by these cases.

## Storage estimates

Decimal GB: about 5.9 GB with Tiny; 12 GB free installation headroom; 14.4 GB with Omnilingual and translation; 44 GB of application/model/voice files for the current catalogue and an 85 GB prudent preparation/cache budget. PCM16 mono 16 kHz capture adds 115,200,000 bytes/hour. Hub duplication/revisions and recordings prevent an absolute maximum. Estimates are conservative Windows budgets; the UI measures actual local files and reports incomplete scans.

## Native runtime checks

The final Windows bundle passes source parity for all 44 application modules and all four JSON catalogues, offline Tiny CPU recognition, both included Piper voices, and an isolated HTTP import followed by offline recognition. A real public YouTube import also passes with the **bundled** engine in the actual windowed executable, with nonempty transcription and completed progress; temporary audio is removed.

The hardware accuracy profile loads **Qwen3-ASR 1.7B on NVIDIA CUDA, float16, without fallback**. An earlier native test exposed invalid console handles when checkpoint progress bars flushed; the final package redirects incidental console output to valid null streams before library imports. The regression test reproduces missing/invalid streams using the actual progress-bar library. The repeat native test uses the intended Qwen backend successfully.

Universal mode passes a local Omnilingual ONNX CPU transcription into a manually fixed French/Arabic pair, Arabic translation and an English third-language record, with MADLAD on CUDA and offline prepared models. This is functional smoke coverage, not a new language-quality benchmark or a guarantee of conversational latency.

[Final macOS native build](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39056962498) and [final Linux native build](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39056965733) pass packaged CPU ASR, French/English voices and isolated HTTP import. The [final DMG/AppImage/portable-archive inspection](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/39057771146) also passes on both platforms: mounted Mac image/signature/architecture, Linux executable parity, all packaged source/catalogues and four native checks per OS.

## Native distribution checks

Before publication the release procedure requires frozen-source parity, CPU offline recognition, included French/English voices, a real isolated HTTP import into offline Tiny recognition, installer size/checksum and Windows upgrade/data-preservation checks. Native reports are kept as release evidence. macOS arm64 and Linux x86-64 remain experimental: physical installation, microphone operation, GUI and GPU acceleration are not claimed by automated checks. [Platform guide](EXPERIMENTAL_DESKTOP_3.2.md).

Recognition/translation models, voices and their limitations are documented in the [conversation guide](TRANSLATION.md), [language guide](LANGUAGES.md) and [complete README inventory](../README.md#langues). An index displayed on 100 is not a calibrated probability that the meaning is correct.

## Windows upgrade and preservation

The 3.2.0 per-user installer completed the actual 3.1.0 → 3.2.0 upgrade on Windows, without a Windows restart. The installed-version registry reports 3.2.0. All **7,691 application files** match the built package byte-for-byte (5,324,692,173 bytes of runtime files), with no missing, changed or obsolete extra runtime files. The installed executable SHA-256 is `393f728edf34b1f89ab46279ce5a3c82a79d66e0081ea949e37a415954daa898`.

All **231 existing output files** retain their hashes. Settings, recovery and the SQLite file retain their hashes; the 74-session history passes its integrity check and logical-dump comparison. A consistent local data checkpoint and the verified 3.1.0 installer are retained for rollback. Model/voice caches remain outside the replaced runtime.

The Windows installer is 2,105,695,957 bytes (SHA-256 `4c7a6f6a889f7a719f6b27fcf5151f9274c66323315363bd0770c44c3b720268`), under GitHub’s 2 GiB asset limit. Mac/Linux assets are also below that limit and have same-release SHA-256 entries. The source/UI checks and native/container checks above have distinct scopes; no physical Mac/Linux installation, microphone or GPU validation is implied.
