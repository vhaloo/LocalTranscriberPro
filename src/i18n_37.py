"""Guided setup and plain-language desktop preferences."""

MESSAGES = {
    "settings_save_unavailable": ("Preferences cannot currently be saved. Check free space and access to the settings folder; your current session remains available.", "Les préférences ne peuvent pas être sauvegardées actuellement. Vérifiez l’espace libre et l’accès au dossier des réglages ; la session reste utilisable."),
    "translation_save": ("Save translation settings", "Enregistrer les réglages de traduction"),
    "translation_save_help": ("Saves the model, context and glossary without downloading files or loading inference. Verify checks existing files; Prepare can download the required selected components.", "Enregistre le modèle, le contexte et le glossaire sans télécharger ni charger l’IA. Vérifier essaie les fichiers présents ; Préparer peut télécharger les composants sélectionnés nécessaires."),
    "translation_saved": ("Translation settings saved. No download or model load started.", "Réglages de traduction enregistrés. Aucun téléchargement ni chargement de modèle n’a été lancé."),
    "context_translation_help": ("Uses recent conversation context to help translate short phrases. It can also propagate an earlier mistake; turn it off if translations become less faithful. Processing stays local.", "Utilise le contexte récent pour aider à traduire les phrases courtes. Cela peut aussi propager une erreur précédente ; désactivez-le si la traduction devient moins fidèle. Le traitement reste local."),
    "translation_cache_help": ("Optional location for the experimental 7B translator. Existing files are not moved; the standard 3B translator retains its normal cache location.", "Emplacement facultatif du traducteur 7B expérimental. Les anciens fichiers ne sont pas déplacés ; le traducteur 3B standard conserve son cache habituel."),
    "offline_verify_help": ("Checks the selected local files and tries loading the engines without downloading. This can use RAM and take time. Missing components are reported.", "Contrôle les fichiers locaux sélectionnés et essaie les moteurs sans télécharger. Cela peut utiliser de la RAM et prendre du temps. Les composants manquants sont signalés."),
    "setup_enabled": ("Enabled", "Activé"),
    "setup_disabled": ("Disabled", "Désactivé"),
    "translation_preferences": ("Translation models and vocabulary…", "Modèles et vocabulaire de traduction…"),
    "model_manage_help": ("Compare the models and their resource needs. Select an absent model, download its files, cancel its preparation or delete its local cache. Browsing starts no download.", "Comparez les modèles et leurs besoins. Choisissez un modèle absent, téléchargez ses fichiers, annulez sa préparation ou supprimez son cache local. Parcourir la liste ne télécharge rien."),
    "profile_best_help": ("Prioritize full OpenAI Whisper large-v3. CPU and virtual memory may retain this model on a small computer, with a potentially long delay.", "Privilégie OpenAI Whisper large-v3 complet. Le CPU et la mémoire virtuelle peuvent conserver ce modèle sur petit ordinateur, avec une attente parfois longue."),
    "profile_fast_help": ("Choose a lighter model and fewer recognition candidates for shorter delays. Accuracy and language coverage may be lower.", "Choisit un modèle plus léger et explore moins de formulations pour réduire l’attente. La précision et la couverture des langues peuvent diminuer."),
    "profile_coverage_help": ("Prioritize Omnilingual and its 1,600+ advertised recognition languages when supported. Coverage does not guarantee the same accuracy in every language.", "Privilégie Omnilingual et ses plus de 1 600 langues de reconnaissance annoncées, si le moteur est compatible. Couvrir une langue ne garantit pas une précision identique pour toutes."),
    "ui_language_setting": ("Interface language", "Langue de l’interface"),
    "ui_language_auto": ("Automatic — system language", "Automatique — langue du système"),
    "ui_language_help": ("Automatic follows the device’s display language at each launch. French and English are available; other system languages use English. A manual choice is kept until you change it. This does not change recognition or translation languages.", "Automatique suit la langue d’affichage de l’appareil à chaque ouverture. L’interface existe en français et en anglais ; les autres langues système utilisent l’anglais. Un choix manuel reste mémorisé. Ce réglage ne change pas les langues parlées ou traduites."),
    "ui_language_detected": ("System: {locale} · Automatic would use {language}", "Système : {locale} · En automatique : {language}"),
    "settings_general": ("Application", "Application"),
    "settings_view": ("Settings presentation", "Présentation des réglages"),
    "settings_recognition": ("Recognition", "Reconnaissance"),
    "settings_text_voice": ("Text & voices", "Texte et voix"),
    "settings_files": ("Files & storage", "Fichiers et stockage"),
    "settings_intro": ("Settings grouped by purpose. Each option explains its effect; hover or focus a control for more help.", "Des réglages classés par usage. Chaque option explique son effet ; survolez une commande ou donnez-lui le focus pour en savoir plus."),
    "advanced_show": ("Show advanced settings", "Afficher les réglages avancés"),
    "advanced_hide": ("Hide advanced settings", "Masquer les réglages avancés"),
    "advanced_help": ("Shows processor and fine-tuning controls. Changing this view preserves your model, languages and current settings.", "Affiche le processeur et les réglages fins. Changer cette présentation conserve le modèle, les langues et les réglages actuels."),
    "settings_group_model": ("Model and spoken language", "Modèle et langue parlée"),
    "settings_group_capture": ("Speech and speakers", "Parole et interlocuteurs"),
    "settings_group_tuning": ("Fine-tuning · optional", "Réglages fins · facultatifs"),
    "settings_group_output": ("Saving and exports", "Enregistrement et exports"),
    "settings_group_format": ("How text is displayed", "Présentation du texte"),
    "settings_group_updates": ("Application updates", "Mises à jour du logiciel"),
    "settings_group_voices": ("Reading and conversation", "Lecture et conversation"),
    "settings_group_language": ("Language and guidance", "Langue et accompagnement"),
    "settings_group_storage": ("Where files are stored", "Emplacement des fichiers"),
    "settings_help_button": ("Explain this setting", "Expliquer ce réglage"),
    "setting_profile_help": ("Accuracy keeps full OpenAI Whisper large-v3 whenever its runtime can run, including a very slow CPU paging attempt. Speed picks a lighter route. Maximum coverage prioritizes languages. Files are prepared only on request or first use.", "Précision privilégie OpenAI Whisper large-v3, y compris par une tentative CPU avec mémoire virtuelle, parfois très lente. Rapidité choisit un parcours plus léger. Couverture maximale privilégie le nombre de langues. Les fichiers se préparent à la demande ou au premier usage."),
    "setting_tuning_intro": ("Automatic settings suit most jobs. A longer maximum fragment gives more context but can increase delay; speech pauses can end a fragment earlier.", "Les réglages automatiques conviennent à la plupart des usages. Un fragment maximal plus long donne du contexte mais peut augmenter l’attente ; une pause dans la parole peut le terminer plus tôt."),
    "setting_beam_help": ("How many candidate sentences recognition explores. Higher values can improve difficult speech and take longer. This is an effort setting, not an accuracy percentage. Keep 5–8 for accuracy, 1–3 for speed.", "Nombre de formulations explorées par la reconnaissance. Une valeur élevée peut aider sur une parole difficile et prend plus de temps. Ce n’est pas un pourcentage de fiabilité. Gardez 5 à 8 pour la précision, 1 à 3 pour la vitesse."),
    "setting_font_help": ("Changes transcript and translation text only, from 14 to 48. A− and A+ also work from the transcript. The audience window has its own size control.", "Modifie uniquement la taille du transcript et des traductions, de 14 à 48. A− et A+ restent disponibles dans le transcript. L’écran interlocuteur possède aussi son propre réglage."),
    "setting_speech_help": ("Read an original or translated line in its own language. French and English voices are included; other local voices can be downloaded when needed. No text is sent to an online speech service.", "Lit une ligne originale ou traduite dans sa propre langue. Les voix française et anglaise sont incluses ; les autres voix locales se téléchargent au besoin. Aucun texte n’est envoyé à un service vocal en ligne."),
    "setting_storage_help": ("Choose where new transcripts and optional microphone recordings are saved. Existing files are not moved. Storage and folders lists model/cache locations and measured sizes.", "Choisissez où enregistrer les nouveaux textes et les enregistrements micro facultatifs. Les anciens fichiers ne sont pas déplacés. Stockage et dossiers indique les caches, les modèles et leurs tailles mesurées."),
    "setting_video_help": ("Limit compressed online-video downloads. This does not limit local audio files or recording duration. Website restrictions can still require a local file or an authorized sign-in export.", "Limite le téléchargement compressé des vidéos en ligne. Cela ne limite ni les fichiers locaux ni la durée des enregistrements. Les restrictions d’un site peuvent nécessiter un fichier local ou votre export de connexion autorisé."),
    "quality_coverage": ("Maximum coverage", "Couverture maximale"),
    "quality_custom": ("Custom model", "Modèle personnalisé"),
    "profile_label": ("Your priority", "Votre priorité"),
    "setup_open": ("Guided setup", "Configuration guidée"),
    "setup_short": ("Help me choose", "M’aider à choisir"),
    "setup_hint": ("A few questions, explained choices", "Quelques questions, des choix expliqués"),
    "setup_title": ("Set up your workspace", "Préparer votre espace de travail"),
    "setup_subtitle": ("Four short steps. Review everything before applying. No recording or model download starts here.", "Quatre étapes courtes. Vérifiez le récapitulatif avant d’appliquer. Aucun enregistrement ni téléchargement de modèle ne démarre ici."),
    "setup_progress": ("Step {step} of {total}", "Étape {step} sur {total}"),
    "setup_step_use": ("What would you like to do?", "Que souhaitez-vous faire ?"),
    "setup_step_languages": ("Which languages and microphone?", "Quelles langues et quel microphone ?"),
    "setup_step_preferences": ("What matters most to you?", "Qu’est-ce qui compte pour vous ?"),
    "setup_step_review": ("Your settings, before applying", "Vos réglages, avant de les appliquer"),
    "setup_use_help": ("Choose a starting workspace. All five uses stay available afterwards in the sidebar.", "Choisissez votre espace de départ. Les cinq usages resteront disponibles ensuite dans la barre latérale."),
    "setup_languages_help": ("Automatic recognition is useful when you do not know the language. Live conversation uses your language and an optional known partner language; a third translation is optional.", "La détection automatique est utile si vous ne connaissez pas la langue parlée. La conversation live utilise votre langue et, si vous la connaissez, celle de l’autre personne. Une troisième traduction est facultative."),
    "setup_preferences_help": ("The same selected model stays selected if CPU paging is needed. Accuracy can be much slower than a conversation; the Speed profile is always available.", "Le modèle choisi reste le même si la mémoire virtuelle est nécessaire. La précision peut être bien plus lente qu’une conversation ; le profil Rapidité reste disponible."),
    "setup_keep_model": ("Keep my current model", "Conserver mon modèle actuel"),
    "setup_keep_model_help": ("Preserves your current checkpoint and processor choice. Choose an automatic priority instead only if you want to replace this configuration.", "Conserve le modèle et le processeur actuels. Choisissez une priorité automatique si vous voulez remplacer cette configuration."),
    "setup_review_help": ("Apply changes the listed preferences only. It keeps transcript text, history and files. It neither records nor downloads models. Prepare this model or your first job can prepare the required files afterwards.", "Appliquer modifie seulement les préférences indiquées. Le transcript, l’historique et les fichiers sont conservés. Aucun enregistrement ni téléchargement n’est lancé. Préparer ce modèle ou le premier traitement préparera ensuite les fichiers nécessaires."),
    "setup_back": ("Back", "Retour"),
    "setup_next": ("Continue", "Continuer"),
    "setup_apply": ("Apply these settings", "Appliquer ces réglages"),
    "setup_cancel": ("Keep my current settings", "Garder mes réglages actuels"),
    "setup_applied": ("Your workspace is ready. Start a job, or prepare its model first.", "Votre espace est prêt. Lancez un traitement, ou préparez d’abord son modèle."),
    "setup_busy": ("Finish or cancel the active job, recording or download before changing this configuration.", "Terminez ou annulez le traitement, l’enregistrement ou le téléchargement en cours avant de modifier cette configuration."),
    "setup_invalid_languages": ("Your language and the partner language must differ. Choose Automatic if the other language is unknown.", "Votre langue et celle de l’autre personne doivent être différentes. Choisissez Automatique si l’autre langue est inconnue."),
    "setup_translate": ("Also translate the text", "Traduire aussi le texte"),
    "setup_large_text": ("Transcript text size", "Taille du texte du transcript"),
    "setup_route": ("Planned model: {model}\nProcessing: {device}", "Modèle prévu : {model}\nCalcul : {device}"),
    "setup_review_line": ("{name}: {value}", "{name} : {value}"),
    "setup_review_privacy": ("Everything is processed on this device. Model downloads, online video and enabled update checks need Internet; speech and text are never sent for cloud inference.", "Tout est traité sur cet appareil. Les modèles à télécharger, les vidéos en ligne et les vérifications de mise à jour activées utilisent Internet ; la parole et le texte ne sont jamais envoyés pour une inférence dans le cloud."),
    "setup_recommended": ("Recommended", "Recommandé"),
    "workspace_tools_more": ("More session tools", "Autres outils de session"),
    "workspace_tools_less": ("Fewer tools", "Réduire les outils"),
    "workspace_tools_help": ("Review and correct lines, open an audience display, type a reply, prepare offline components or manage confidential sessions. Expanding this section does not change any setting.", "Révisez les phrases, ouvrez un écran interlocuteur, saisissez une réponse, préparez les composants hors ligne ou gérez une session confidentielle. Déplier cette section ne change aucun réglage."),
    "source_language_help": ("Choose Automatic when speech may change language, or choose a known spoken language to guide recognition. A spoken-language choice never translates the text by itself.", "Choisissez Automatique si la langue peut varier, ou une langue parlée connue pour guider la reconnaissance. Choisir une langue parlée ne traduit pas le texte à lui seul."),
    "text_tools_help": ("Add names and specialized vocabulary to help recognition. It is a hint, not a command to invent words. Your vocabulary stays local.", "Ajoutez des noms propres et du vocabulaire spécialisé pour aider la reconnaissance. Ce sont des indications, pas une consigne pour inventer des mots. Le vocabulaire reste local."),
    "interface_status": ("Private workspace · {version}", "Espace privé · {version}"),
    "help_hover_title": ("About this control", "À propos de cette commande"),
    "setup_test_mic": ("Test microphone levels", "Tester le niveau du micro"),
    "setup_test_mic_help": ("Opens a level meter for a short microphone check. It does not record, save or transcribe anything. Stop or close the test to release the microphone.", "Ouvre un indicateur de niveau pour vérifier le micro. Aucun son n’est enregistré, sauvegardé ou transcrit. Arrêtez ou fermez le test pour libérer le microphone."),
    "setup_mic_running": ("Speak: only the level is measured. No recording is being saved.", "Parlez : seul le niveau est mesuré. Aucun enregistrement n’est sauvegardé."),
    "setup_mic_error": ("Microphone unavailable. Check the selected input and system microphone permission.", "Microphone indisponible. Vérifiez l’entrée choisie et l’autorisation du microphone dans le système."),
    "setup_mic_idle": ("Microphone test stopped.", "Test du microphone arrêté."),
    "setup_mic_stop": ("Stop microphone test", "Arrêter le test du micro"),
}


def register(strings):
    for key, (english, french) in MESSAGES.items():
        strings["en"][key] = english
        strings["fr"][key] = french
    strings["en"]["chunk"] = "Maximum fragment length (seconds)"
    strings["fr"]["chunk"] = "Durée maximale d’un fragment (secondes)"
    strings["en"]["beam"] = "Recognition effort"
    strings["fr"]["beam"] = "Effort de reconnaissance"
    strings["en"]["quality_best"] = "OpenAI accuracy"
    strings["fr"]["quality_best"] = "Précision OpenAI"
    strings["en"]["quality_fast"] = "Speed"
    strings["fr"]["quality_fast"] = "Rapidité"
    strings["en"]["workspace_settings_help"] = "Application language and updates, recognition, text and voices, files and storage. Advanced controls stay optional. Changing their visibility preserves your choices."
    strings["fr"]["workspace_settings_help"] = "Langue et mises à jour du logiciel, reconnaissance, texte et voix, fichiers et stockage. Les commandes avancées restent facultatives. Les masquer conserve vos choix."
    for index, language in enumerate(("en", "fr")):
        strings[language]["model_help"] = MESSAGES["model_manage_help"][index]
        strings[language]["tip_language"] = MESSAGES["ui_language_help"][index]
