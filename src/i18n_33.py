"""French and English strings for the 3.3 conversation workbench."""

TEXT = {
    "review_turns": ("Réviser les phrases", "Review turns"),
    "review_turns_help": ("Corrigez le texte logique original, sa traduction ou le locuteur. Les horaires sont conservés ; toute correction est historisée. Une nouvelle traduction ne traite que la phrase choisie.", "Edit logical original text, translation or speaker. Timing is retained and edits are recorded. Retranslation processes only the selected turn."),
    "review_speaker": ("Nom du locuteur (facultatif)", "Speaker name (optional)"),
    "review_language": ("Code de langue de l’original, par exemple ar, fr, ht", "Original language code, for example ar, fr, ht"),
    "review_source": ("Original — texte modifiable", "Original — editable text"),
    "review_translation": ("Traduction — ou relancez-la après correction de l’original", "Translation — or regenerate it after editing the original"),
    "review_retranslate": ("Retraduire cette phrase", "Retranslate this turn"),
    "review_audio": ("Réécouter cette phrase", "Replay this turn"),
    "review_history": ("{count} correction(s) conservée(s)", "{count} recorded edit(s)"),
    "review_show_history": ("Voir les corrections", "View revisions"),
    "review_numbers": ("Nombres différents : à vérifier", "Different numbers: review"),
    "review_stale": ("Une correction plus récente est conservée. Relancez la traduction de cette version.", "A newer edit was retained. Retranslate that version if needed."),
    "audience": ("Écran interlocuteur", "Audience display"),
    "audience_help": ("Fenêtre indépendante : déplacez-la sur l’écran de votre interlocuteur. Choisissez sa langue ou les deux, puis réglez la taille avec A− / A+.", "Independent window: move it to your conversation partner’s screen. Choose their language or both, and adjust size with A− / A+."),
    "audience_both": ("Toutes les langues", "All languages"),
    "typed_reply": ("Écrire et parler", "Type and speak"),
    "typed_reply_help": ("Écrivez dans votre langue de destination. L’application traduit vers l’autre langue de la paire, l’ajoute au compte rendu et la lit à voix haute. Confirmez d’abord cette autre langue.", "Type in your destination language. The app translates to the other language in the pair, adds the reply to the transcript and reads it aloud. Confirm the other language first."),
    "reply_translate_speak": ("Traduire et lire", "Translate and read"),
    "reply_choose_language": ("Choisissez l’autre langue de la conversation avant de traduire la réponse.", "Choose the other conversation language before translating the reply."),
    "offline_prepare": ("Préparer hors ligne", "Prepare offline"),
    "offline_prepare_help": ("Prépare la reconnaissance, la traduction et les voix des langues sélectionnées. « Vérifier » utilise uniquement les fichiers locaux et essaie les moteurs. Une voix absente du catalogue est signalée ; la reconnaissance ne garantit pas une voix pour chaque langue.", "Prepare recognition, translation and voices for selected languages. Verify uses local files only and exercises the engines. Voices unavailable in the catalogue are listed; recognition coverage does not imply voice coverage."),
    "offline_verify": ("Vérifier sans téléchargement", "Verify without downloading"),
    "offline_download": ("Télécharger et préparer les langues choisies", "Download and prepare selected languages"),
    "offline_complete": ("Vérification du profil terminée — consultez le résultat.", "Profile check finished — inspect the result."),
    "privacy_controls": ("Confidentialité", "Privacy"),
    "privacy_controls_help": ("Mode confidentiel : aucune nouvelle sauvegarde automatique du texte, de l’audio ou de l’historique. Le texte reste en mémoire jusqu’à la fermeture et peut être enregistré en .ltps chiffré avec votre mot de passe. L’audio n’est pas inclus. Les anciens fichiers restent présents. Ce choix ne persiste pas au redémarrage. Les exports manuels restent possibles.", "Confidential mode: no new automatic transcript, audio or history files. Text stays in memory until closing and can be saved as a password-encrypted .ltps file. Audio is not included. Existing files remain. This mode resets on restart. Manual exports remain available."),
    "private_toggle": ("Session confidentielle sans sauvegarde automatique", "Confidential session without automatic saving"),
    "private_active": ("CONFIDENTIEL · pas de sauvegarde automatique · pensez au fichier chiffré", "CONFIDENTIAL · automatic saving off · save an encrypted file if needed"),
    "private_inactive": ("Sauvegardes locales habituelles activées", "Normal local saving enabled"),
    "private_save": ("Enregistrer un fichier chiffré…", "Save encrypted file…"),
    "private_open": ("Ouvrir un fichier chiffré…", "Open encrypted file…"),
    "private_password": ("Mot de passe (10 caractères minimum). Il ne pourra pas être récupéré.", "Password (at least 10 characters). It cannot be recovered."),
    "private_confirm": ("Confirmez le mot de passe", "Confirm password"),
    "private_mismatch": ("Les mots de passe ne correspondent pas.", "Passwords do not match."),
    "private_error": ("Impossible d’ouvrir ou de sauvegarder ce fichier. Vérifiez le mot de passe, le fichier et les droits d’écriture.", "Cannot open or save this file. Check the password, file and write permissions."),
    "private_saved": ("Session chiffrée enregistrée", "Encrypted session saved"),
    "provisional": ("Provisoire [{language}] · {text}", "Provisional [{language}] · {text}"),
    "pipeline_lag": ("Audio restant : {seconds} s", "Remaining audio: {seconds} s"),
    "pair_different": ("Les deux langues de conversation doivent être différentes.", "Choose two different conversation languages."),
    "pair_next_turn": ("Langues mises à jour : prise en compte au prochain fragment. Les phrases précédentes sont conservées.", "Languages updated: applied at the next turn. Previous turns are retained."),
    "tools_idle": ("Terminez l’opération en cours avant de préparer les modèles ou de changer la confidentialité.", "Finish the current operation before preparing models or changing privacy."),
    "workbench_failed": ("Outil de conversation : {error}", "Conversation tool: {error}"),
    "language_candidates": ("Langues possibles — confirmer :", "Possible languages — confirm:"),
    "context_translation": ("Traduction contextuelle (locale)", "Contextual translation (local)"),
    "glossary_help": ("Glossaire facultatif : une ligne « terme source | code destination | traduction imposée ». Exemple : Maple Street | fr | rue Maple. Les termes ne sont imposés que si les marqueurs survivent à la traduction ; sinon la traduction habituelle est utilisée.", "Optional glossary: one line ‘source term | destination code | required translation’. Example: Maple Street | fr | rue Maple. Terms are applied only when markers survive translation; otherwise ordinary translation is used."),
    "glossary_label": ("Glossaire facultatif : terme source | langue destination | traduction", "Optional glossary: source term | destination language | translation"),
    "translation_model_resources": ("3B : standard. 7B : essai local, téléchargement de 8,33 Go ; 28 Go de RAM totale et 14 Go disponibles. Un modèle plus gros ne garantit pas une meilleure traduction.", "3B: standard. 7B: local experiment, 8.33 GB download; 28 GB total RAM and 14 GB available. A larger model does not guarantee better translation."),
    "default_cache": ("Cache standard de l’application", "Standard application cache"),
    "translation_cache_choose": ("Choisir le dossier du modèle 7B…", "Choose 7B model folder…"),
    "storage_translation_7b": ("Traduction 7B — dossier personnalisé", "7B translation — custom folder"),
}


def register(strings):
    for key, (fr, en) in TEXT.items():
        strings["fr"][key] = fr
        strings["en"][key] = en
    strings["fr"]["translation_help_body"] += "\n\n3.3 : Réviser les phrases permet de corriger et de retraduire une intervention. Écran interlocuteur ouvre une fenêtre indépendante. Les langues peuvent être corrigées pendant la capture : le changement s’applique au fragment suivant. Préparer hors ligne et Confidentialité expliquent les modèles locaux, les voix et la sauvegarde chiffrée. Le texte jaune est provisoire et n’est jamais exporté."
    strings["en"]["translation_help_body"] += "\n\n3.3: Review turns edits and retranslates one intervention. Audience display opens a separate window. Language changes during capture apply at the next turn. Prepare offline and Privacy explain local models, voices and encrypted saving. Yellow text is provisional and never exported."
