# Local Transcriber Pro 3.3.0

La 3.3 conserve toutes les fonctions et améliore les conversations, la révision du texte et les mises à jour, avec des traitements locaux après préparation des modèles.

- Aperçus provisoires du texte, suivi de l’audio restant et confirmation des langues pendant la capture.
- Révision de l’original et de sa traduction, réécoute du passage, historique des corrections et retraduction ciblée.
- Fenêtre interlocuteur indépendante, texte agrandissable, réponses écrites puis traduites et lues.
- Préparation hors ligne, sessions en mémoire et sauvegardes chiffrées facultatives.
- MADLAD 7B facultatif, contexte et glossaire ; sélection vocale tenant compte des ressources de toute la chaîne.
- Manifestes de mise à jour signés Ed25519 et paquet Windows CPU plus léger : **0,432 Go**, contre **2,106 Go** pour le paquet CUDA + CPU.

La mise à niveau Windows 3.2 → 3.3 est vérifiée sur la machine locale : paramètres, historique et fichiers conservés. Les 185 tests Windows et 12 essais de l’exécutable installé passent, dont un import YouTube public. Le code passe aussi sur macOS/Linux, et leurs archives ont été contrôlées dans les environnements natifs. Ces deux distributions restent **expérimentales**, sans validation physique des microphones/GPU. Les mesures linguistiques publiées restent des diagnostics d’erreurs, sans pourcentage de fiabilité du sens inventé.

[Guide de conversation](https://github.com/vhaloo/LocalTranscriberPro/blob/v3.3.0/docs/TRANSLATION.md) · [Langues, stockage et captures](https://github.com/vhaloo/LocalTranscriberPro/blob/v3.3.0/README.md) · [Validation détaillée](https://github.com/vhaloo/LocalTranscriberPro/blob/v3.3.0/docs/VALIDATION_3.3.md)

English — private conversation tools, with every previous function retained:

- Provisional live text and captured-audio backlog, with final transcription priority.
- Confirmable language candidates and language changes between turns.
- Automatic model admission for combined ASR/translation memory, with pinned local language hints for Qwen/Parakeet when needed.
- Paired original/translation editing, precise source replay, selective retranslation and revision history.
- Independent audience window, large text and typed translated/spoken replies.
- Offline profile preparation and optional password-encrypted transcript sessions.
- Optional pinned MADLAD 7B translation, context and glossary controls.
- Settings that scroll while the transcript stays visible.
- Ed25519-signed update manifests and a separate lighter Windows CPU package.

Windows is the supported installation. Apple Silicon macOS and Linux packages remain experimental. Language coverage is not a guarantee of semantic correctness; confidence indices are not calibrated probabilities. See the validation report, conversation guide and complete README language inventory.

Native Authenticode signing and Apple notarization are not supplied by the independent update-manifest signature. The maintainer must configure those platform certificates separately.
