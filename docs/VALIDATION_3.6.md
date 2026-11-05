# Validation 3.6.0 — 2026-11-05

## Scope

On-demand preparation of a single selected recognizer, automatic full-accuracy CPU paging for small 64-bit computers, checkpoint retention after failed loads and offline MLX preparation. Language/model weights and all previous user functions are retained. No new per-language accuracy percentage is claimed.

## Source and desktop checks

Release validation is in progress. Regression cases cover simulated 2/4/8 GB hardware, runtime/disk/forced-GPU guards, one selected downloader, cancellation, missing offline snapshots and network-free model/task navigation. The real Tk fixture checks all five tasks at 1320×990 and 1024×768, plus the low-memory route summary, with zero inference/download calls from navigation. Illustrative screenshots contain no private data. Native package and installed-runtime results will be recorded before publication.

## Limits

Virtual-memory permission cannot force an OS allocation beyond its commit limit. Low-memory profiles are simulations, not physical 2 GB hardware benchmarks. Native CPU loading provides functional evidence, not a language-quality or speed comparison. macOS/Linux are experimental; physical installation, microphones, GPU and genuinely exhausted-memory environments remain unverified. Model files and OS paging consume different storage budgets. The application never changes swap/pagefile settings.
