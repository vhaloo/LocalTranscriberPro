# macOS / Linux 3.1.0 — Experimental packages / Paquets expérimentaux

These packages are published for early testing. **Windows 3.1.0 retains its validated stable installer.** Native CPU transcription and bundled French/English voices pass automated checks on macOS 14 arm64 and Ubuntu 24.04 x86-64. Physical installation, microphones, GPU acceleration and other operating-system versions remain unverified. English instructions follow the French guide below.

## Télécharger et vérifier

| Plateforme | Fichier expérimental |
|---|---|
| Mac Apple Silicon, arm64 | [DMG 3.1.0](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v3.1.0/LocalTranscriberPro-3.1.0-macOS-arm64-experimental.dmg) |
| Linux x86-64 | [AppImage 3.1.0](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v3.1.0/LocalTranscriberPro-3.1.0-Linux-x86_64-experimental.AppImage) · [Archive portable](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v3.1.0/LocalTranscriberPro-3.1.0-Linux-x86_64-experimental.tar.gz) |

Le [manifeste SHA-256](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v3.1.0/SHA256SUMS.txt) contient les empreintes de ces fichiers et du paquet Windows. Comparez l'empreinte du téléchargement avant installation :

```sh
# macOS
shasum -a 256 LocalTranscriberPro-3.1.0-macOS-arm64-experimental.dmg

# Linux, depuis le dossier des téléchargements et du manifeste
sha256sum --ignore-missing --check SHA256SUMS.txt
```

Les versions précédentes restent disponibles dans [Releases](https://github.com/vhaloo/LocalTranscriberPro/releases). Sauvegardez vos données et conservez votre ancienne application avant cet essai. Les paquets 3.1 utilisent les mêmes emplacements de préférences, d'historique et de modèles ; une sauvegarde reste utile pour revenir à une ancienne version.

## Mac Apple Silicon

Le paquet cible les puces Apple M1 et suivantes, **pas les Mac Intel**. macOS 14 est la version de référence des essais automatisés ; les versions plus anciennes n'ont pas été essayées.

1. Ouvrez le DMG puis glissez **Local Transcriber Pro.app** dans **Applications**.
2. Ouvrez l'application depuis Applications. Le paquet possède une signature ad-hoc ; il n'a ni signature Developer ID ni notarisation Apple.
3. Si macOS bloque l'ouverture et que le fichier provient de cette release avec l'empreinte attendue, suivez la procédure Apple : après une première tentative, **Réglages Système → Confidentialité et sécurité → Ouvrir quand même**, si cette option est proposée. [Instructions officielles Apple](https://support.apple.com/en-us/102445).
4. Autorisez le microphone lorsque vous lancez un enregistrement. Sélectionnez ensuite une entrée audio et commencez par un court essai.

Les essais CI valident la reconnaissance sur CPU. MLX/MPS et les autres moteurs restent à essayer sur un vrai Mac ; le choix automatique peut utiliser un repli compatible.

## Linux x86-64

Ubuntu 24.04 avec une session graphique sert de référence. D'autres distributions peuvent nécessiter des bibliothèques système différentes. Le paquet contient un runtime PyTorch CPU ; l'accélération NVIDIA n'est pas validée ni promise sans préparation supplémentaire.

Rendez l'AppImage exécutable puis ouvrez-la :

```sh
chmod u+x LocalTranscriberPro-3.1.0-Linux-x86_64-experimental.AppImage
./LocalTranscriberPro-3.1.0-Linux-x86_64-experimental.AppImage
```

Si FUSE manque, vous pouvez utiliser la fonction d'extraction/lancement de l'AppImage :

```sh
./LocalTranscriberPro-3.1.0-Linux-x86_64-experimental.AppImage --appimage-extract-and-run
```

Cette méthode demande davantage d'espace temporaire. [Documentation officielle AppImage sur FUSE et l'extraction](https://docs.appimage.org/user-guide/troubleshooting/fuse.html).

L'archive portable constitue une autre option et conserve les permissions Unix :

```sh
mkdir -p "$HOME/Applications/LocalTranscriberPro-3.1.0-experimental"
tar -xzf LocalTranscriberPro-3.1.0-Linux-x86_64-experimental.tar.gz \
  -C "$HOME/Applications/LocalTranscriberPro-3.1.0-experimental"
"$HOME/Applications/LocalTranscriberPro-3.1.0-experimental/LocalTranscriberPro/LocalTranscriberPro"
```

La CI installe `libportaudio2` pour le runtime audio. Si une erreur PortAudio apparaît sur Ubuntu, installez ce paquet avec votre gestionnaire système, puis relancez. Le fonctionnement de tous les microphones, serveurs audio, environnements Wayland/X11 et réglages d'affichage n'est pas validé.

## Premier essai et mises à jour

Préparez d'abord un petit modèle et transcrivez un court fichier, puis essayez le microphone. Les voix française et anglaise sont incluses. Les autres modèles et voix se téléchargent selon les fonctions choisies ; ils fonctionnent ensuite localement. Le mode universel étendu nécessite davantage de mémoire et peut être lent sur CPU. [Modèles et ressources](../README.md#local-models-and-hardware).

Les mises à jour macOS/Linux ouvrent la page de release ; le remplacement de l'application reste manuel. La présence de fichiers expérimentaux sur cette release ne transforme pas le canal Windows en préversion.

Signalez les problèmes dans les [issues GitHub](https://github.com/vhaloo/LocalTranscriberPro/issues) en précisant système, architecture, mémoire, modèle, CPU/GPU et message d'erreur. Évitez de joindre une conversation privée. [Résultats et limites des essais](VALIDATION_3.1.md).

## English quick start

- **Mac:** download the arm64 experimental DMG, open it and drag the app into Applications. Apple Silicon only; macOS 14 is the automated-test reference. The app is ad-hoc signed and not Apple-notarized. If blocked, follow [Apple's per-app opening instructions](https://support.apple.com/en-us/102445) after verifying the download. Grant microphone permission when recording.
- **Linux:** download the x86-64 experimental AppImage, use `chmod u+x` and run it. Ubuntu 24.04 is the build/test reference. If FUSE is unavailable, pass `--appimage-extract-and-run` or use the portable tar archive. A graphical desktop and working system audio are needed; `libportaudio2` is installed in CI.
- Back up existing data and keep your previous app for rollback. Prepare models once before offline use; French/English voices are bundled. Updates on these platforms open the release page and require manual replacement.
- These are **experimental platform packages**. Native CPU ASR and voice smoke checks do not establish physical installation, microphone, GUI or GPU reliability. Windows remains stable. Verify file integrity with `SHA256SUMS.txt` from the same release.
