# Changelog

## 2.2.0

- Added conservative model admission based on total/free RAM, total/free VRAM, disk space, architecture and proven CPU/GPU runtimes.
- Added a complete model-requirements selector: unsafe choices remain visible but are greyed out, disabled and explained.
- Added a second runtime guard that rechecks resources and safely falls back before allocating a model.
- Added a responsive bilingual splash screen with real startup stages and duplicate-launch protection.
- Added explicit status messages for first downloads, cached preparation, engine startup and safe retry.
- Bundled a platform-specific FFmpeg binary so online-video extraction works on a clean computer.
- Added a bilingual Windows installer preflight showing detected RAM, storage and bundled prerequisites.
- Added startup and model-change preloading so the selected engine is normally armed before Record is pressed.
- Added a persistent History view that indexes earlier exports and keeps every completed session reviewable.
- Added progressive recording saves plus a human-readable history log inside the user's Transcriptions folder.
- Added readable block/line layouts with optional start times and per-block durations.
- Made Simple mode apply the highest stable model, beam search and task-specific settings automatically.
- Added a full-window initialization state as a safety fallback when a model is not already armed.
- Enlarged the transcript editor and made the active Stop Recording button unmistakable.

## 2.1.0

- Reimagined Simple mode as a playful two-step home screen with four large, rounded task choices.
- Added approachable Best, Faster and Small PC quality profiles without hiding the full model catalogue in Advanced mode.
- Added a permanent tape-recorder-style microphone display with live waveform, level bar, analog VU needle and peak dB reading.
- Added explicit confirmation when the operating-system microphone is selected automatically, plus a level-only privacy notice.
- Added contextual hover explanations throughout Simple and Advanced modes.
- Kept every 2.0 workflow and professional setting available in the compact Advanced view.

## 2.0.0

- Rebuilt the interface around Simple and Advanced modes.
- Added guided File, Conference, Endless Dictation and Online Video workflows.
- Added operating-system language detection and complete French/English UI switching.
- Replaced the legacy OpenAI Whisper-only engine with adaptive faster-whisper/CTranslate2, MLX and PyTorch fallback backends.
- Added every official Whisper checkpoint, with `large-v3` as the maximum-accuracy default and `large-v3-turbo` as the fast large option.
- Added truthful hardware diagnostics and safe largest-model selection down to 4 GB CPU machines.
- Added learned time-to-completion estimates.
- Preserved recording, batch, drag-and-drop, YouTube, translation, cleanup, speaker labels, model management, subtitles, autosave and recovery.
- Added VTT export alongside TXT, SRT, JSON and CSV.
- Removed global TLS-verification bypass and constrained model deletion and online URLs.
- Added Windows, macOS and Linux package workflows with release checksums.

## 1.1

The original application is preserved at `archive-v1.1-before-v2.0`.
