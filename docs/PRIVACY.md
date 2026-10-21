# Privacy and security

## Local by design

Audio transcription, translation and speaker labeling run on the user's computer. The application has no account system, analytics SDK, advertising, cloud transcription path or hidden API fallback.

Network access occurs only for:

1. downloading a selected model the first time it is used;
2. retrieving explicitly requested media from a supported website or HTTP(S) media URL;
3. checking the official GitHub stable release when startup update checks are enabled or the user clicks ↻;
4. downloading a release installer, checksum and independently signed manifest after the user accepts an update;
5. downloading the official yt-dlp engine/checksum when its explicit update button is chosen;
6. preparing an optional selected local voice on first use, with the displayed download prompt.

Downloaded models are cached locally and can be inspected or deleted in the Model Manager.

## Security controls

- The global TLS-verification bypass in version 1 was removed. The current certificate bundle is used and HTTPS verification stays enabled.
- Online-media URLs must be HTTP(S), without inline username/password or control characters. Local file URLs are rejected; local files use the dedicated file chooser. Extraction runs in a separate cancellable worker with a size limit and free-space reserve.
- Model deletion resolves and validates the target against known model-cache roots before removing anything.
- Settings and recovery files use per-user operating-system data directories.
- Writes for transcripts and settings use temporary files followed by atomic replacement where practical.
- The Windows installer is per-user and requests no administrator rights.
- CI validates source on Windows, macOS and Linux before packaging.
- Release assets include SHA-256 checksums; the 3.3 updater additionally verifies an Ed25519 publisher signature.

## Code signing

Automated public builds use the documented build workflow but may be unsigned unless the maintainer configures platform secrets:

- Windows Authenticode certificate
- Apple Developer ID Application and Installer certificates, plus notarization credentials

The independent Ed25519 release-manifest signature protects the 3.3 updater and binds the version, exact filename, byte count and SHA-256. Its private key stays outside the source tree and packaged runtime. It does not provide Windows Authenticode, Apple Developer ID or notarization. The current installers have no commercial platform certificate; operating-system warnings can still appear. A first manual installation needs the usual trust in the official repository and downloaded package. The previous 3.2 updater uses its existing HTTPS/checksum checks for the initial 3.3 upgrade.

## Local files

Default transcripts are stored under the user's Documents/Transcriptions directory. Each completed session creates TXT, SRT, VTT, JSON and CSV outputs. Microphone sessions update their TXT and JSON progressively so useful work survives an interruption. A local editor recovery file preserves the latest session, including corrections. Clearing the editor removes this recovery copy; completed exports remain intact. Microphone WAV audio is retained by default; Advanced mode can disable retention after a successful session. On failure, captured audio is kept for recovery.

The History view uses a local SQLite index under the user's application-data directory and a readable `LocalTranscriberPro-history.jsonl` log beside the exports. These contain transcript metadata and previews only, remain on the computer and are never uploaded.

## Model and update trust

New model snapshots are pinned to explicit revisions and load packaged Python code, never repository-provided Python. Files remain in the local cache. Update checks send the usual HTTPS request metadata to GitHub, including the source IP and app User-Agent; audio, transcripts, hardware details and vocabulary are not transmitted. No automatic update is installed without accepting the proposal. Missing or invalid checksums, signatures, version/asset bindings or damaged installers abort a 3.3 update. SHA-256 alone protects integrity; the additional pinned Ed25519 public key supplies independent signature verification.

Requested YouTube downloads use the bundled yt-dlp EJS solver and Node runtime to process YouTube's JavaScript challenges with yt-dlp's permission restrictions. Automatic downloading of remote EJS components is disabled; the included solver ships with application updates. An optional verified official yt-dlp executable can be updated independently to follow site changes.

## Explicit online sign-in and temporary files — 3.2

A user may select a Netscape cookie export. Browser databases are never read automatically. The selected path is kept only for the current app session, is not saved in settings and is not included in diagnostics. A bounded temporary copy is passed to the isolated downloader and removed after import or cancellation; the original export is not modified. Cookie contents, requested URLs and raw extractor errors never enter the application log. Site access necessarily sends the requested URL and any selected applicable cookies to that site. Cookies are sensitive session credentials; the application shows that explanation before selection.

Each import owns a unique `ltp-video-*` folder under `Cache/online-audio` with an explicit ownership marker. Only that job is cleaned up after recognition, failure or cancellation. An abrupt OS/process crash can leave an unfinished job; the storage panel exposes its location. Cleanup does not scan or delete unrelated files. Technical diagnostics copy OS/tool versions and tool availability, without conversation contents or URLs.

**Storage and folders** shows actual application, export, cache, settings/history/recovery and log locations with read-only measurements. User data lives outside the runtime and survives app replacement. XDG-configured locations are respected on Linux.

## Confidential sessions — 3.3

Enable **Confidentiality → Keep this session in memory** before starting a sensitive conversation. While enabled, new microphone audio uses memory, and automatic transcript exports, editor recovery and history writes are disabled. Speaker analysis that needs a retained recording is disabled. This is a per-session switch, not a persistent default. Existing files, older recovery copies and previously saved conversations remain on disk; enabling it does not erase them. Imported source files also remain where the user placed them.

**Save an encrypted session** explicitly saves the transcript, language metadata and correction history in a `.ltps` file using AES-256-GCM and a password-derived scrypt key, with a fresh salt and nonce. Audio itself is not included. Audio-path references may be present inside the encrypted metadata. The application does not save or recover the password. Opening an encrypted file enables confidential mode for that session. Plaintext exports remain available when explicitly requested; the confidentiality dialog explains that distinction.

Memory-only capture cannot prevent operating-system paging, crash dumps, screen capture, clipboard use or deliberate manual exports. It is not secure erasure or a whole-computer encryption system. Correction history stores earlier text: review it before deliberately sharing an exported or encrypted session. The audience window and local voice playback can reveal displayed or spoken text to people nearby.
