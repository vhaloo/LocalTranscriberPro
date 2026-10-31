"""Task-first workspace vocabulary, French and English."""

TEXT = {
    "settings": ("Paramètres", "Settings"),
    "storage_budget": (
        "Minimum : environ {minimum_files} de fichiers, avec {minimum_free} libres conseillés avant installation.\nConversation par défaut : environ {universal_files} avec Whisper large-v3 et la traduction ; couverture maximale : {coverage_files} avec Omnilingual.\nTous les modèles et voix : environ {catalogue_files} de fichiers ; budget prudent {catalogue_free_budget} avec préparation/caches.\nAudio sauvegardé : environ {recording_hour} par heure de capture mono.",
        "Minimum: about {minimum_files} of files; {minimum_free} free recommended before installation.\nDefault conversation: about {universal_files} with Whisper large-v3 and translation; maximum coverage: {coverage_files} with Omnilingual.\nAll models and voices: about {catalogue_files} of files; allow {catalogue_free_budget} for preparation/caches.\nSaved audio: about {recording_hour} per hour of mono capture.",
    ),
    "language_auto": ("Auto", "Auto"),
    "language_fr": ("FR", "FR"),
    "language_en": ("EN", "EN"),
    "workspace_subtitle": (
        "Audio, texte et dialogue · sur cet ordinateur",
        "Audio, text and conversation · on this computer",
    ),
    "app_subtitle": (
        "Transcription, traduction et voix locales",
        "Local transcription, translation and speech",
    ),
    "workspace_quick_guide": (
        "Choisissez un usage à gauche (Ctrl+1 à Ctrl+5), puis une source et les langues utiles. Le texte conserve l’essentiel de l’écran. Les outils de révision, l’écran interlocuteur et les réponses écrites sont à gauche. Paramètres (Ctrl+,) regroupe reconnaissance, voix, indices et stockage. F11 agrandit la lecture ; Échap revient.",
        "Choose a task on the left (Ctrl+1 to Ctrl+5), then a source and relevant languages. Text gets most of the screen. Review, audience display and typed replies are on the left. Settings (Ctrl+,) groups recognition, voices, indicators and storage. F11 expands reading; Escape returns.",
    ),
    "workspace_search_help": (
        "Ctrl+F ouvre une recherche littérale, sans modifier ni lire le texte. Entrée passe au résultat suivant, Maj+Entrée au précédent, Échap ferme la recherche. Les mille premières occurrences sont repérées. Pour l’arabe affiché avec des formes contextuelles, la recherche utilise aussi le texte logique et peut surligner la ligne complète.",
        "Ctrl+F opens literal search without editing or speaking the text. Enter goes forward, Shift+Enter backward, and Escape closes search. The first thousand occurrences are indexed. For shaped Arabic display, search also checks logical text and may highlight the complete line.",
    ),
    "auto_will_use": (
        "Priorité OpenAI : {model}, selon la mémoire et les capacités disponibles.",
        "OpenAI priority: {model}, subject to available memory and runtime capabilities.",
    ),
    "workspace_step_source": ("1  CHOISIR UN USAGE", "1  CHOOSE A TASK"),
    "workspace_step_model": ("2  RECONNAISSANCE", "2  RECOGNITION"),
    "workspace_step_tools": ("3  RELIRE ET PARTAGER", "3  REVIEW AND SHARE"),
    "workspace_task_files": ("Fichiers audio et vidéo", "Audio and video files"),
    "workspace_task_universal": ("Traduction live", "Live translation"),
    "workspace_task_conference": ("Conférence", "Conference"),
    "workspace_task_dictation": ("Dictée continue", "Continuous dictation"),
    "workspace_task_link": ("Vidéo en ligne", "Online video"),
    "workspace_updates": ("↻", "↻"),
    "workspace_settings_help": (
        "Réglages de transcription, de voix et de stockage. Ctrl+, pour les retrouver.",
        "Recognition, voice and storage settings. Open again with Ctrl+,.",
    ),
    "workspace_recognition": ("Reconnaissance", "Recognition"),
    "workspace_voices": ("Voix et indices", "Voices and indicators"),
    "workspace_storage": ("Fichiers et stockage", "Files and storage"),
    "workspace_choose_model": ("Choisir un modèle…", "Choose a model…"),
    "workspace_openai_policy": (
        "Précision : priorité aux modèles locaux OpenAI Whisper, large-v3 dès que la mémoire le permet. Rapide : privilégie la vitesse. Le catalogue conserve tous les autres modèles et le profil de couverture maximale.",
        "Accuracy prioritizes local OpenAI Whisper models, with large-v3 when memory allows. Faster prioritizes speed. All other models and the maximum coverage profile remain in the catalogue.",
    ),
    "workspace_language_help": (
        "Détection automatique, français ou anglais. Toutes les langues restent accessibles dans les paramètres de reconnaissance.",
        "Automatic detection, French or English. All languages remain available in recognition settings.",
    ),
    "workspace_local": (
        "Traitement local · voix et modèles préparés utilisables hors ligne",
        "Local processing · prepared voices and models work offline",
    ),
    "workspace_empty_title": ("Votre texte, au premier plan", "Your text, front and center"),
    "workspace_enter_url": ("Saisir une adresse vidéo", "Enter a video address"),
    "workspace_find": ("Rechercher", "Find"),
    "workspace_search_hint": (
        "Rechercher dans le texte · Entrée : suivant · Échap : fermer",
        "Find in transcript · Enter: next · Escape: close",
    ),
    "workspace_profile_summary": ("{model}\nTraitement : {device}", "{model}\nProcessing: {device}"),
}


def register(strings):
    for key, (fr, en) in TEXT.items():
        strings["fr"][key], strings["en"][key] = fr, en
    strings["fr"]["translation_help_body"] = strings["fr"]["translation_help_body"].replace(
        "Le profil automatique universel privilégie la couverture vocale, puis la précision : Whisper large-v3 sur un ordinateur compatible.",
        "Le profil Précision OpenAI privilégie Whisper large-v3 lorsque la mémoire le permet. Le profil Multilinguisme maximal du catalogue reste disponible, notamment pour les langues supplémentaires reconnues par Omnilingual.",
    )
    strings["en"]["translation_help_body"] = strings["en"]["translation_help_body"].replace(
        "The universal automatic profile favors language coverage, then accuracy: Whisper large-v3 on compatible hardware.",
        "The OpenAI accuracy profile prioritizes Whisper large-v3 when memory permits. Maximum language coverage remains available in the catalogue, including additional languages recognized by Omnilingual.",
    )
