# Couverture et priorités linguistiques — 3.1.0

## Priorités pour les échanges au Canada

Les priorités de développement répondent aux besoins d'échanges multilingues au Canada. Elles ne constituent pas un classement officiel des langues parlées par les demandeurs d'asile, et l'application n'attribue jamais une langue à une personne d'après son origine.

Les données publiques récentes de la CISR portent sur le **pays présenté comme pays de persécution**, pas sur la langue. Au premier semestre 2026, elles comptent notamment 4 322 demandes déférées pour l'Inde, 2 262 pour Haïti et 1 921 pour l'Iran. L'inventaire de fin 2025 met aussi en évidence le Mexique, le Nigeria et le Bangladesh. Un même pays peut correspondre à plusieurs langues. Sources : [CISR janvier–juin 2026](https://www.irb-cisr.gc.ca/fr/statistiques/asile/Pages/SPRStat2026.aspx), [CISR, comparution du 9 mars 2026](https://www.irb-cisr.gc.ca/en/transparency/proactive-disclosure/Pages/cimm-mar-2026.aspx).

Une source CISR donne directement une ancienne liste de langues d'interprétation : espagnol, arabe, créole haïtien, mandarin, pendjabi, lingala, farsi, yoruba, ourdou et somali. Il s'agit de la note 49 d'une revue terminée en 2019 et publiée en 2020, **pas d'un classement 2026**. [Source historique](https://irb-cisr.gc.ca/en/transparency/reviews-audit-evaluations/Pages/sogie-guideline-implementation-review.aspx).

Le premier ensemble de travail combine donc le créole haïtien ; le pendjabi, l'hindi et le gujarati ; le persan/farsi ; l'espagnol ; l'arabe et ses variétés ; le mandarin ; le bengali, l'ourdou et le tamoul ; le lingala, le yoruba, le somali, le haoussa et l'igbo. Le tigrigna, l'amharique, le pachto, le swahili et le turc complètent cet accès rapide. Le français et l'anglais sont placés en tête pour la langue de destination. Cet ordre est un choix pratique de développement fondé sur ces indices, pas une mesure statistique de fréquence linguistique.

## Trois couvertures différentes

| Fonction | Moteur local | Couverture exposée |
|---|---|---|
| Reconnaissance étendue | Meta Omnilingual CTC 1B v2 | Plus de 1 600 langues annoncées ; précision variable |
| Identification de la langue du texte reconnu | GlotLID v3 | Plus de 2 000 étiquettes langue/écriture ; ni certitude acoustique ni garantie sur les phrases courtes |
| Reconnaissance alternative | Whisper large-v3 | 100 identifiants de langue ; toutes les anciennes tailles conservées |
| Reconnaissance générale | Qwen3-ASR | 30 langues annoncées ; profil général de précision GPU |
| Reconnaissance rapide | Parakeet TDT v3 | 25 langues européennes |
| Traduction | MADLAD-400 3B int8 | 452 jetons de langue/variantes dans le catalogue local |
| Lecture vocale | Piper, MMS, voix système | 47 voix locales proposées, dont français/anglais inclus sous Windows ; autres voix selon disponibilité |

La présence d'un jeton de traduction n'implique pas une reconnaissance ou une voix disponible pour cette langue. Les nombres de langues, variantes et étiquettes d'écriture ne s'additionnent pas. Une langue peut être transcrite correctement et identifiée incorrectement ; une traduction peut paraître fluide et changer le sens. Les indices affichés sont non calibrés.

Le profil universel automatique privilégie Omnilingual quand le moteur CPU, les 16 Go de RAM totale, les 10 Go disponibles et l'espace de préparation requis sont présents. Il se replie vers le meilleur Whisper multilingue compatible. Le profil général continue de privilégier Qwen 1.7B sur un GPU compatible ; le profil rapidité privilégie Parakeet. Le choix manuel reste accessible.

## Ce qui a réellement été essayé

L'échantillon diagnostique comprend 70 extraits publics de test, deux par groupe : créole haïtien ; 26 configurations FLEURS ; huit groupes Casablanca (Algérie, Égypte, Jordanie, Mauritanie, Maroc, Palestine, Émirats arabes unis, Yémen). Il couvre les langues prioritaires disponibles dans ces corpus ainsi que le cantonais, le thaï, le vietnamien, l'indonésien, le japonais et le coréen.

Ces extraits sont trop peu nombreux pour certifier un dialecte ou établir un classement général. FLEURS est principalement de la lecture ; il ne représente pas à lui seul une conversation spontanée, un niveau de littératie ou une salle bruyante. Le test ne permet pas de garantir les variantes régionales, le changement de langue dans une même phrase, ou toutes les directions de traduction. Les détails chiffrés et cas faibles sont publiés dans [VALIDATION_3.1.md](VALIDATION_3.1.md).

Les tests ont notamment motivé l'ajout d'Omnilingual et le remplacement d'un détecteur limité à 176 langues par GlotLID. Le modèle étendu améliore plusieurs langues sud-asiatiques et africaines sur cet échantillon ; Whisper reste utile pour le créole haïtien, plusieurs langues asiatiques et certaines variétés arabes. Les langues non essayées restent disponibles sans être déclarées validées.

## Quand l'échange est difficile

Fixez manuellement la paire si la détection se trompe. Choisissez un autre modèle vocal si l'original est mauvais. Faites des phrases courtes et une pause entre les interlocuteurs ; réécoutez les passages importants. La lecture vocale et la troisième langue peuvent aider à vérifier un échange, sans constituer une preuve que la traduction est correcte. La séparation de deux voix est expérimentale et désactivée par défaut.

Les variétés arabes ne sont pas forcées dans huit modèles séparés : les modèles de reconnaissance partagent leur représentation multilingue. Les labels de pays du corpus de test ne deviennent pas une déduction automatique de l'origine d'un utilisateur.

## Références des moteurs

[Meta Omnilingual](https://github.com/facebookresearch/omnilingual-asr), [export Sherpa CTC](https://k2-fsa.github.io/sherpa/onnx/omnilingual-asr/models.html), [GlotLID v3](https://huggingface.co/cis-lmu/glotlid), [OpenAI Whisper](https://github.com/openai/whisper), [MADLAD-400](https://huggingface.co/google/madlad400-3b-mt). Les révisions et sommes de contrôle utilisées sont enregistrées dans le code et les catalogues locaux.
