# Traduction et lecture locales — 3.3.1

## Lecture au clic / Click to speak

Cochez **Lire une ligne au clic**, sous les commandes du transcript ou dans **Écran interlocuteur**. Cliquez sur le texte original, la traduction ou la troisième langue : toute la phrase est lue dans la langue de cette ligne. Cela fonctionne aussi dans les modes fichiers, vidéos, conférence, dictée et dans la vue de lecture agrandie. Les lignes longues renvoyées à la ligne à l’écran restent une seule phrase ; les indices de confiance et les lignes vides ne sont pas lus.

Le choix est partagé entre les deux fenêtres. Il est **activé par défaut en traduction universelle live**, et mémorisé séparément pour le mode live et les autres modes. Si vous le décochez en live, ce choix reste conservé. Dans un transcript ordinaire, décochez pour modifier le texte ; recochez pour entendre sa version corrigée. Un double-clic, une sélection par glissement ou un défilement ne lance pas la lecture. Le clic simple attend environ une demi-seconde pour se distinguer d’un double-clic.

Chaque clic suit la langue de la ligne, même si vous avez choisi manuellement une autre voix dans la banque. Les voix locales déjà préparées ont priorité ; une voix système compatible peut servir de secours. Une voix locale manquante est proposée au téléchargement avec votre accord et ses informations de licence. Le catalogue vocal couvre moins de langues que la reconnaissance et la traduction ; la qualité et les variantes de prononciation dépendent de chaque voix. Un ancien import sans langue doit recevoir une langue dans **Réviser les phrases**, ou une langue parlée explicite dans les réglages, avant une lecture automatique fiable.

Cliquez sur une autre phrase pour remplacer la lecture en cours. **Arrêter** annule aussi la phrase en attente ; ce bouton existe dans les deux fenêtres. Pendant la lecture, la capture du micro est suspendue pour éviter de retranscrire les haut-parleurs. Elle reprend uniquement si l’application l’avait elle-même suspendue : une pause demandée par l’utilisateur est conservée. Vous pouvez préparer les langues et les voix avant un entretien pour rester entièrement hors ligne.

**English:** enable **Click a line to speak** in either window. Originals, translations and third-language lines use their own language, independent of a manually selected foreign-language voice. The shared checkbox is enabled by default for Universal live translation, with independently remembered choices for live and other tasks. Clicks replace pending playback; Stop cancels it. Drag selection, double-click selection and scrolling remain silent. Uncheck to edit ordinary transcripts. Prepared local voices are preferred; missing voices retain explicit download prompts and compatible system fallback. Voice coverage is narrower than ASR/translation coverage. Capture pauses during speech and resumes only when the application owns that pause.

## Nouveautés 3.3 : converser, vérifier, partager l’écran

**Le transcript reste visible pendant que les réglages défilent.** F11 agrandit toujours la lecture ; A− / A+ conserve le réglage de taille. **Écran interlocuteur** ouvre une fenêtre indépendante, déplaçable sur un autre écran, avec filtre de langue et police de 18 à 72 points. Aucun deuxième écran physique n’est requis pour l’ouvrir.

**Texte provisoire :** quand le moteur est disponible, un aperçu du tour en cours apparaît en jaune. Il peut changer. Ce passage rapide utilise un décodage allégé ; le résultat final est recalculé avec les réglages de précision choisis et le fragment audio complet. L’aperçu n’entre ni dans les exports ni dans l’historique. Il s’agit d’aperçus successifs locaux, pas d’une promesse de streaming mot par mot ni d’une latence fixe. Les fragments finalisés ont priorité ; les aperçus ralentissent automatiquement si le moteur met du temps, et un aperçu arrivé après la fin du tour est écarté. « Audio restant » compte les secondes capturées encore en attente de finalisation, pas une estimation de temps de calcul.

**Langues en cours de capture :** les sélecteurs restent disponibles en conversation. Les changements sont appliqués entre deux fragments ; les interventions déjà traduites conservent leur direction initiale. Les boutons de langues possibles permettent de confirmer une détection. Sur une paire connue, le profil automatique peut passer à un moteur général de précision déjà préparé et compatible avec les deux langues ; il ne télécharge pas un nouveau modèle au milieu de l’entretien. La détection identifie une langue, pas une personne. Un changement de langue au sein d’une phrase reste difficile et n’est pas une attribution certaine de langue à chaque mot.

**Réviser les phrases** ouvre les originaux et traductions sans modifier l’ordre Unicode conservé dans les fichiers. Un aperçu facilite la lecture des écritures de droite à gauche. Sélectionnez une intervention, corrigez le texte ou la langue, ajoutez si besoin un nom de locuteur, puis enregistrez. Une modification de l’original invalide sa traduction et ses anciens indices ; **Retraduire cette phrase** recalcule uniquement cette intervention et sa troisième langue. Une traduction arrivée après une correction plus récente ne l’écrase pas. **Voir les corrections** expose l’historique ; JSON et les fichiers chiffrés le conservent. Les exports TXT/SRT/VTT/CSV restent des vues du texte courant. Une différence de nombres déclenche une invitation à vérifier, sans affirmer que le sens est faux.

**Réécouter cette phrase** lit le passage associé lorsque son fichier audio existe encore. Pour les nouvelles sessions enregistrées, conservez l’audio du micro pour pouvoir relire les anciens passages ; un audio supprimé ou un téléchargement temporaire déjà nettoyé ne peut pas être réécouté. Les fichiers locaux importés gardent leur liaison avec leur source. Les phrases écrites n’ont pas d’audio original.

**Écrire et parler** accepte une réponse dans votre langue, la traduit vers l’autre langue confirmée, l’ajoute au log et la fait lire par une voix locale ou système disponible. La capture se suspend pendant la lecture, comme pour la lecture habituelle. Les demandes de voix manquantes conservent leur confirmation et leurs informations de licence.

## Préparer une utilisation sans Internet

Dans **Préparer hors ligne**, choisissez les langues de l’entretien dans les sélecteurs principaux, puis préparez le profil. Le bouton de téléchargement est explicite ; les voix disponibles et leurs licences sont présentées. **Vérifier sans téléchargement** charge uniquement les modèles locaux et exerce reconnaissance, traduction et voix disponibles. Un moteur absent ou une voix non disponible reste clairement signalé ; aucune couverture vocale n’est inventée. Le test de reconnaissance s’appuie sur une voix locale préparée lorsque son format le permet.

MADLAD 3B reste le moteur de traduction standard. Le modèle facultatif **MADLAD 7B MT-BT int8**, conversion Nextcloud-AI d’un modèle Google, occupe environ 8,33 Go. Il exige 28 Go de RAM totale et 14 Go disponibles ; le GPU n’est utilisé qu’avec au moins 10 Go de VRAM réellement libres après la reconnaissance. Le CPU reste possible, avec un délai plus élevé. Choisissez un dossier sur un disque assez grand ; **Stockage et dossiers** expose aussi cet emplacement. Un modèle plus gros n’est pas automatiquement plus juste dans chaque langue.

La **traduction contextuelle**, facultative, conserve un court contexte de la même langue ; si la séparation des phrases n’est pas conservée par le modèle, l’application revient à la phrase seule. Le glossaire utilise une ligne `terme source | langue de destination | traduction imposée`, par exemple `Maple Street | fr | rue Maple`. Les termes ne sont imposés que si les marqueurs survivent au décodage ; sinon le moteur revient à la traduction habituelle. Ces options restent à évaluer selon les langues et les termes utilisés.

## Session confidentielle et fichier chiffré

**Confidentialité → Session confidentielle** désactive les nouvelles sauvegardes automatiques du texte, de l’audio, de la récupération et de l’historique. Le texte reste en mémoire jusqu’à la fermeture. Les fichiers précédemment créés restent présents ; les exports manuels restent possibles. Ce réglage se réinitialise au lancement suivant et son état est rappelé dans le statut.

Vous pouvez enregistrer un fichier `.ltps` protégé par mot de passe : AES-256-GCM authentifie les données et Scrypt dérive la clé avec un sel aléatoire. Le mot de passe n’est pas sauvegardé et ne peut pas être récupéré. Le fichier contient le texte, ses traductions et corrections, **pas l’audio**. L’ouverture d’un fichier chiffré active le mode confidentiel. Ce chiffrement de fichier ne protège pas un ordinateur déjà compromis, la mémoire ou un export manuel en clair.

## English — 3.3 conversation tools

The transcript stays visible while settings scroll. Live previews are provisional, use idle inference capacity and never enter exports. The backlog counts captured audio awaiting final processing. Confirm or change languages during capture; changes apply at the next turn and preserve earlier routing. A prepared compatible accuracy model can replace the broad-coverage recognizer once both languages are known.

**Review turns** preserves logical Unicode originals, timed audio links and a revision history. Edit an original or translation, name a speaker, replay linked audio or retranslate that turn only. Source edits invalidate old translation/confidence information; stale asynchronous results never overwrite newer edits. Number differences prompt review, not a semantic verdict.

**Audience display** is a separate movable window with language filtering and 18–72 point text. **Type and speak** translates a written reply to the confirmed other language, adds it to the log and reads it locally. **Prepare offline** explicitly prepares models/voices and exercises available local engines without downloads during verification. Optional MADLAD 7B, contextual translation and a destination-specific glossary retain documented resource and quality limits.

**Confidential sessions** create no new automatic transcript/audio/history/recovery files. Save text and revisions in a password-encrypted `.ltps` file when needed. Audio is excluded. Existing files remain and manual plaintext exports are possible. Passwords are not saved or recoverable; confidentiality resets on the next app launch.

## Démarrer une conversation

Cliquez **Traduction universelle live**. Choisissez votre langue dans **Langue de destination / votre langue**. Laissez **Autre langue de la conversation** sur détection automatique, ou choisissez une langue connue. La recherche accepte un nom français/anglais et un code. Le troisième sélecteur ajoute, si nécessaire, une langue commune à tout le compte rendu.

Lancez **Enregistrer**. Le modèle de reconnaissance et MADLAD doivent être préparés avant la capture ; la progression explique les premiers téléchargements. Les modèles préparés s'utilisent hors ligne. La traduction exige 12 Go de RAM totale et 6 Go disponibles ; l'interface signale une machine insuffisante. Un modèle vocal compatible est sélectionné automatiquement ; le bouton **Modèle vocal** permet de le changer.

## Deux langues, deux directions

En automatique, deux langues reconnues avec une indication de langue d'au moins 0,55 et du texte exploitable constituent la paire. L'application ne déduit jamais une langue à partir d'un pays ou d'une personne. Une fois la paire reconnue, français → arabe et arabe → français, par exemple, sont routés sans changer de bouton. Avant que la paire soit complète, la parole étrangère est traduite vers votre langue ; une ligne dans votre propre langue peut rester en attente. Elle est complétée lorsque l'autre langue est connue.

Qwen et Parakeet utilisent aussi le détecteur textuel local GlotLID lorsqu’ils ne fournissent pas de score de langue. Ce complément de 1,69 Go est préparé avant la capture et reste dans le cache Omnilingual partagé ; il ne télécharge rien pendant la reconnaissance. Pour Qwen, un désaccord entre sa langue annoncée et le détecteur réduit l’indication au lieu de forcer une paire. Si le détecteur n’est pas préparé en mode hors ligne, ou si le texte est ambigu, confirmez les langues avec les boutons proposés. Ce score d’identification n’est pas une probabilité de transcription ou de traduction correcte.

Une détection peut se tromper même avec un score élevé. Si la paire est fausse, corrigez l’autre langue dans son sélecteur : le changement sera appliqué au prochain fragment. Le changement manuel de modèle pendant l’enregistrement reste bloqué ; seul le choix automatique entre moteurs déjà préparés se fait entre deux fragments. La troisième langue est facultative ; une traduction identique à l’original ou à la destination n’est pas affichée deux fois.

## Texte et rythme de traitement

L'original est blanc, la traduction verte et la troisième langue bleue. Chaque groupe garde sa langue et son repère temporel. L'arabe et les écritures de droite à gauche sont présentés dans leur sens de lecture ; les exports et la lecture vocale gardent l'ordre Unicode logique.

La capture écoute des fenêtres de 32 ms et recherche la parole avec Silero VAD. Une pause d'environ 0,7 seconde termine une prise de parole ; un tour long est borné à 12 secondes. La barre indique la durée capturée, pas un pourcentage de traduction calculé. Le statut donne le stade réel et le nombre de fragments en attente. L'original peut apparaître pendant la traduction. **Pause** suspend la capture ; **Arrêter** termine et traite le reste déjà capturé. Parlez chacun votre tour, avec une courte pause entre deux interventions.

**A− / A+** règlent la police entre 14 et 48. **F11** masque les réglages et agrandit la fenêtre de lecture sur son écran courant. **Échap** quitte la lecture agrandie. Les commandes Pause/Arrêter restent accessibles. Le mode reste utilisable sur une configuration à plusieurs écrans.

## Reconnaissance, traduction et voix

Le profil multilingue automatique privilégie Omnilingual sur une machine compatible, puis le meilleur Whisper qui tient dans les ressources disponibles. Qwen 1.7B demeure le profil général de précision sur GPU compatible ; sa couverture de 30 langues est plus étroite. Parakeet privilégie la vitesse CPU pour 25 langues européennes. Le sélecteur affiche précision relative, rapidité et multilinguisme séparément, ainsi que les raisons matérielles d'indisponibilité.

Le choix automatique tient compte du couple reconnaissance/traduction. Si le premier modèle de reconnaissance laisse trop peu de mémoire au traducteur, l’application libère ce modèle, réserve la traduction puis recherche le meilleur moteur vocal compatible avec la mémoire restante. Le diagnostic indique cette réserve. Sous Windows, la mémoire disponible tient aussi compte de la limite d’engagement du système : d’autres logiciels peuvent réduire les ressources utilisables même si de la RAM physique semble libre.

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

## Aides, stockage et médias en ligne — 3.3

Les principales commandes montrent une aide au survol et au focus clavier. **Stockage et dossiers**, en haut de la fenêtre, affiche les besoins, les dossiers exacts des modèles/voix/historique/exports et leurs tailles. Comptez environ 5,9 Go pour le minimum avec Tiny, 14,4 Go pour Omnilingual + traduction et 53 Go pour tout le catalogue ; prévoyez 12 Go libres avant installation ou 95 Go avec les caches de toutes les options. L’audio enregistré ajoute environ 115 Mo/heure et il n’existe pas de maximum absolu.

**Vidéo en ligne** accepte YouTube, les autres sites pris en charge et les liens média HTTP(S). **Options vidéo et diagnostic** actualise le moteur officiel vérifié et règle la limite. L’audio compressé est vérifié puis traité localement ; l’annulation arrête aussi le téléchargement. Une connexion éventuelle utilise uniquement l’export de cookies que vous choisissez, via une copie temporaire. **Utiliser un fichier local…** offre un autre parcours lorsqu’un site refuse l’import. [Dossiers, budgets et procédure détaillée](../README.md#storage-requirements-and-locations--stockage-et-dossiers).
