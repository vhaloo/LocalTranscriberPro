# Local Transcriber Pro 3.0 — validation

Windows validation combines source tests, real inference in the frozen Windows package and source desktop UI checks. Final installation is checked by comparing installed files with that package and verifying the user's preserved data. The application retains all 2.2 workflows: file/video batches and folder drops, microphone recording/pause/stop, conference speaker labels, dictation, YouTube, language detection and English translation, VAD, subtitle sidecars, five export formats, editable text, vocabulary, history, recovery and manual model/device choice.

## Automated source checks

The suite covers resource admission and missing runtimes, free-memory zero values, language/translation compatibility, real inference/model replacement serialization, cancellation, stereo chunk decoding/timeline offsets, microphone overflow preservation, WAV flushing, atomic concurrent writes, malformed settings/recovery, editor corrections/full rewrites in every export, contiguous subtitle numbering, partial-batch continuation and exact update asset/size/checksum validation. Installer invocation and bundled JavaScript discovery are checked independently.

## Runtime checks

Real French and English human samples from the Sherpa model repository are used, with a 75-second stereo fixture containing those samples at 0, 30 and 60 seconds, plus a 32-second silent fixture. Tests verify the actual backend and fallback reason, text, final progress and long-media offsets. Qwen 1.7B and 0.6B, Parakeet CPU and Whisper GPU are exercised. Translation routes to Whisper. Cached inference is run with `HF_HUB_OFFLINE=1`.

Source YouTube download testing uses a short publicly accessible clip with the bundled JavaScript runtime, without login, cookies or browser credential access. A separate online check in the installed GUI was not completed; the user requested final installation without further GUI testing. Failed/deleted videos are reported instead of being considered inference failures.

The real Xbox NUI microphone is exercised through the source desktop UI: start, pause, resume, stop, final ASR and five automatic exports. The verified WAV is mono PCM16 at 16 kHz and contains 21.44 seconds of captured audio, excluding the paused interval. This verifies the physical capture route without representing a multi-speaker meeting. The multilingual selector's FR layout and separate score columns are visually inspected; the catalogue order and default Accuracy profile are checked separately.

Final installation succeeded with exit code 0 and no Windows restart. All 7,305 installed package files match their SHA-256 manifest. The user's 70 history sessions, 2,324 recovery segments and prior preferences are preserved; migrated settings enable startup update checks and the Accuracy profile. A Windows `WinError 448` on cached model symlinks affected the initial installer relaunch. The 44 affected cached links were replaced with NTFS hard links to the same unchanged blobs, with their original link metadata saved. Relaunch from the delivery shell then opened the installed GUI and loaded Qwen3-ASR 1.7B on CUDA successfully. The ready state was inspected on screen; computer control was released immediately afterwards.

## Scope and practical limits

- This local validation targets Windows 11 x64, Ryzen 7 5800X, 64 GB RAM and RTX 5070 12 GB. macOS, Linux and Apple MPS/MLX need their own hardware validation.
- Short human samples prove inference and integration, not a universal model ranking. A synthetic French fixture produced weaker Parakeet spelling, so the Accuracy profile continues to favor Qwen/Whisper.
- Word timing for Qwen is available in the forced aligner's 11 languages; other Qwen languages use approximate window timing. Explicitly select complementary languages to route to Whisper.
- Speaker labels are estimates, do not identify a person and can be imperfect with overlap/noise. No physical multi-speaker meeting is represented by the single-speaker fixture.
- Newer official releases are proposed only when published with the expected installer and checksum. Download integrity/cancellation and installer invocation are covered by source tests. The native installer waits for the retiring application process before replacing its files. The complete in-app update acceptance cycle was not re-exercised after that fix; the final installation is performed directly in the background.
- GUI inspection used isolated QA settings/history. Final installation verifies the installed package, startup and the user's preserved settings without further computer control. Production transcripts were backed up before migration.

The local delivery report and JSON runtime evidence are under `artifacts/`. The prior installation, source bundle and settings checkpoint are under `artifacts/checkpoint-2.2.0/`.
