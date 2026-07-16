# Privacy and security

## Local by design

Audio transcription, translation and speaker labeling run on the user's computer. The application has no account system, analytics SDK, advertising, cloud transcription path or hidden API fallback.

Network access occurs only for:

1. downloading a selected model the first time it is used;
2. downloading a YouTube video's audio after the user explicitly starts that task.

Downloaded models are cached locally and can be inspected or deleted in the Model Manager.

## Security controls

- The global TLS-verification bypass in version 1 was removed. The current certificate bundle is used and HTTPS verification stays enabled.
- Online-video URLs are limited to known YouTube HTTPS hosts before yt-dlp receives them.
- Model deletion resolves and validates the target against known model-cache roots before removing anything.
- Settings and recovery files use per-user operating-system data directories.
- Writes for transcripts and settings use temporary files followed by atomic replacement where practical.
- The Windows installer is per-user and requests no administrator rights.
- CI validates source on Windows, macOS and Linux before packaging.
- Release assets include SHA-256 checksums.

## Code signing

Automated public builds are reproducible but may be unsigned unless the maintainer configures platform secrets:

- Windows Authenticode certificate
- Apple Developer ID Application and Installer certificates, plus notarization credentials

Users should verify the SHA-256 checksum when installing an unsigned community build. Signing can be enabled without changing application code.

## Local files

Default transcripts are stored under the user's Documents/Transcriptions directory. Each completed session creates TXT, SRT, VTT, JSON and CSV outputs. Microphone sessions update their TXT and JSON progressively so useful work survives an interruption. A recovery file is kept only while a session is unsaved and is removed after successful autosave.

The History view uses a local SQLite index under the user's application-data directory and a readable `LocalTranscriberPro-history.jsonl` log beside the exports. These contain transcript metadata and previews only, remain on the computer and are never uploaded.
