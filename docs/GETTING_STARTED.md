# Démarrer simplement / Getting started — 3.7.0

## M’aider à choisir

Le bouton en haut de la barre latérale ouvre un assistant réutilisable. Il est aussi proposé au premier lancement d’un nouveau profil. Un profil existant conserve ses réglages et n’est pas interrompu par cet assistant.

1. **Usage et interface.** Choisissez fichiers, traduction live, conférence, dictée ou vidéo. Automatique suit la langue d’affichage de l’appareil à chaque ouverture ; l’interface existe en français et en anglais, avec repli anglais pour les autres langues système. Le choix manuel reste mémorisé. Ce choix n’impose aucune langue à la reconnaissance ou à la traduction.
2. **Langues et microphone.** Gardez la détection si la langue parlée est inconnue. En traduction live, choisissez votre langue, l’autre langue si elle est connue et une troisième langue facultative. Un test du niveau sonore de 12 secondes peut être lancé explicitement : il ne conserve pas d’audio et ne fait ni transcription ni traduction. Changer de page ou fermer l’assistant libère le test.
3. **Priorités et lisibilité.** Précision OpenAI conserve Whisper large-v3, y compris avec CPU/mémoire virtuelle si nécessaire. Rapidité adapte le choix à la mémoire physique ; Multilinguisme maximal privilégie la couverture disponible. Conserver mon choix laisse le modèle et le processeur actuels. Les réglages de police, audio conservé, locuteurs et lecture au clic décrivent leur effet. La mémoire virtuelle peut être extrêmement lente et reste soumise aux limites du système.
4. **Vérifier puis appliquer.** Le récapitulatif montre le modèle prévu, son traitement et les options retenues. Retour permet de corriger ; Annuler conserve les préférences précédentes. Appliquer mémorise les choix et conserve la conversation affichée. Le téléchargement du modèle attend le premier usage ou **Préparer ce modèle**.

L’assistant reste disponible plus tard. Terminez la capture, les calculs et la lecture vocale avant de modifier une configuration complète. Les langues de conversation peuvent toujours être ajustées dans leurs sélecteurs pendant une conversation, entre deux fragments.

## Les réglages au bon endroit

| Page | Ce qu’elle contient |
|---|---|
| Application | Langue de l’interface, assistant, affichage des options avancées, vérification et installation des mises à jour |
| Reconnaissance | Modèle, langue parlée, séparation des personnes, VAD/nettoyage/chevauchement ; processeur et durée/effort en options avancées |
| Texte et voix | Traduction locale, vocabulaire, taille du texte, disposition, repères temporels, indices facultatifs, voix et lecture lente |
| Fichiers et stockage | Dossier de sortie, emplacements et espace, confidentialité, audio conservé, sous-titres et limite du téléchargement vidéo |

Chaque réglage comprend une explication lisible. Le bouton **?** ouvre la même aide ; le survol ou le focus clavier l’affiche en bulle. **F1** affiche l’aide de la commande ciblée, **Échap** ferme d’abord cette bulle. Masquer les réglages avancés conserve leurs valeurs.

La langue parlée est aussi accessible juste au-dessus de la source pour les usages ordinaires. En traduction live, les trois sélecteurs de conversation restent au premier plan. **Autres outils de session** développe les outils moins fréquents, sans retirer de fonction. **Ctrl+,** ouvre les paramètres ; **Ctrl+F** cherche dans le texte ; **F11** agrandit la lecture et **A− / A+** modifie sa taille.

## Préparer sans télécharger inutilement

Le catalogue laisse les modèles absents visibles. **Télécharger** ne prépare que le modèle choisi ; **Supprimer** demande confirmation avec les chemins concernés. Le choix d’un profil automatique ne télécharge pas toute la liste. **Texte et voix → Traduction locale et vocabulaire** permet d’enregistrer le choix du traducteur sans le charger ; la préparation et la vérification locale ont leurs propres boutons. Les modèles, voix et composants déjà préparés s’utilisent hors ligne.

La taille d’installation, les emplacements réels et l’usage du disque figurent dans **Stockage et dossiers** et dans le [README](../README.md). Les modèles volumineux restent séparés du logiciel et survivent à ses mises à jour.

## English quick start

**Help me choose** asks four short sets of questions: use/interface, speech and conversation languages/microphone, priorities/readability, then a review. Back/Cancel preserve the previous preferences; Apply saves only the reviewed choices and retains the displayed conversation. Setup does not run inference, save audio or download weights. Its explicit 12-second microphone level test releases the input on navigation or closure.

New profiles follow system display language on each launch. French and English are supported; other system languages use English. Choose Automatic, Français or English in **Settings → Application**. Existing explicit choices survive migration. UI language is independent of speech, translation and voices.

Settings has four pages: **Application**, **Recognition**, **Text & voices**, **Files & storage**. Every option has an inline explanation, **?** button and hover/focus/F1 help. Escape dismisses the help. Advanced presentation retains existing model/processor/tuning values. The sidebar keeps five uses and expandable session tools. Recognition preparation stays on demand; translation preferences can be saved without preparing a model. See the [conversation guide](TRANSLATION.md) for speech, live translation, revision, audience display and privacy.
