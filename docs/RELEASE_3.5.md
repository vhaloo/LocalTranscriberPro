# Local Transcriber Pro 3.5.0

**Le modèle CPU choisi malgré le manque de RAM, et des mises à jour discrètes.**

- CPU — mémoire virtuelle : tente le modèle demandé sans le remplacer, dans des processus de reconnaissance/traduction isolés et annulables. Runtime, langue, intégrité et espace disque restent contrôlés.
- La pagination reste gérée par Windows/macOS/Linux, sans changement système. Elle peut être très lente ou échouer à la limite mémoire du système.
- Vérification à chaque démarrage activé : aucune erreur ni fenêtre intrusive hors ligne ou si l'application est à jour ; nouvelle version, progression et disponibilité dans l'en-tête.
- Windows : téléchargement signé, vérification SHA-256, installation et relance au repos activés par défaut et désactivables. Les tâches, fenêtres ouvertes et sessions privées contenant du texte reportent l'installation automatique ; « Plus tard » reporte à la prochaine ouverture.
- Toutes les fonctions 3.4 conservées : interface par usage, OpenAI Whisper large-v3 par défaut sur matériel compatible, conversation multilingue, écran déporté, lecture au clic, révision, confidentialité, fichiers/vidéos et exports.
- README, aide bilingue et douze captures réelles actualisés. Cinq paquets : Windows complet/CPU et macOS/Linux expérimentaux, avec manifeste signé.

Les modèles préparés traitent audio et texte localement. Internet est nécessaire aux téléchargements et vérifications de version ; aucun audio ni transcript n'est envoyé à GitHub. Mac/Linux restent expérimentaux avec remplacement manuel, sans validation physique du micro/GPU.

[Guide et captures](https://github.com/vhaloo/LocalTranscriberPro#readme) · [Validation](https://github.com/vhaloo/LocalTranscriberPro/blob/main/docs/VALIDATION_3.5.md)

Validation : 253 tests Windows, tests sources/natifs Mac/Linux réussis, dix contrôles du runtime Windows installé et installation automatique réelle avec relance après plus de 60 secondes d’inactivité. Les 82 sessions et 269 fichiers existants sont préservés.
