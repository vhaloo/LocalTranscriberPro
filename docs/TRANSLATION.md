# Traduction et lecture locales — 3.1.0

## Démarrer une conversation

Cliquez **Traduction universelle live**. Choisissez votre langue dans **Langue de destination / votre langue**. Laissez **Autre langue de la conversation** sur détection automatique, ou choisissez une langue connue. La recherche accepte un nom français/anglais et un code. Le troisième sélecteur ajoute, si nécessaire, une langue commune à tout le compte rendu.

Lancez **Enregistrer**. Le modèle de reconnaissance et MADLAD doivent être préparés avant la capture ; la progression explique les premiers téléchargements. Les modèles préparés s'utilisent hors ligne. La traduction exige 12 Go de RAM totale et 6 Go disponibles ; l'interface signale une machine insuffisante. Un modèle vocal compatible est sélectionné automatiquement ; le bouton **Modèle vocal** permet de le changer.

## Deux langues, deux directions

En automatique, deux langues reconnues avec une indication de langue d'au moins 0,55 et du texte exploitable constituent la paire. L'application ne déduit jamais une langue à partir d'un pays ou d'une personne. Une fois la paire reconnue, français → arabe et arabe → français, par exemple, sont routés sans changer de bouton. Avant que la paire soit complète, la parole étrangère est traduite vers votre langue ; une ligne dans votre propre langue peut rester en attente. Elle est complétée lorsque l'autre langue est connue.

Une détection peut se tromper même avec un score élevé. Si la paire est fausse, arrêtez la capture et fixez l'autre langue avant de repartir. Le changement de langue/modèle pendant l'enregistrement est bloqué pour garder une session cohérente. La troisième langue est facultative ; une traduction identique à l'original ou à la destination n'est pas affichée deux fois.

## Texte et rythme de traitement

L'original est blanc, la traduction verte et la troisième langue bleue. Chaque groupe garde sa langue et son repère temporel. L'arabe et les écritures de droite à gauche sont présentés dans leur sens de lecture ; les exports et la lecture vocale gardent l'ordre Unicode logique.

La capture écoute des fenêtres de 32 ms et recherche la parole avec Silero VAD. Une pause d'environ 0,7 seconde termine une prise de parole ; un tour long est borné à 12 secondes. La barre indique la durée capturée, pas un pourcentage de traduction calculé. Le statut donne le stade réel et le nombre de fragments en attente. L'original peut apparaître pendant la traduction. **Pause** suspend la capture ; **Arrêter** termine et traite le reste déjà capturé. Parlez chacun votre tour, avec une courte pause entre deux interventions.

**A− / A+** règlent la police entre 14 et 48. **F11** masque les réglages et agrandit la fenêtre de lecture sur son écran courant. **Échap** quitte la lecture agrandie. Les commandes Pause/Arrêter restent accessibles. Le mode reste utilisable sur une configuration à plusieurs écrans.

## Reconnaissance, traduction et voix

Le profil multilingue automatique privilégie Omnilingual sur une machine compatible, puis le meilleur Whisper qui tient dans les ressources disponibles. Qwen 1.7B demeure le profil général de précision sur GPU compatible ; sa couverture de 30 langues est plus étroite. Parakeet privilégie la vitesse CPU pour 25 langues européennes. Le sélecteur affiche précision relative, rapidité et multilinguisme séparément, ainsi que les raisons matérielles d'indisponibilité.

**Omnilingual CTC 1B v2** est une reconnaissance CPU de plus de 1 600 langues, choisie par le profil universel sur une machine compatible (16 Go de RAM totale, 10 Go disponibles, 5,6 Go de téléchargement avec GlotLID). Fixer une langue de conversation hors du catalogue Whisper le sélectionne sur une machine compatible. Les heures sont celles du fragment complet ; aucun alignement mot à mot ni score de transcription n'est inventé. Son identification de langue vient du texte reconnu par GlotLID v3, avec plus de 2 000 étiquettes de langue et d'écriture. Une langue reconnue par le modèle peut donc ne pas être identifiée automatiquement. Le modèle n'est pas systématiquement plus précis que Whisper ; les deux restent sélectionnables.

MADLAD-400 3B int8 expose 452 jetons de langue/variantes dans ce paquet. La présence dans le catalogue n'est pas une validation de toutes les directions. Certains dialectes aboutissent à une écriture plus standard. Le résultat traduit correspond au groupe source entier ; les mots traduits n'ont pas de temps d'alignement individuels. [Couverture et essais](LANGUAGES.md).

## Dire des lignes à voix haute

Sélectionnez les lignes du transcript, puis **Lire les lignes**, ou clic droit → **Lire les lignes sélectionnées**. Les lignes originales et traduites gardent chacune leur langue. Une sélection partielle dans une conversation lit les lignes correspondantes complètes pour préserver l'ordre logique des écritures. Sans sélection, la dernière ligne traduite est lue.

**Banque de voix** propose Auto, 47 voix locales et les voix compatibles installées dans le système. Auto utilise d'abord la voix locale déjà préparée puis une voix système correspondante. Le français et l'anglais Piper sont inclus dans le paquet Windows. Une voix manquante téléchargeable est proposée avec sa langue ; aucune voix n'est téléchargée sans accepter. MMS complète notamment le créole haïtien, le pendjabi, le bengali et le somali, avec une licence **CC BY-NC 4.0** explicitement signalée. Il n'y a pas de voix locale intégrée pour chaque langue du catalogue de traduction.

Un choix manuel de voix change la prononciation, pas la traduction. Windows expose les voix System.Speech installées, macOS les voix `say`, Linux celles d'espeak/espeak-ng lorsqu'ils sont disponibles. L'énumération sur ces systèmes ne garantit pas qu'une voix existe pour chaque langue. La langue de l'interface suit le système au premier lancement ; les voix du système figurent avec leur langue dans la banque.

**Voix lente** réduit le débit. **■ Voix** interrompt la lecture. La capture se met en pause pendant la lecture pour éviter l'écho ; elle reprend uniquement si l'application l'avait elle-même suspendue. Une ligne est limitée à 2 500 caractères lors de la lecture, sans tronquer le transcript enregistré. Le clic droit permet aussi de réécouter le dernier fragment audio capturé pendant cette session.

## Indices facultatifs

**Indices de confiance** masque ou affiche de petites annotations sous les groupes. La reconnaissance utilise le logarithme de probabilité moyen disponible, ou les probabilités de mots ; la traduction utilise le score normalisé du décodeur. Les indices sont transformés sur 100 pour la lecture. Ils ne sont pas calibrés : **90/100 ne signifie pas 90 % de chances que le sens soit correct**, et les scores de moteurs/langues différents ne se comparent pas directement. Indisponible est affiché si le moteur ne fournit pas l'information.

L'indice de langue concerne la détection, pas la traduction. Une valeur inférieure à 0,65 est signalée comme incertaine. Omnilingual indique une détection à partir du texte, Whisper une détection vocale. Les annotations ne sont jamais injectées dans le texte transcrit ou les exports. Les métadonnées structurées restent dans JSON.

## Deux voix qui se chevauchent — expérimental

La case **2 voix superposées · essai**, désactivée par défaut, prépare SepFormer WHAMR 16 kHz (~113 Mo), puis tente une séparation en deux canaux par fenêtres de six secondes. Chaque canal passe dans la reconnaissance et la traduction locales. Les canaux ne sont pas des identités stables et peuvent changer entre fragments. Ce modèle a été entraîné sur des mélanges anglais ; son efficacité dans les autres langues n'est pas garantie. Il peut omettre ou dupliquer des mots, y compris lorsqu'une seule personne parle. Il ralentit le traitement.

L'identification habituelle des personnes reste une option distincte, appliquée à la session enregistrée. Le mode de séparation n'est ni une preuve d'identité, ni une reconstruction certaine. Gardez l'audio source si une révision est nécessaire. Les résultats des essais contrôlés sont dans [la validation](VALIDATION_3.1.md).

## Historique et sauvegardes

Chaque session termine avec TXT, SRT, VTT, CSV et JSON dans le dossier choisi ; les textes originaux/traduits restent associés. Les sauvegardes progressives TXT/JSON et l'audio de récupération protègent une session interrompue. Historique rouvre le résultat ; Effacer vide l'écran sans effacer les fichiers sauvegardés. Le transcript bilingue est protégé contre les corrections accidentelles de ses associations ; le transcript simple conserve l'édition.

Pour les noms, nombres et décisions importants, réécoutez et faites confirmer le sens. Ces outils facilitent un échange ; leur couverture annoncée ne garantit pas une interprétation correcte de toute langue, tout dialecte ou toute situation sonore.
