# Diagnostics multilingues 3.3 — 21 octobre 2026

280 extraits publics : huit pour chacun de 35 groupes, avec réseau bloqué pendant le chargement et l’inférence. Les groupes de Casablanca représentent des corpus arabes régionaux, sans identifier l’origine d’une personne. FLEURS contient surtout de la parole lue ; huit extraits CMU couvrent le créole haïtien. Les fichiers audio et les textes complets restent locaux. [Compteurs agrégés et empreintes des entrées](evaluations/3.3-language-diagnostics.json).

**Ce tableau mesure des erreurs de reconnaissance, pas la fiabilité du sens ou de la traduction.** Huit extraits sont insuffisants pour certifier une langue, un dialecte, le bruit, la parole spontanée ou tous les locuteurs. Les échantillons ne constituent pas une enquête représentative des personnes arrivant au Canada. Ils ne pilotent pas automatiquement le classement des modèles.

Omnilingual CTC 1B v2 : CPU, 280 extraits ; Qwen3-ASR 0.6B : CUDA float16, 168 extraits dans 21 groupes de sa couverture déclarée. Le choix automatique de l’application conserve sa politique prudente. Les essais Whisper CPU partiels restent séparés et ne sont pas mélangés dans ce tableau. Le comparatif Qwen 1.7B a été interrompu lorsque les ressources libres ne permettaient pas de charger exactement ce modèle ; aucun résultat 0.6B n’est publié sous le nom 1.7B. Les autres applications sont restées ouvertes. Les temps agrégés dans le JSON décrivent cette exécution, pas un classement de vitesse contrôlé.

**CER plus bas = moins d’erreurs.** Pondération par nombre de caractères de référence, après normalisation Unicode, casse, ponctuation, signes arabes et chiffres/lettres. Les insertions peuvent donner plus de 100 %. Le WER disponible dans le JSON dépend du découpage par espaces et convient mal à certaines écritures. Une sortie non vide et un code de langue correct ne prouvent pas une restitution correcte.

| Langue / groupe | Extraits | CER Omnilingual 1B v2 (%) ↓ | CER Qwen 0.6B (%) ↓ |
|---|---:|---:|---:|
| Créole haïtien | 8 | 25.6 | Hors couverture déclarée |
| Espagnol (Amérique latine) | 8 | 1.2 | 2.1 |
| Persan (Iran) | 8 | 3.6 | 13.3 |
| Pendjabi (Inde) | 8 | 8.0 | Hors couverture déclarée |
| Lingala (RDC) | 8 | 4.7 | Hors couverture déclarée |
| Yoruba (Nigeria) | 8 | 20.2 | Hors couverture déclarée |
| Somali | 8 | 10.9 | Hors couverture déclarée |
| Haoussa | 8 | 7.0 | Hors couverture déclarée |
| Igbo | 8 | 10.6 | Hors couverture déclarée |
| Amharique | 8 | 10.7 | Hors couverture déclarée |
| Swahili | 8 | 1.6 | Hors couverture déclarée |
| Turc | 8 | 3.6 | 5.2 |
| Gujarati | 8 | 4.6 | Hors couverture déclarée |
| Français | 8 | 6.8 | 7.7 |
| Anglais | 8 | 3.1 | 2.3 |
| Arabe — Algérie | 8 | 29.6 | 38.1 |
| Arabe — Égypte | 8 | 25.8 | 28.8 |
| Arabe — Jordanie | 8 | 18.5 | 23.7 |
| Arabe — Mauritanie | 8 | 41.7 | 46.1 |
| Arabe — Maroc | 8 | 39.9 | 46.6 |
| Arabe — Palestine | 8 | 14.7 | 23.3 |
| Arabe — Émirats arabes unis | 8 | 17.8 | 21.0 |
| Arabe — Yémen | 8 | 17.0 | 30.2 |
| Mandarin | 8 | 22.0 | 10.2 |
| Cantonais | 8 | 18.3 | 4.9 |
| Hindi | 8 | 3.3 | 18.5 |
| Ourdou | 8 | 43.8 | Hors couverture déclarée |
| Tamoul | 8 | 6.0 | Hors couverture déclarée |
| Bengali | 8 | 6.9 | Hors couverture déclarée |
| Pachto | 8 | 17.1 | Hors couverture déclarée |
| Thaï | 8 | 22.8 | 9.0 |
| Vietnamien | 8 | 10.3 | 5.2 |
| Indonésien | 8 | 1.4 | 2.8 |
| Japonais | 8 | 19.2 | 8.9 |
| Coréen | 8 | 6.1 | 3.2 |

La tentative supplémentaire de Whisper en CUDA int8_float16 a été refusée par le contrôle de VRAM réellement libre. Les autres applications sont restées ouvertes. Les mesures CPU partielles ne remplacent pas un comparatif équilibré et ne sont pas publiées comme un essai complet. Le [comparatif historique sur 70 extraits](VALIDATION_3.1.md) reste disponible. Whisper large-v3 CPU passe par ailleurs le test fonctionnel complet de conversation 3.3.

Le compteur d’accord des langues dans le JSON utilise les alias de routage de traduction : cantonais et mandarin y partagent `zh`. Il ne certifie pas une identification de dialecte.

## Reproduction

```text
python scripts/prepare_language_tests.py --samples 8 --folder LOCAL_AUDIO_FOLDER
python scripts/evaluate_languages.py --model omnilingual-1b-v2 --asr-only --folder LOCAL_AUDIO_FOLDER --report-folder artifacts/validation-3.3/languages
python scripts/evaluate_languages.py --model qwen3-asr-0.6b --asr-only --folder LOCAL_AUDIO_FOLDER --report-folder artifacts/validation-3.3/languages
python scripts/summarize_language_tests.py --manifest LOCAL_AUDIO_FOLDER/manifest.json
```

Les empreintes publiées permettent de vérifier les entrées exactes. La préparation sélectionne les premières lignes admissibles du test officiel (3 à 14 secondes), sans adaptation sur ces références. Les corpus peuvent évoluer : comparer les empreintes avant de revendiquer une reproduction exacte. Les jeux de données eux-mêmes ne sont pas tous épinglés à une révision immuable. Les modèles et leurs charges locales sont épinglés dans le code et les catalogues. [Sources et licences](MODELS_AND_LICENSES.md), [validation globale](VALIDATION_3.3.md).
