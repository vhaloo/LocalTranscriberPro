# Privacy and security

## Local by design

Audio transcription, translation and speaker labeling run on the user's computer. The application has no account system, analytics SDK, advertising, cloud transcription path or hidden API fallback.

Network access occurs only for:

1. downloading a selected model the first time it is used;
2. downloading a YouTube video's audio after the user explicitly starts that task;
3. checking the official GitHub stable release when startup update checks are enabled or the user clicks ↻;
4. downloading a release installer and checksum after the user accepts an update.

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

Automated public builds use the documented build workflow but may be unsigned unless the maintainer configures platform secrets:

- Windows Authenticode certificate
- Apple Developer ID Application and Installer certificates, plus notarization credentials

Users should verify the SHA-256 checksum when installing an unsigned community build. Signing can be enabled without changing application code.

## Local files

Default transcripts are stored under the user's Documents/Transcriptions directory. Each completed session creates TXT, SRT, VTT, JSON and CSV outputs. Microphone sessions update their TXT and JSON progressively so useful work survives an interruption. A local editor recovery file preserves the latest session, including corrections. Clearing the editor removes this recovery copy; completed exports remain intact. Microphone WAV audio is retained by default; Advanced mode can disable retention after a successful session. On failure, captured audio is kept for recovery.

The History view uses a local SQLite index under the user's application-data directory and a readable `LocalTranscriberPro-history.jsonl` log beside the exports. These contain transcript metadata and previews only, remain on the computer and are never uploaded.

## Model and update trust

New model snapshots are pinned to explicit revisions and load packaged Python code, never repository-provided Python. Files remain in the local cache. Update checks send the usual HTTPS request metadata to GitHub, including the source IP and app User-Agent; audio, transcripts, hardware details and vocabulary are not transmitted. No automatic update is installed without accepting the proposal. A missing checksum or damaged installer aborts installation. SHA-256 downloaded over HTTPS protects integrity but is not an independent publisher signature.

Requested YouTube downloads use the bundled yt-dlp EJS solver and Node runtime to process YouTube's JavaScript challenges with yt-dlp's permission restrictions. Automatic downloading of remote EJS components is disabled; updates to the solver ship with application updates.
