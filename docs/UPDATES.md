# Application updates / Mises à jour

At startup, an enabled background check queries only the official repository's latest stable GitHub release. No audio or transcript is sent. Offline startup and API failures remain usable and quiet; the manual ↻ check explains failures. Drafts, pre-releases, older versions and releases without the required Windows installer, checksum and signed-manifest assets are ignored.

The proposal shows the version and requires the user's acceptance. Download is cancellable. HTTPS redirects are restricted to GitHub asset hosts; the asset URLs must belong to this exact repository and release. Both the announced byte count and SHA-256 must match before the temporary download becomes executable.

Before installation the app must be idle. It saves editor corrections, recovery and settings, starts the per-user Inno installer, then exits and releases the application mutex. `/AUTOUPDATE` instructs the installer to relaunch the installed version after copying. No Windows restart, administrator elevation or user-data deletion is requested.

`/WAITPID` passes the actual retiring process ID. During `InitializeSetup`, the installer opens a synchronization-only process handle and waits for its exit before Inno checks the application mutex or replaces native libraries. A timeout stops the update before replacement. This avoids a startup race with the application's final save/close callbacks and uses Windows directly, with no shell helper.

The bundled `_internal` runtime is replaced completely to prevent obsolete native libraries or dependency metadata from shadowing the new versions. Settings, history, downloaded models and recordings are outside that runtime directory and are preserved.

Windows supports installation and relaunch. On macOS/Linux the accepted proposal opens the official release page for a platform-appropriate installation. Those platforms do not yet have automated replacement.

The stable 3.3.0 release also carries explicitly labelled **experimental** macOS Apple Silicon and Linux x86-64 assets. This per-platform status does not change the stable Windows updater channel. Mac/Linux users install these packages manually; see [the experimental installation guide](EXPERIMENTAL_DESKTOP_3.3.md).

## Français

La vérification en arrière-plan est activée par défaut et se désactive dans Avancé. Le bouton ↻ lance une vérification manuelle. Une nouvelle version stable officielle est proposée ; aucune installation ne commence sans accepter. L'audio, le texte, le vocabulaire et les informations matérielles ne sont pas envoyés.

Accepter télécharge et vérifie le paquet, sauvegarde la session, ferme l'application, installe pour le compte Windows actuel et relance la nouvelle version. Un fichier incomplet, modifié, sans SHA-256 ou sans signature valide bloque l'installation depuis la 3.3. Annuler conserve l'application actuelle. Les enregistrements et transcriptions actifs doivent être terminés avant installation.

## Release requirements

- Stable numeric tag `vX.Y.Z` (or `X.Y.Z`), greater than the running version.
- Asset `LocalTranscriberPro-X.Y.Z-Windows-x64-Setup.exe`.
- For CPU-only installations, asset `LocalTranscriberPro-X.Y.Z-Windows-x64-CPU-Setup.exe`; the packaged `runtime-flavor.json` preserves that choice on later updates.
- Asset `SHA256SUMS.txt`, containing that exact filename and its SHA-256.
- Assets `release-manifest.json` and `release-manifest.sig`, signed with the maintainer's Ed25519 key and binding the numeric version and each exact asset name, size and SHA-256.
- All assets must be hosted under `https://github.com/vhaloo/LocalTranscriberPro/releases/download/<tag>/`.
- Keep the installer AppId, application mutex and per-user data locations unchanged.

Version 3.3 pins the Ed25519 public key in `src/release_signature.py`. Invalid/missing signatures and mismatched versions or asset metadata fail closed. Private signing keys are neither committed nor bundled. The prior 3.2 client cannot retrospectively gain this verifier: its initial upgrade to 3.3 follows its existing HTTPS/SHA-256 procedure. Published Windows installers currently have no commercial Authenticode signature; Ed25519 manifests do not replace native operating-system certificates.

## Keeping GitHub current for every release

`scripts/check_release_docs.py` is required in validation and packaging. The README title/download, changelog, platform versions, current guide and screenshot manifest must match the code version. Screenshots are checked for valid image data and SHA-256. Native packages pass frozen ASR/voice checks, then exact verified assets are attached to a draft; stable publication follows actual Windows install validation and manifest signing. Explicitly authorized experimental assets carry their own status and validation limits. Existing verified release assets are preserved. See [BUILDING.md](BUILDING.md).

## Independent video-engine repair — 3.2.0

**Video options → Update the official video engine** is a separate explicit download. It queries only `yt-dlp/yt-dlp-nightly-builds`, accepts the exact platform asset and same-release `SHA2-256SUMS`, checks size and SHA-256 and writes a receipt in the video-engine cache. Each subsequent import verifies the executable again before launching it. Missing/changed/unverified files use the bundled engine. An update needs no app restart, preserves the current engine on download/hash failure and does not update any recognition/translation model. The button sends no audio, transcript, cookie or URL to GitHub.

The nightly channel follows the recommendation of [yt-dlp’s maintainers](https://github.com/yt-dlp/yt-dlp#installation) for timely site fixes. It does not bypass DRM, authentication or a site’s restrictions. The regular application startup updater continues to use stable Local Transcriber Pro releases.
