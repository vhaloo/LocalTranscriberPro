# Local Transcriber Pro 2.2

Private, offline transcription for Windows, macOS and Linux — with a genuinely simple interface when you want it and every professional control when you need it.

> **[↓ PRÉSENTATION COMPLÈTE EN FRANÇAIS ↓](#francais)**

## Simple interface

![Local Transcriber Pro 2.2 simple mode showing automatic large-v3 selection, microphone VU meter, recording controls and transcript history](docs/images/local-transcriber-pro-2.2-simple-mode.png)

*Simple mode automatically selects the safest maximum quality, confirms the microphone visually and keeps the recording controls and transcript in one clear workspace.*

## Install — start here

You do **not** need to know how to program. You do **not** need to install Python, FFmpeg, CUDA or any other technical prerequisite. Choose the package for your computer, install it, then let Local Transcriber Pro configure itself.

### Step 1 — Download the correct file

1. Click the download link that matches your computer in the table below.
2. If your browser asks whether to save or keep the file, choose **Save** or **Keep**.
3. You can also open the [official Local Transcriber Pro Releases page](https://github.com/vhaloo/LocalTranscriberPro/releases/latest), expand **Assets** and select the same filename there.

| Your computer | File to download | Minimum |
|---|---|---|
| Windows 11 or Windows 10, 64-bit | **[Download for Windows](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v2.2.0/LocalTranscriberPro-2.2.0-Windows-x64-Setup.exe)**<br><code>LocalTranscriberPro-2.2.0-Windows-x64-Setup.exe</code> | 4 GB RAM for Tiny; NVIDIA GPU optional |
| Mac with macOS 12 or newer | **[Download for macOS](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v2.2.0/LocalTranscriberPro-2.2.0-macOS.dmg)**<br><code>LocalTranscriberPro-2.2.0-macOS.dmg</code> | Apple Silicon recommended; Intel uses the CPU |
| Linux, 64-bit | **[Download the Linux AppImage](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v2.2.0/LocalTranscriberPro-2.2.0-Linux-x86_64.AppImage)**<br><code>LocalTranscriberPro-2.2.0-Linux-x86_64.AppImage</code> | Modern distribution and 4 GB RAM for Tiny |
| Linux portable archive | **[Download the Linux archive](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v2.2.0/LocalTranscriberPro-2.2.0-Linux-x86_64.tar.gz)**<br><code>LocalTranscriberPro-2.2.0-Linux-x86_64.tar.gz</code> | Use only if AppImage is unsuitable |

Choose a file whose name begins with **LocalTranscriberPro**. The automatically generated **Source code** files are for developers and do not install the application.

### Step 2 — Install it

#### Windows

1. Open **Downloads** and double-click <code>LocalTranscriberPro-2.2.0-Windows-x64-Setup.exe</code>.
2. Windows may display a SmartScreen warning because this community application does not yet use a paid commercial signing certificate. Confirm that the file came from this repository. If Windows shows **Windows protected your PC**, click **More info**, then **Run anyway**.
3. The installer checks your RAM and free storage before copying anything. Read the summary, then continue with **Next** and **Install**.
4. No administrator password is normally required. The application is installed for your Windows account and can add a desktop shortcut.
5. Click **Finish** to launch Local Transcriber Pro.

#### macOS

1. Open **Downloads** and double-click <code>LocalTranscriberPro-2.2.0-macOS.dmg</code>.
2. Drag **Local Transcriber Pro** into the **Applications** folder shown in the window.
3. Open **Applications**, then double-click **Local Transcriber Pro**.
4. macOS may say that it cannot verify the developer. Control-click the application, choose **Open**, then choose **Open** again. You only need to approve this once.
5. Eject the Local Transcriber Pro disk image after the application opens.

#### Linux

1. Download <code>LocalTranscriberPro-2.2.0-Linux-x86_64.AppImage</code>.
2. Right-click the file, open **Properties**, then open **Permissions**.
3. Enable **Allow executing file as program**, or the equivalent option used by your distribution.
4. Double-click the AppImage.

If your file manager does not show that permission, open a terminal in the download folder and run:

    chmod +x LocalTranscriberPro-2.2.0-Linux-x86_64.AppImage
    ./LocalTranscriberPro-2.2.0-Linux-x86_64.AppImage

The <code>.tar.gz</code> package is a portable alternative: extract it, open the resulting <code>LocalTranscriberPro</code> folder and run the <code>LocalTranscriberPro</code> executable inside it.

### Step 3 — Complete the first launch

1. A startup screen appears immediately. **Do not double-click the application again.** It is detecting your CPU, memory and GPU, then preparing the best model that can run safely.
2. The interface follows the language of your operating system. Use **FR** or **EN** at the top to change it at any time.
3. The first use of a speech model requires an Internet connection while its files are downloaded. This can take several minutes. The status on screen explains every stage. The model is downloaded only once and is reused offline afterward.
4. If your system asks for microphone access, choose **Allow**. File transcription still works without it, but live recording cannot hear you.
5. Wait until the application says that the model and microphone are ready. Check that the level meter moves when you speak, then choose **Files**, **Conference**, **Dictate** or **Online video**.

Local Transcriber Pro automatically selects the largest model that fits safely. A powerful computer normally receives <code>large-v3</code>; a 4 GB computer falls back to Tiny. Quality and stability take priority over speed.

### Where your work is saved

- Completed and in-progress transcriptions are saved automatically under <code>Documents/Transcriptions</code>.
- **History** reopens earlier sessions.
- Model files are stored in the application cache and reused instead of being downloaded for every transcription.
- Your audio and transcription stay on this computer. Only a model download or an online-video download that you explicitly request uses the Internet.

### If the first launch seems slow

- Keep the application open while the startup screen is visible. Loading a large model can take from a few seconds to several minutes on a small CPU.
- Keep enough free storage for the model: approximately 0.08 GB for Tiny up to 3.1 GB for <code>large-v3</code>, plus temporary working space.
- If a model cannot run safely, the application disables it and selects a smaller one instead of risking a crash.
- Installation files are unsigned community builds. Every release includes <code>SHA256SUMS.txt</code> so advanced users can verify the downloads.

## What is new in 2.2

- **Crash-resistant automatic admission.** The app measures total and currently available RAM, free storage, CPU runtime, GPU runtime, total/free VRAM and architecture before admitting a model.
- **Unsafe models are visible but disabled.** Advanced mode shows the full catalogue, exact minimums and the reason an unavailable model is greyed out. A disabled model cannot be selected.
- **A second safety gate inside the engine.** Saved settings and changing system load are checked again immediately before model loading. If conditions changed, the engine safely chooses the best model that still fits.
- **Immediate startup feedback.** A responsive bilingual splash screen appears before heavy AI libraries load and explains memory, GPU and interface preparation step by step. Duplicate launches are blocked.
- **No missing FFmpeg surprise.** The platform-specific FFmpeg helper is bundled for online-video extraction, alongside the Python, AI, audio and diarization runtimes already included.
- **Long operations explain themselves.** First model download, cache preparation, engine startup and safe fallback each have a plain-language status.
- **Record is armed before it is needed.** The maximum safe model loads during the startup splash. Changing a model or processor immediately preloads the replacement in the background.
- **Permanent session history.** Every completed job is indexed in History, older exports are discovered automatically, and no Clear action deletes saved work.
- **Progressive recording safety.** Long microphone sessions continuously update TXT and JSON files under <code>Documents/Transcriptions</code> before Stop is pressed.
- **Flexible readable text.** Advanced mode can switch between paragraphs and one phrase per line, with optional start times and durations in seconds.
- **Quality-first Simple mode.** Choosing Files, Conference, Dictation or Online Video automatically applies the largest safe model and the strongest stable accuracy settings for that computer.

## The 2.1 interface

- **A truly playful Simple mode.** Four large rounded choices lead to one clearly explained next step: Files, Conference, Endless Dictation or Online Video.
- **A live vintage recorder display.** The microphone card stays visible, confirms the automatically selected device, draws the waveform, lights a level bar and moves an analog VU needle before recording begins.
- **No technical quality decision in Simple mode.** The app chooses maximum stable quality automatically; Advanced mode still exposes the full catalogue and tuning controls.
- **Explanations everywhere.** Hover over the main controls to learn what they do; privacy and automatic choices are also stated directly on screen.

## The 2.0 foundation

- **Simple and Advanced interfaces.** Start with four clear tasks: files, conference, endless dictation or an online video. One button reveals every advanced setting.
- **Maximum local quality by default.** The default profile selects the largest safe model for the computer and prioritizes OpenAI Whisper <code>large-v3</code>. <code>large-v3-turbo</code> is available when speed matters more.
- **Every official Whisper size remains available.** Tiny, Base, Small, Medium, Large v1/v2/v3, Turbo and English-only variants.
- **Hardware-aware acceleration.** NVIDIA CUDA and CPU use <code>faster-whisper</code>/CTranslate2; Apple Silicon uses MLX when available. A PyTorch compatibility engine provides a safe GPU fallback.
- **Honest hardware proof.** The hardware panel shows the detected CPU, RAM, GPU, VRAM and which runtime is actually available — not merely whether a GPU name exists.
- **Useful ETA.** Before a file starts, the app estimates processing time from its duration and hardware. After one completed transcription it learns the measured speed of that model and computer.
- **English and French UI.** The first launch follows the operating-system language; language can be changed at any time.
- **Modern sessions.** Conference mode enables speaker labels, dictation runs without a time limit, files can be dropped in batches, online video audio can be downloaded explicitly, and History can reopen earlier work.
- **Complete exports.** Automatic TXT, SRT, VTT, JSON and CSV copies, editable transcript, one-click clipboard copy, crash recovery and smart subtitles beside videos.

All transcription remains local. The only network operations are the first download of a selected model and an online-video download explicitly requested by the user.

## Models and practical requirements

The values below are conservative working targets. Quantization and platform backends can change actual use.

| Model | Typical download | Recommended memory | Use |
|---|---:|---:|---|
| <code>large-v3</code>, <code>large-v2</code>, <code>large-v1</code> | ~3.1 GB | CPU: 12 GB RAM / GPU: 7 GB VRAM and 8 GB host RAM | Best local multilingual accuracy; v3 is the default when safe |
| <code>large-v3-turbo</code> | ~1.6 GB | CPU: 8 GB RAM / GPU: 5 GB VRAM and 5.2 GB host RAM | Much faster, small accuracy trade-off; no reliable speech translation |
| <code>medium</code> / <code>medium.en</code> | ~1.5 GB | CPU: 8 GB RAM / GPU: 4 GB VRAM and 5.2 GB host RAM | Strong quality on mid-range computers |
| <code>small</code> / <code>small.en</code> | ~0.5 GB | CPU: 5 GB RAM / GPU: 2 GB VRAM and 4 GB host RAM | Balanced quality and speed |
| <code>base</code> / <code>base.en</code> | ~0.15 GB | CPU: 4.5 GB RAM / GPU: 1 GB VRAM and 4 GB host RAM | Lightweight general use |
| <code>tiny</code> / <code>tiny.en</code> | ~0.08 GB | CPU: 3.5 GB RAM / GPU: 0.8 GB VRAM and 4 GB host RAM | Safe 4 GB-computer fallback; slow CPUs are supported |

The gate also requires currently available working memory and enough free space for a first download. Those live values and every decision are visible under **This computer** and **Models and minimum requirements**.

<code>gpt-4o-transcribe</code> is newer and more accurate than Whisper, but OpenAI currently provides it as a hosted API rather than downloadable local weights. Local Transcriber Pro therefore uses the strongest openly downloadable OpenAI checkpoint (<code>large-v3</code>) instead of pretending an API model is offline.

See [Hardware and model selection](docs/HARDWARE.md) for exact behavior.

## Preserved and expanded feature set

- live microphone recording, pause and stop shortcuts
- unlimited dictation and conference capture
- audio/video batch queue and drag-and-drop folders
- YouTube audio download and transcription
- automatic spoken-language detection and speech-to-English translation
- speaker diarization/labels
- silence removal (VAD) and repetition cleanup
- synchronized subtitles beside source videos
- model cache manager
- output-folder selection and open-on-complete
- permanent session history with earlier-export discovery
- progressive TXT/JSON recording saves in <code>Documents/Transcriptions</code>
- block/line layouts with optional timestamps and durations
- TXT, SRT, VTT, JSON and CSV export
- session autosave and recovery
- automatic CPU/GPU selection with manual override

## Developer setup

    py -3.12 -m venv .venv
    ./.venv/Scripts/python -m pip install -r requirements-dev.txt
    ./.venv/Scripts/python main.py

Speaker labeling adds the optional compatibility pack:

    ./.venv/Scripts/python -m pip install -r requirements-diarization.txt

Run the validation suite:

    ./.venv/Scripts/python -m ruff check main.py src tests
    ./.venv/Scripts/python -m pytest

Build a Windows application folder:

    ./scripts/build_windows.ps1

Cross-platform packages are reproducibly built by <code>.github/workflows/desktop-build.yml</code>. Full instructions are in [Building and releasing](docs/BUILDING.md).

## Privacy and security

- No analytics, telemetry or cloud transcription is enabled by the app.
- TLS certificate verification is never disabled.
- Online downloads use an explicit YouTube host allowlist.
- Model deletion is restricted to known cache directories.
- The installer uses per-user installation and does not require administrator privileges.
- Release assets include SHA-256 checksums.

Read the complete [privacy and security note](docs/PRIVACY.md).

## Version 1 archive

The original 1.1 application remains permanently available at [<code>archive-v1.1-before-v2.0</code>](https://github.com/vhaloo/LocalTranscriberPro/releases/tag/archive-v1.1-before-v2.0) and the original [<code>v1.1</code>](https://github.com/vhaloo/LocalTranscriberPro/releases/tag/v1.1) release.

## License

MIT — developed by [Vhaloo](https://github.com/vhaloo).

---

<a id="francais"></a>

# LOCAL TRANSCRIBER PRO 2.2 — FRANÇAIS

Transcription privée et hors ligne pour Windows, macOS et Linux — avec une interface réellement simple quand vous le souhaitez et tous les réglages professionnels quand vous en avez besoin.

> **[↑ BACK TO THE ENGLISH VERSION / RETOUR À LA VERSION ANGLAISE ↑](#local-transcriber-pro-22)**

## Interface simple

![Mode simple de Local Transcriber Pro 2.2 montrant la sélection automatique de large-v3, le vumètre du microphone, les commandes d’enregistrement et l’historique des transcriptions](docs/images/local-transcriber-pro-2.2-simple-mode.png)

*Le mode simple choisit automatiquement la meilleure qualité sûre, confirme visuellement le microphone et réunit les commandes d’enregistrement et la transcription dans un seul espace clair.*

## Installation — commencez ici

Vous n’avez **pas** besoin de savoir programmer. Vous n’avez **pas** besoin d’installer Python, FFmpeg, CUDA ni aucun autre prérequis technique. Choisissez le paquet correspondant à votre ordinateur, installez-le, puis laissez Local Transcriber Pro se configurer automatiquement.

### Étape 1 — Téléchargez le bon fichier

1. Cliquez dans le tableau ci-dessous sur le lien de téléchargement correspondant à votre ordinateur.
2. Si votre navigateur demande s’il faut enregistrer ou conserver le fichier, choisissez **Enregistrer** ou **Conserver**.
3. Vous pouvez également ouvrir la [page officielle des releases de Local Transcriber Pro](https://github.com/vhaloo/LocalTranscriberPro/releases/latest), déplier **Assets** et y sélectionner le même nom de fichier.

| Votre ordinateur | Fichier à télécharger | Minimum |
|---|---|---|
| Windows 11 ou Windows 10, 64 bits | **[Télécharger pour Windows](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v2.2.0/LocalTranscriberPro-2.2.0-Windows-x64-Setup.exe)**<br><code>LocalTranscriberPro-2.2.0-Windows-x64-Setup.exe</code> | 4 Go de RAM pour Tiny; GPU NVIDIA facultatif |
| Mac avec macOS 12 ou plus récent | **[Télécharger pour macOS](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v2.2.0/LocalTranscriberPro-2.2.0-macOS.dmg)**<br><code>LocalTranscriberPro-2.2.0-macOS.dmg</code> | Apple Silicon recommandé; Intel utilise le CPU |
| Linux, 64 bits | **[Télécharger l’AppImage Linux](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v2.2.0/LocalTranscriberPro-2.2.0-Linux-x86_64.AppImage)**<br><code>LocalTranscriberPro-2.2.0-Linux-x86_64.AppImage</code> | Distribution moderne et 4 Go de RAM pour Tiny |
| Archive Linux portable | **[Télécharger l’archive Linux](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v2.2.0/LocalTranscriberPro-2.2.0-Linux-x86_64.tar.gz)**<br><code>LocalTranscriberPro-2.2.0-Linux-x86_64.tar.gz</code> | À utiliser seulement si AppImage ne convient pas |

Choisissez un fichier dont le nom commence par **LocalTranscriberPro**. Les fichiers **Source code** générés automatiquement sont destinés aux développeurs et n’installent pas l’application.

### Étape 2 — Installez l’application

#### Windows

1. Ouvrez **Téléchargements** et double-cliquez sur <code>LocalTranscriberPro-2.2.0-Windows-x64-Setup.exe</code>.
2. Windows peut afficher un avertissement SmartScreen parce que cette application communautaire n’utilise pas encore de certificat commercial payant. Vérifiez que le fichier vient bien de ce dépôt. Si Windows affiche **Windows a protégé votre ordinateur**, cliquez sur **Informations complémentaires**, puis sur **Exécuter quand même**.
3. L’installateur vérifie votre mémoire vive et votre espace libre avant de copier quoi que ce soit. Lisez le résumé, puis continuez avec **Suivant** et **Installer**.
4. Aucun mot de passe administrateur n’est normalement nécessaire. L’application est installée pour votre compte Windows et peut ajouter un raccourci au bureau.
5. Cliquez sur **Terminer** pour lancer Local Transcriber Pro.

#### macOS

1. Ouvrez **Téléchargements** et double-cliquez sur <code>LocalTranscriberPro-2.2.0-macOS.dmg</code>.
2. Faites glisser **Local Transcriber Pro** vers le dossier **Applications** affiché dans la fenêtre.
3. Ouvrez **Applications**, puis double-cliquez sur **Local Transcriber Pro**.
4. macOS peut indiquer qu’il ne peut pas vérifier le développeur. Faites un clic avec la touche Contrôle sur l’application, choisissez **Ouvrir**, puis choisissez encore **Ouvrir**. Cette autorisation n’est nécessaire qu’une seule fois.
5. Éjectez l’image disque Local Transcriber Pro après l’ouverture de l’application.

#### Linux

1. Téléchargez <code>LocalTranscriberPro-2.2.0-Linux-x86_64.AppImage</code>.
2. Faites un clic droit sur le fichier, ouvrez **Propriétés**, puis **Permissions**.
3. Activez **Autoriser l’exécution du fichier comme un programme**, ou l’option équivalente de votre distribution.
4. Double-cliquez sur l’AppImage.

Si votre gestionnaire de fichiers n’affiche pas cette autorisation, ouvrez un terminal dans le dossier de téléchargement et exécutez :

    chmod +x LocalTranscriberPro-2.2.0-Linux-x86_64.AppImage
    ./LocalTranscriberPro-2.2.0-Linux-x86_64.AppImage

Le paquet <code>.tar.gz</code> est une solution portable de remplacement : décompressez-le, ouvrez le dossier <code>LocalTranscriberPro</code> obtenu et lancez l’exécutable <code>LocalTranscriberPro</code> qu’il contient.

### Étape 3 — Terminez le premier lancement

1. Un écran de démarrage apparaît immédiatement. **Ne double-cliquez pas une deuxième fois sur l’application.** Elle détecte votre processeur, votre mémoire et votre GPU, puis prépare le meilleur modèle capable de fonctionner sans risque.
2. L’interface suit la langue de votre système d’exploitation. Utilisez **FR** ou **EN** en haut de la fenêtre pour changer de langue à tout moment.
3. La première utilisation d’un modèle vocal nécessite une connexion Internet pendant le téléchargement de ses fichiers. Cela peut prendre plusieurs minutes. L’état affiché à l’écran explique chaque étape. Le modèle n’est téléchargé qu’une seule fois et sera ensuite réutilisé hors ligne.
4. Si votre système demande l’autorisation d’utiliser le microphone, choisissez **Autoriser**. La transcription de fichiers fonctionne toujours sans cette permission, mais l’enregistrement en direct ne peut pas vous entendre.
5. Attendez que l’application indique que le modèle et le microphone sont prêts. Vérifiez que le vumètre bouge lorsque vous parlez, puis choisissez **Fichiers**, **Conférence**, **Dicter** ou **Vidéo en ligne**.

Local Transcriber Pro sélectionne automatiquement le plus gros modèle qui peut fonctionner sans risque. Un ordinateur puissant reçoit normalement <code>large-v3</code>; un ordinateur avec 4 Go de RAM se replie sur Tiny. La qualité et la stabilité sont prioritaires sur la vitesse.

### Où votre travail est enregistré

- Les transcriptions terminées et en cours sont enregistrées automatiquement dans <code>Documents/Transcriptions</code>.
- **Historique** permet de rouvrir les sessions précédentes.
- Les fichiers des modèles sont conservés dans le cache de l’application et réutilisés au lieu d’être téléchargés à chaque transcription.
- Votre audio et votre transcription restent sur cet ordinateur. Seuls le téléchargement d’un modèle ou celui d’une vidéo en ligne que vous demandez explicitement utilisent Internet.

### Si le premier lancement semble lent

- Gardez l’application ouverte tant que l’écran de démarrage est visible. Le chargement d’un gros modèle peut demander de quelques secondes à plusieurs minutes sur un petit processeur.
- Conservez assez d’espace libre pour le modèle : environ 0,08 Go pour Tiny jusqu’à 3,1 Go pour <code>large-v3</code>, en plus de l’espace de travail temporaire.
- Si un modèle ne peut pas fonctionner sans risque, l’application le désactive et en choisit un plus petit au lieu de risquer un plantage.
- Les fichiers d’installation sont des versions communautaires non signées. Chaque release comprend <code>SHA256SUMS.txt</code> afin que les utilisateurs avancés puissent vérifier les téléchargements.

## Nouveautés de la 2.2

- **Admission automatique résistante aux plantages.** L’application mesure la RAM totale et actuellement disponible, le stockage libre, le moteur CPU, le moteur GPU, la VRAM totale et libre ainsi que l’architecture avant d’autoriser un modèle.
- **Les modèles dangereux restent visibles, mais sont désactivés.** Le mode Avancé affiche le catalogue complet, les minimums exacts et la raison pour laquelle un modèle indisponible est grisé. Un modèle désactivé ne peut pas être sélectionné.
- **Une deuxième barrière de sécurité dans le moteur.** Les réglages enregistrés et la charge changeante du système sont vérifiés de nouveau juste avant le chargement du modèle. Si les conditions ont changé, le moteur choisit sans risque le meilleur modèle qui tient encore en mémoire.
- **Retour immédiat au démarrage.** Un écran de démarrage bilingue et réactif apparaît avant le chargement des lourdes bibliothèques d’IA et explique étape par étape la préparation de la mémoire, du GPU et de l’interface. Les doubles lancements sont bloqués.
- **Plus de mauvaise surprise liée à FFmpeg.** L’outil FFmpeg propre à la plateforme est inclus pour extraire les vidéos en ligne, avec les moteurs Python, IA, audio et d’identification des personnes déjà fournis.
- **Les opérations longues s’expliquent.** Le premier téléchargement du modèle, la préparation du cache, le démarrage du moteur et le repli sûr possèdent chacun un message en langage clair.
- **L’enregistrement est armé avant d’être nécessaire.** Le meilleur modèle sûr est chargé pendant l’écran de démarrage. Changer de modèle ou de processeur précharge immédiatement son remplaçant en arrière-plan.
- **Historique permanent des sessions.** Chaque tâche terminée est indexée dans Historique, les anciens exports sont découverts automatiquement et aucune action Effacer ne supprime le travail enregistré.
- **Sécurité progressive des enregistrements.** Les longues sessions au microphone actualisent continuellement leurs fichiers TXT et JSON dans <code>Documents/Transcriptions</code>, avant même d’appuyer sur Arrêter.
- **Texte lisible et flexible.** Le mode Avancé peut alterner entre des paragraphes et une phrase par ligne, avec des heures de départ et des durées en secondes facultatives.
- **Le mode Simple donne la priorité à la qualité.** Choisir Fichiers, Conférence, Dictée ou Vidéo en ligne applique automatiquement le plus gros modèle sûr et les réglages de précision stables les plus élevés pour cet ordinateur.

## L’interface de la 2.1

- **Un mode Simple réellement ludique.** Quatre grands choix arrondis conduisent à une seule prochaine étape clairement expliquée : Fichiers, Conférence, Dictée sans fin ou Vidéo en ligne.
- **Un affichage d’enregistreur rétro en direct.** La carte du microphone reste visible, confirme le périphérique sélectionné automatiquement, dessine la forme d’onde, allume une barre de niveau et déplace l’aiguille d’un vumètre analogique avant même le début de l’enregistrement.
- **Aucune décision technique de qualité en mode Simple.** L’application choisit automatiquement la qualité stable maximale; le mode Avancé expose toujours le catalogue complet et les réglages fins.
- **Des explications partout.** Survolez les commandes principales pour apprendre ce qu’elles font; la confidentialité et les choix automatiques sont également indiqués directement à l’écran.

## Les fondations de la 2.0

- **Interfaces Simple et Avancée.** Commencez avec quatre tâches claires : fichiers, conférence, dictée sans fin ou vidéo en ligne. Un bouton révèle tous les réglages avancés.
- **Qualité locale maximale par défaut.** Le profil par défaut sélectionne le plus gros modèle sûr pour l’ordinateur et donne la priorité à OpenAI Whisper <code>large-v3</code>. <code>large-v3-turbo</code> reste disponible lorsque la vitesse compte davantage.
- **Toutes les tailles officielles de Whisper restent disponibles.** Tiny, Base, Small, Medium, Large v1/v2/v3, Turbo et leurs variantes uniquement anglaises.
- **Accélération adaptée au matériel.** NVIDIA CUDA et le CPU utilisent <code>faster-whisper</code>/CTranslate2; Apple Silicon utilise MLX lorsqu’il est disponible. Un moteur de compatibilité PyTorch fournit un repli GPU sûr.
- **Preuve honnête du matériel.** Le panneau matériel affiche le CPU, la RAM, le GPU et la VRAM détectés ainsi que le moteur réellement disponible — pas seulement la présence d’un nom de GPU.
- **Estimation utile du temps.** Avant de commencer un fichier, l’application estime la durée du traitement à partir de sa durée et du matériel. Après une transcription terminée, elle apprend la vitesse mesurée de ce modèle sur cet ordinateur.
- **Interface anglaise et française.** Le premier lancement suit la langue du système d’exploitation; la langue peut être modifiée à tout moment.
- **Sessions modernes.** Le mode Conférence active les étiquettes de personnes, la dictée fonctionne sans limite de temps, les fichiers peuvent être déposés par lots, l’audio d’une vidéo en ligne peut être téléchargé explicitement et Historique peut rouvrir un ancien travail.
- **Exports complets.** Copies automatiques TXT, SRT, VTT, JSON et CSV, transcription modifiable, copie dans le presse-papiers en un clic, récupération après plantage et sous-titres intelligents à côté des vidéos.

Toutes les transcriptions restent locales. Les seules opérations réseau sont le premier téléchargement d’un modèle sélectionné et le téléchargement d’une vidéo en ligne explicitement demandé par l’utilisateur.

## Modèles et prérequis pratiques

Les valeurs ci-dessous sont des objectifs de fonctionnement prudents. La quantification et les moteurs propres à chaque plateforme peuvent modifier l’utilisation réelle.

| Modèle | Téléchargement typique | Mémoire recommandée | Utilisation |
|---|---:|---:|---|
| <code>large-v3</code>, <code>large-v2</code>, <code>large-v1</code> | ~3,1 Go | CPU : 12 Go de RAM / GPU : 7 Go de VRAM et 8 Go de RAM | Meilleure précision locale multilingue; v3 est utilisé par défaut lorsqu’il est sûr |
| <code>large-v3-turbo</code> | ~1,6 Go | CPU : 8 Go de RAM / GPU : 5 Go de VRAM et 5,2 Go de RAM | Beaucoup plus rapide, avec une petite perte de précision; pas de traduction vocale fiable |
| <code>medium</code> / <code>medium.en</code> | ~1,5 Go | CPU : 8 Go de RAM / GPU : 4 Go de VRAM et 5,2 Go de RAM | Grande qualité sur les ordinateurs intermédiaires |
| <code>small</code> / <code>small.en</code> | ~0,5 Go | CPU : 5 Go de RAM / GPU : 2 Go de VRAM et 4 Go de RAM | Bon équilibre entre qualité et vitesse |
| <code>base</code> / <code>base.en</code> | ~0,15 Go | CPU : 4,5 Go de RAM / GPU : 1 Go de VRAM et 4 Go de RAM | Usage général léger |
| <code>tiny</code> / <code>tiny.en</code> | ~0,08 Go | CPU : 3,5 Go de RAM / GPU : 0,8 Go de VRAM et 4 Go de RAM | Repli sûr pour les ordinateurs de 4 Go; les CPU lents sont pris en charge |

La barrière de sécurité exige également assez de mémoire de travail actuellement disponible et suffisamment d’espace libre pour un premier téléchargement. Ces valeurs en direct et chaque décision sont visibles sous **Cet ordinateur** et **Modèles et prérequis minimums**.

<code>gpt-4o-transcribe</code> est plus récent et plus précis que Whisper, mais OpenAI le fournit actuellement comme API hébergée plutôt que comme poids téléchargeables localement. Local Transcriber Pro utilise donc le meilleur point de contrôle OpenAI ouvertement téléchargeable (<code>large-v3</code>) au lieu de prétendre qu’un modèle d’API fonctionne hors ligne.

Consultez [Matériel et sélection du modèle](docs/HARDWARE.md) pour connaître le comportement exact.

## Fonctionnalités conservées et enrichies

- enregistrement du microphone en direct, pause et raccourcis d’arrêt
- dictée sans limite et enregistrement de conférences
- file de fichiers audio/vidéo et dépôt de dossiers par glisser-déposer
- téléchargement et transcription de l’audio YouTube
- détection automatique de la langue parlée et traduction de la parole vers l’anglais
- identification et étiquettes des personnes
- suppression des silences (VAD) et nettoyage des répétitions
- sous-titres synchronisés à côté des vidéos sources
- gestionnaire du cache des modèles
- sélection du dossier de sortie et ouverture à la fin
- historique permanent des sessions avec découverte des anciens exports
- sauvegardes progressives TXT/JSON dans <code>Documents/Transcriptions</code>
- présentations en blocs ou en lignes avec heures et durées facultatives
- exports TXT, SRT, VTT, JSON et CSV
- sauvegarde automatique et récupération des sessions
- sélection automatique CPU/GPU avec remplacement manuel

## Configuration pour les développeurs

    py -3.12 -m venv .venv
    ./.venv/Scripts/python -m pip install -r requirements-dev.txt
    ./.venv/Scripts/python main.py

L’identification des personnes ajoute le paquet de compatibilité facultatif :

    ./.venv/Scripts/python -m pip install -r requirements-diarization.txt

Lancez la suite de validation :

    ./.venv/Scripts/python -m ruff check main.py src tests
    ./.venv/Scripts/python -m pytest

Construisez un dossier d’application Windows :

    ./scripts/build_windows.ps1

Les paquets multiplateformes sont construits de manière reproductible par <code>.github/workflows/desktop-build.yml</code>. Les instructions complètes se trouvent dans [Construction et publication](docs/BUILDING.md).

## Confidentialité et sécurité

- Aucune analytique, télémétrie ni transcription dans le nuage n’est activée par l’application.
- La vérification des certificats TLS n’est jamais désactivée.
- Les téléchargements en ligne utilisent une liste d’hôtes YouTube explicitement autorisés.
- La suppression des modèles est limitée aux dossiers de cache connus.
- L’installateur fonctionne par utilisateur et ne nécessite pas de privilèges administrateur.
- Les fichiers des releases comprennent des sommes de contrôle SHA-256.

Lisez la [note complète sur la confidentialité et la sécurité](docs/PRIVACY.md).

## Archive de la version 1

L’application 1.1 originale reste disponible de façon permanente dans [<code>archive-v1.1-before-v2.0</code>](https://github.com/vhaloo/LocalTranscriberPro/releases/tag/archive-v1.1-before-v2.0) ainsi que dans la release originale [<code>v1.1</code>](https://github.com/vhaloo/LocalTranscriberPro/releases/tag/v1.1).

## Licence

MIT — développé par [Vhaloo](https://github.com/vhaloo).
