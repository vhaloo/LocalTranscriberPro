"""Memory and update controls added in 3.5."""
TEXT = {
    "translation_model_resources": (
        "3B : standard. 7B : essai local, téléchargement de 8,33 Go ; seuils normaux : 28 Go de RAM totale et 14 Go disponibles. Le mode CPU — mémoire virtuelle permet une tentative sous ces seuils, avec lenteur ou échec possibles. Plus gros ne garantit pas une meilleure traduction.",
        "3B: standard. 7B: local experiment, 8.33 GB download; normal thresholds: 28 GB total RAM and 14 GB available. CPU — virtual memory can attempt it below these thresholds, with possible slowness or failure. Larger does not guarantee better translation."),
    "device_cpu_virtual": ("CPU — mémoire virtuelle", "CPU — virtual memory"),
    "cpu_virtual_ready": ("CPU avec pagination autorisée · modèle conservé", "CPU paging allowed · selected model retained"),
    "cpu_virtual_select": ("Forcer sur CPU", "Force on CPU"),
    "cpu_virtual_short": ("RAM insuffisante ? Choisissez « CPU — mémoire virtuelle » dans Processeur.",
                          "Not enough RAM? Select “CPU — virtual memory” under Processor."),
    "cpu_virtual_help": (
        "Tente le modèle CPU choisi même si la RAM physique est insuffisante, sans le remplacer. Le système peut utiliser son fichier d’échange (swap). Le chargement est isolé et annulable. Prévoyez du disque libre : la pagination peut être très lente ou échouer à la limite mémoire du système. Aucun réglage système n’est modifié. La mémoire virtuelle du système peut conserver des pages même en session privée.",
        "Attempts your selected CPU model despite insufficient physical RAM, without replacing it. The OS may use its pagefile/swap. Loading is isolated and cancellable. Keep disk space free: paging can be very slow or fail at the OS memory limit. No system setting is changed. OS virtual memory may retain pages even during a private session."),
    "load_cpu_virtual": ("Chargement CPU isolé : {model} · pagination autorisée, annulable",
                         "Isolated CPU loading: {model} · paging allowed, cancellable"),
    "update_auto_install": ("Installer automatiquement au repos", "Install automatically when idle"),
    "tip_update_automatic": (
        "Vérifie la dernière version officielle à chaque démarrage, sans fenêtre intrusive. Hors ligne ou déjà à jour : aucune erreur. Une nouvelle version apparaît dans le bouton de mise à jour de l’en-tête.",
        "Checks the latest official release at every launch, without a popup. Offline or up to date: no error. A new version appears in the header update button."),
    "tip_update_auto_install": (
        "Windows : télécharge et vérifie signature + SHA-256, puis installe et relance après 60 secondes d’inactivité, sans transcription, enregistrement, lecture vocale ni fenêtre ouverte. Une session privée contenant du texte attend votre action. « Plus tard » reporte à la prochaine ouverture. macOS/Linux : installation manuelle expérimentale. Désactivez cette option pour choisir le moment.",
        "Windows: downloads and verifies the signature + SHA-256, then installs and relaunches after 60 idle seconds, with no transcription, recording, speech playback or open dialog. A private session containing text waits for your action. “Later” defers until next launch. macOS/Linux: experimental manual installation. Turn this off to choose when to install."),
    "update_explanation": (
        "Le paquet officiel est vérifié par signature Ed25519 et SHA-256. Windows installe puis relance l’application dans son dossier actuel, en préservant modèles, réglages et historique. Vous pouvez reporter. macOS/Linux : la page officielle permet le remplacement manuel. Installer ferme la session privée en mémoire : exportez-la si nécessaire.",
        "The official package is verified with Ed25519 and SHA-256. Windows installs and relaunches in the current folder, preserving models, settings and history. You can defer. macOS/Linux: the official page provides manual replacement. Installing closes an in-memory private session: export it if needed."),
    "update_offline_quiet": ("Vérification indisponible pour le moment. L’application reste utilisable hors ligne.",
                             "Update check unavailable for now. The application remains usable offline."),
    "update_retry_quiet": ("La mise à jour reste disponible. Réessayez lorsque vous le souhaitez ; l’application reste ouverte.",
                           "The update remains available. Retry when convenient; the application stays open."),
    "update_ready_quiet": ("Version {version} vérifiée et prête. Installation au repos si activée, ou cliquez sur Installer. « Plus tard » reporte à la prochaine ouverture.",
                           "Version {version} is verified and ready. Installs when idle if enabled, or click Install. “Later” defers until next launch."),
    "update_installing_quiet": ("Vérification finale et préparation de l’installation…", "Final verification and installation preparation…"),
}


def register(strings):
    for key, (fr, en) in TEXT.items():
        strings["fr"][key], strings["en"][key] = fr, en
