# Validation 3.2.0 — 2026-10-17

Version 3.2 preserves the recognition/translation models, language catalogues and decoding policy from 3.1. The new work targets help, storage inspection, online-media acquisition and packaging verification. The [35-group multilingual diagnostics from 3.1](VALIDATION_3.1.md) remain historical small-sample measurements; they were not rerun or relabelled as new reliability percentages.

## Source and UI checks

- Windows source checks cover the retained features and new real-worker HTTP audio import, stalled-server cancellation, unreadable audio, owned-job cleanup, cookie export preservation and URL validation.
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

The optional official Windows engine was downloaded as 17,842,237 bytes, matched the same-release SHA-256 manifest and passed re-verification before use. The test left no owned temporary jobs. These are acquisition/decoding checks, not speech-quality or all-site benchmarks. Internet conditions, content availability, authentication, geoblocking and server verification can change. Vimeo and all other extractors are not individually certified by these cases.

## Storage estimates

Decimal GB: about 5.9 GB with Tiny; 12 GB free installation headroom; 14.4 GB with Omnilingual and translation; 44 GB of application/model/voice files for the current catalogue and an 85 GB prudent preparation/cache budget. PCM16 mono 16 kHz capture adds 115,200,000 bytes/hour. Hub duplication/revisions and recordings prevent an absolute maximum. Estimates are conservative Windows budgets; the UI measures actual local files and reports incomplete scans.

## Native distribution checks

Before publication the release procedure requires frozen-source parity, CPU offline recognition, included French/English voices, a real isolated HTTP import into offline Tiny recognition, installer size/checksum and Windows upgrade/data-preservation checks. Native reports are kept as release evidence. macOS arm64 and Linux x86-64 remain experimental: physical installation, microphone operation, GUI and GPU acceleration are not claimed by automated checks. [Platform guide](EXPERIMENTAL_DESKTOP_3.2.md).

Recognition/translation models, voices and their limitations are documented in the [conversation guide](TRANSLATION.md), [language guide](LANGUAGES.md) and [complete README inventory](../README.md#langues). An index displayed on 100 is not a calibrated probability that the meaning is correct.
