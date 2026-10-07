# Application updates / Mises à jour

At startup, an enabled background check queries only the official repository's latest stable GitHub release. No audio or transcript is sent. Offline startup and API failures remain usable and quiet; the manual ↻ check explains failures. Drafts, pre-releases, older versions and releases without both the Windows installer and checksum manifest are ignored.

The proposal shows the version and requires the user's acceptance. Download is cancellable. HTTPS redirects are restricted to GitHub asset hosts; the asset URLs must belong to this exact repository and release. Both the announced byte count and SHA-256 must match before the temporary download becomes executable.

Before installation the app must be idle. It saves editor corrections, recovery and settings, starts the per-user Inno installer, then exits and releases the application mutex. `/AUTOUPDATE` instructs the installer to relaunch the installed version after copying. No Windows restart, administrator elevation or user-data deletion is requested.

The bundled `_internal` runtime is replaced completely to prevent obsolete native libraries or dependency metadata from shadowing the new versions. Settings, history, downloaded models and recordings are outside that runtime directory and are preserved.

Windows supports installation and relaunch. On macOS/Linux the accepted proposal opens the official release page for a platform-appropriate installation. Those platforms do not yet have automated replacement.

## Français

La vérification en arrière-plan est activée par défaut et se désactive dans Avancé. Le bouton ↻ lance une vérification manuelle. Une nouvelle version stable officielle est proposée ; aucune installation ne commence sans accepter. L'audio, le texte, le vocabulaire et les informations matérielles ne sont pas envoyés.

Accepter télécharge et vérifie le paquet, sauvegarde la session, ferme l'application, installe pour le compte Windows actuel et relance la nouvelle version. Un fichier incomplet, modifié ou sans SHA-256 bloque l'installation. Annuler conserve l'application actuelle. Les enregistrements et transcriptions actifs doivent être terminés avant installation.

## Release requirements

- Stable numeric tag `vX.Y.Z` (or `X.Y.Z`), greater than the running version.
- Asset `LocalTranscriberPro-X.Y.Z-Windows-x64-Setup.exe`.
- Asset `SHA256SUMS.txt`, containing that exact filename and its SHA-256.
- Both assets must be hosted under `https://github.com/vhaloo/LocalTranscriberPro/releases/download/<tag>/`.
- Keep the installer AppId, application mutex and per-user data locations unchanged.

Checksums over trusted HTTPS provide integrity verification, not an independent digital signature. Published Windows installers currently have no commercial Authenticode signature.
