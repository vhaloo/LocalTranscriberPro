# Quiet application updates — 3.5.0

At every enabled startup the app checks only the official GitHub latest-stable release endpoint in a background thread. Offline, timeout, unavailable metadata and already-current results never open an error or modal dialog. The app remains usable. Manual checks report a short status; startup checks stay quiet. Audio, transcripts, vocabulary and hardware details are not sent to GitHub.

The header update button displays a newer version, download progress and readiness. Clicking it opens details with **Install** and **Later**. Checking at startup and automatic idle installation are separate settings under **Settings → Recognition**, both enabled by default. Explicitly disabled existing check preferences remain disabled. Source-development sessions do not auto-install over a maintained desktop installation.

## Windows

The packaged Windows app can download in the background, verify the publisher's Ed25519 manifest, exact asset name/version/size and SHA-256, and install automatically after 60 seconds without keyboard/mouse interaction in the application. Recording, recognition/preloading, speech, tool workers, visible dialogs and private text defer unattended installation. Hidden settings do not block it. **Later** defers installation for this launch; the next startup can retry. Disable automatic installation to choose when to install manually.

An unchanged cached installer is reused only after rechecking its actual bytes against freshly verified release metadata. HTTPS redirects are restricted to GitHub asset hosts. Before closing, the app hashes the prepared file again and checks 12 GB of free installation space plus temporary headroom. Failed downloads, signatures, storage checks or process handoff leave the app open with a retry indicator. No unverified package is launched. The final idle check runs again after background preparation, so activity during verification defers installation.

The app commits editor changes, saves recovery/settings, starts the per-user installer and exits. `/WAITPID` waits on the retiring app process before Inno checks its mutex or replaces files; `/AUTOUPDATE` relaunches the new version. The current custom installation folder and full/CPU runtime flavor are preserved. No Windows restart, elevation or system/pagefile-setting change is requested. Settings/history/models/recordings live outside the replaced `_internal` runtime.

An explicit manual installation may close an in-memory private session; export it first if needed. Automatic installation defers while any private text is present, including uncommitted editor text.

## macOS / Linux

Startup checks and the version indicator are quiet; **Install** opens the official release page for manual replacement. These distributions remain experimental. There is no automatic package replacement or elevation on these platforms. [Platform guide](EXPERIMENTAL_DESKTOP_3.5.md).

## Français

À chaque ouverture activée, vérification discrète de la dernière release stable officielle : aucune erreur ni fenêtre intrusive sans Internet ou si le logiciel est à jour. Le bouton de l'en-tête indique une nouvelle version, sa progression et sa disponibilité. Les options **Vérifier au démarrage** et **Installer automatiquement au repos** sont séparées dans Paramètres → Reconnaissance ; les choix de désactivation existants sont respectés.

Windows télécharge, vérifie signature Ed25519 et SHA-256, attend au moins 60 secondes d'inactivité et la fin des tâches, sauvegarde, installe dans le dossier actuel et relance. Les fenêtres visibles et sessions privées contenant du texte reportent l'installation automatique. « Plus tard » reporte à la prochaine ouverture. Un téléchargement/contrôle indisponible laisse l'application ouverte. Mac/Linux : remplacement manuel expérimental depuis la page officielle.

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
