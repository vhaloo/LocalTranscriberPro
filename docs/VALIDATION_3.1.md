# Validation 3.1.0 — 8 octobre 2026

## Périmètre

Windows 11 x64, Ryzen 5800X, 64 Go de RAM, NVIDIA RTX 5070 12 Go. Les chiffres ci-dessous décrivent cette validation locale et un petit échantillon diagnostique. Ils ne certifient aucune langue, aucun dialecte, aucun niveau de littératie ni un usage d'interprétation professionnel. macOS/Linux conservent le support source et les constructions CI ; aucun essai physique de la 3.1 sur ces systèmes n'est revendiqué.

## Contrôles logiciels et interface

La suite couvre les admissions matérielles, les modèles, les réglages/migrations, le cache vérifié, les annulations, les exports, les sauvegardes concurrentes, les queues audio, les limites de diarisation, le découpage de parole, le routage bilingue, les écritures RTL, les indices et les contrôles de mise à jour. **133 tests automatisés passent**, ainsi que Ruff et la compilation Python avant publication.

Le contrôle de l'interface réelle, avec historique/réglages isolés et texte de démonstration, vérifie la sélection logique arabe/français pour la lecture, la copie Unicode, la protection des associations bilingues, F11/Échap, la police 14–48 et le masquage des indices sans altérer le transcript simple. La zone de lecture passe de 187 à 1 139 pixels de haut. Un défaut qui étendait le plein écran sur plusieurs moniteurs a été remplacé par l'agrandissement de la fenêtre sur son écran courant.

Un cas réel de fastText retournant `1.0000100135803223` a motivé une normalisation dans [omnilingual.py](../src/omnilingual.py) et un test de non-régression : ce léger dépassement ne doit pas casser la validation/sauvegarde d'une transcription.

## Évaluation de reconnaissance : 70 extraits

Deux extraits de 3 à 14 secondes par groupe, sélectionnés de manière déterministe parmi les premières lignes du split de test. Les références et l'audio restent dans les artefacts locaux ignorés, sans redistribution. Les origines et hashes sont conservés dans le manifeste local.

- [UBC-NLP/Casablanca](https://huggingface.co/datasets/UBC-NLP/Casablanca) : 16 extraits, huit groupes de dialectes arabes ; licence CC BY-NC-ND, test local uniquement.
- [Google FLEURS](https://huggingface.co/datasets/google/fleurs) : 52 extraits, 26 configurations ; principalement parole lue.
- [Corpus CMU haïtien, miroir utilisé](https://huggingface.co/datasets/phatjmo/cmu_haitian) : deux extraits du split test. Le chevauchement éventuel avec les données d'entraînement des moteurs n'a pas été audité.

Whisper large-v3 CUDA et Omnilingual CTC 1B v2 CPU ont chacun traité les 70 mêmes extraits, avec les connexions réseau bloquées pendant chargement et inférence. Le passage Whisper a aussi produit une traduction française MADLAD pour chaque extrait ; sans références de traduction ni évaluateurs natifs, sa justesse sémantique n'est pas certifiée. Omnilingual a été évalué séparément en reconnaissance.

Le CER est la distance d'édition en caractères divisée par le nombre de caractères de référence. Normalisation NFKC, casse, ponctuation, diacritiques et quelques variantes orthographiques arabes ; espaces retirés du CER. Agrégation pondérée par la longueur des références. **Plus bas est meilleur ; un résultat peut dépasser 100 %.** Les chiffres ne sont ni des scores de confiance ni des mesures représentatives de tous les locuteurs. Deux extraits par groupe ne suffisent pas à classer les moteurs généralement.

| Groupe (2 extraits chacun) | CER Whisper | CER Omnilingual |
|---|---:|---:|
| Créole haïtien | 10.0 % | 23.6 % |
| Espagnol | 0.4 % | 0.9 % |
| Persan | 4.5 % | 1.9 % |
| Pendjabi | 29.0 % | 8.4 % |
| Lingala | 14.0 % | 6.5 % |
| Yoruba | 35.8 % | 14.9 % |
| Somali | 100.0 % | 9.1 % |
| Haoussa | 23.7 % | 7.6 % |
| Igbo | 59.5 % | 7.7 % |
| Amharique | 107.5 % | 8.9 % |
| Swahili | 3.6 % | 0.6 % |
| Turc | 5.4 % | 6.0 % |
| Gujarati | 12.3 % | 6.2 % |
| Français | 2.2 % | 3.5 % |
| Anglais | 2.4 % | 3.0 % |
| Algeria | 17.9 % | 10.7 % |
| Egypt | 45.1 % | 28.0 % |
| Jordan | 20.6 % | 21.6 % |
| Mauritania | 50.0 % | 61.8 % |
| Morocco | 30.9 % | 25.4 % |
| Palestine | 17.3 % | 9.5 % |
| UAE | 25.6 % | 18.0 % |
| Yemen | 25.6 % | 22.3 % |
| Mandarin | 0.0 % | 13.6 % |
| Cantonais | 3.9 % | 11.8 % |
| Hindi | 102.0 % | 2.6 % |
| Ourdou | 38.5 % | 36.7 % |
| Tamoul | 11.9 % | 7.9 % |
| Bengali | 14.9 % | 5.0 % |
| Pachto | 74.6 % | 15.9 % |
| Thaï | 14.7 % | 23.9 % |
| Vietnamien | 1.6 % | 11.1 % |
| Indonésien | 0.0 % | 0.0 % |
| Japonais | 8.6 % | 26.7 % |
| Coréen | 5.3 % | 5.3 % |

Sur l'ensemble de ces seuls extraits, CER pondéré : **Whisper 27,4 % ; Omnilingual 12,3 %**. Ces résultats motivent le profil universel étendu, tout en conservant Whisper pour les situations où il est meilleur. Plusieurs langues et dialectes restent difficiles. La vitesse mesurée pendant ces diagnostics n'est pas un benchmark : certaines tâches CPU/compilation ont tourné simultanément.

GlotLID v3 identifie la langue à partir du texte reconnu. Il améliore les détections africaines par rapport au détecteur initial limité à 176 langues. Les variantes arabes sont ramenées à `ar` pour le routage. Il peut encore confondre du créole haïtien, de l'ourdou ou déclarer inconnue une courte phrase en mandarin. Une langue correctement identifiée ne prouve pas que les mots ou la traduction sont justes.

## Lecture vocale hors ligne

Génération locale, réseau bloqué, de fichiers audio non vides et finis en français, anglais, arabe, mandarin, créole haïtien, pendjabi, bengali et yoruba. Piper/Sherpa et MMS/Vits sont exercés sur CPU. Ce contrôle valide l'exécution et le signal produit ; il ne remplace pas une évaluation de prononciation par des locuteurs natifs. La banque contient 47 choix locaux, pas 47 langues toutes validées. Les voix système macOS/Linux n'ont pas été physiquement testées.

## Deux voix superposées

Deux mélanges contrôlés de six secondes, sources réelles connues, niveaux RMS égalisés. SepFormer produit deux canaux finis de 96 000 échantillons ; aucune durée audio n'est perdue. L'assignation des canaux maximise le SI-SDR par rapport aux sources connues.

| Mélange | Amélioration moyenne SI-SDR | Temps CPU observé |
|---|---:|---:|
| Anglais + français | +7,06 dB | 14,03 s pour 6 s d'audio |
| Arabe marocain + français | +0,71 dB | 14,48 s pour 6 s d'audio |

Le second mélange montre une faible amélioration, avec un canal légèrement dégradé. La séparation n'est donc pas présentée comme fiable dans toutes les langues. Elle est **expérimentale et désactivée par défaut**. Ces mesures de séparation ne sont pas une validation des mots reconnus ni des traductions produites.

## Paquet et installation

Les diagnostics du véritable exécutable Windows vérifient le backend déclaré, les sorties et les métadonnées, séparément des tests de code source. Le binaire final et les fichiers de modèles/catalogues sont contrôlés contre la source publiée avant installation. La validation de livraison conserve les rapports locaux et les sommes SHA-256.

L'installation par utilisateur conserve le même AppId et les emplacements de données. Réglages, historique SQLite et récupération sont sauvegardés immédiatement avant remplacement ; leurs contenus sont comparés après installation. Le paquet 3.0 de retour arrière reste disponible localement. Le téléchargement de mise à jour vérifie la taille et le SHA-256 des ressources de la release officielle ; aucune mise à jour silencieuse sans acceptation n'est déclenchée par l'application.

## Reproduire les diagnostics

```text
python -m pip install pyarrow
python scripts/prepare_language_tests.py
python scripts/evaluate_languages.py --model large-v3
python scripts/evaluate_languages.py --model omnilingual-1b-v2 --asr-only
python scripts/evaluate_overlap.py
```

`pyarrow` est un outil de préparation des échantillons, exclu du paquet. Les scripts gardent les fichiers de test sous `artifacts/dialect-tests`, ignoré par Git. Ils ne constituent pas une suite de certification linguistique et ne doivent pas entraîner la redistribution d'audio sous des licences restrictives.
