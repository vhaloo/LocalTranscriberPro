# Changelog

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
