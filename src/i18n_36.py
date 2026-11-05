"""Single-model, on-demand preparation and automatic quality paging."""

TEXT = {
    "model_download": ("Télécharger", "Download"),
    "model_cancel_download": ("Annuler le téléchargement", "Cancel download"),
    "model_on_disk": ("Disponible hors ligne · suppression possible", "Available offline · removable"),
    "model_partial": ("Fichiers présents · préparation à compléter ou autre format", "Files present · preparation incomplete or another format"),
    "model_missing": ("Non téléchargé · sélection et téléchargement à la demande", "Not downloaded · select or download on demand"),
    "model_browse_download": ("Choisir ou télécharger un modèle…", "Choose or download a model…"),
    "model_download_help": (
        "Télécharger prépare les fichiers sans charger l’IA, même si son moteur manque ou si la RAM est faible. Supprimer retire uniquement les fichiers du modèle, après confirmation ; les composants partagés restent dans « Modèles téléchargés ». Fermer annule un téléchargement en cours ; un nouvel essai réutilise les fichiers déjà reçus.",
        "Download prepares files without loading the AI, even if its runtime is missing or RAM is low. Delete removes only that model's files, after confirmation; shared components stay in “Downloaded models”. Closing cancels an active download; retry reuses files already received."),
    "model_download_running": ("Téléchargement de {model} uniquement… Vous pouvez annuler.",
                               "Downloading {model} only… You can cancel."),
    "model_download_done": ("{model} téléchargé. Le chargement attend votre premier usage.",
                            "{model} downloaded. Loading waits until first use."),
    "model_download_failed": ("Téléchargement interrompu : {error}. Réessayez au besoin.",
                              "Download interrupted: {error}. Retry when convenient."),
    "model_remove_question": (
        "Supprimer les fichiers de {model} ci-dessous ?\n\n{details}\n\nLes tailles sont estimées ; les liens partagés peuvent réduire l’espace récupéré. Les composants communs, transcriptions et enregistrements sont conservés. Le modèle pourra être téléchargé de nouveau.",
        "Delete the following files for {model}?\n\n{details}\n\nSizes are estimated; shared links can reduce recovered space. Shared components, transcripts and recordings are kept. You can download the model again."),
    "model_remove_done": ("Fichiers du modèle supprimés. Téléchargement à nouveau disponible.",
                          "Model files deleted. Download is available again."),
    "model_remove_failed": ("Certains fichiers n’ont pas pu être supprimés. Vérifiez les modèles téléchargés.",
                            "Some files could not be deleted. Check Downloaded models."),
    "model_prepare": ("Préparer ce modèle", "Prepare this model"),
    "model_prepared": ("Modèle prêt", "Model ready"),
    "model_prepare_help": (
        "Détecte le meilleur modèle pour le profil choisi. Seul ce modèle est téléchargé au premier usage, ou avec ce bouton. Parcourir les modèles ne télécharge rien. Traduction, voix et outils ne sont préparés que si vous les utilisez. Une fois préparé, le modèle fonctionne hors ligne.",
        "Detects the best model for your selected profile. Only this model is downloaded on first use, or with this button. Browsing models downloads nothing. Translation, voices and tools are prepared only when used. Once prepared, the model works offline."),
    "model_waiting_download": (
        "Choisi : {model} (~{size:g} Go). Téléchargement au premier usage ou avec « Préparer ce modèle ».",
        "Selected: {model} (~{size:g} GB). Downloads on first use or with “Prepare this model”."),
    "model_waiting_cached": (
        "{model} disponible localement · chargement au premier usage ou avec « Préparer ce modèle ».",
        "{model} available locally · loads on first use or with “Prepare this model”."),
    "workspace_openai_policy": (
        "Précision : privilégie Whisper large-v3 complet. GPU compatible, sinon CPU int8 ; si la RAM manque, le mode CPU isolé autorise la mémoire virtuelle et peut être extrêmement lent. Le système peut encore refuser une allocation. Rapidité garde un choix adapté à la RAM physique. Seul le modèle retenu est préparé, au besoin.",
        "Accuracy prioritizes full Whisper large-v3. Compatible GPU, otherwise int8 CPU; when RAM is insufficient, isolated CPU mode allows virtual memory and may be extremely slow. The OS may still refuse an allocation. Speed keeps a physical-RAM-adapted choice. Only the selected model is prepared, when needed."),
    "model_requirements_help": (
        "Choisir ou parcourir ne télécharge rien. Le premier usage ou « Préparer ce modèle » prépare uniquement votre choix et ses composants nécessaires. Précision Auto privilégie OpenAI Whisper large-v3, même sur petit PC via CPU/mémoire virtuelle. Rapidité reste adaptée à la RAM physique. Les scores sont relatifs, pas des pourcentages de réussite.",
        "Selecting or browsing downloads nothing. First use or “Prepare this model” prepares only your choice and its required components. Accuracy Auto prioritizes OpenAI Whisper large-v3, including small PCs via CPU/virtual memory. Speed stays adapted to physical RAM. Scores are relative, not success percentages."),
    "cpu_virtual_ready": (
        "CPU · mémoire virtuelle si nécessaire · très lent possible · modèle conservé",
        "CPU · virtual memory if needed · may be very slow · selected model retained"),
}


def register(strings):
    for key, (fr, en) in TEXT.items():
        strings["fr"][key], strings["en"][key] = fr, en
