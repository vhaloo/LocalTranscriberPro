"""Generate the complete README language inventory from pinned, offline data."""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import __version__  # noqa: E402
from src.models import MODEL_BY_ID  # noqa: E402

START = "<!-- BEGIN GENERATED LANGUAGE INVENTORY -->"
END = "<!-- END GENERATED LANGUAGE INVENTORY -->"


def load(name):
    return json.loads((ROOT / name).read_text("utf-8"))


def cell(value):
    return str(value).replace("|", "&#124;").replace("\n", " ")


def alphabetical(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(c))


def unique(rows):
    codes = [row["code"] for row in rows]
    if len(codes) != len(set(codes)):
        raise ValueError("Duplicate language codes in documentation input")


def generate():
    catalogue = load("src/data/translation_languages.json")
    omnilingual = load("docs/data/omnilingual_languages.json")
    diagnostics = load("docs/data/language_diagnostics.json")
    runtime_omni = load("src/data/omnilingual.json")
    for key in ("repository", "revision"):
        if omnilingual["export"][key] != runtime_omni[key]:
            raise ValueError("Omnilingual model changed: refresh the publisher's language inventory")
    unique(omnilingual["languages"])
    unique(catalogue["languages"])
    by_code = {row["code"]: row for row in catalogue["languages"]}
    aliases = {"jw": "jv", "tl": "fil"}
    whisper = omnilingual["whisper_codes"]
    if len(set(whisper)) != len(whisper):
        raise ValueError("Duplicate Whisper language codes")
    normalized = {"jw": "jv", "tl": "fil", "yue": "zh"}
    if {normalized.get(code, code) for code in whisper} != set(catalogue["asr_languages"]):
        raise ValueError("Whisper language inventory and application catalogue differ")
    qwen = set(MODEL_BY_ID["qwen3-asr-1.7b"].languages)
    if qwen != set(MODEL_BY_ID["qwen3-asr-0.6b"].languages):
        raise ValueError("Qwen models now have different language coverage")
    parakeet = set(MODEL_BY_ID["parakeet-tdt-0.6b-v3"].languages)
    if not qwen.union(parakeet) <= {aliases.get(code, code) for code in whisper}:
        raise ValueError("Add newly supported recognition languages to the README table")
    piper = load("src/data/voices.json")["voices"]
    mms = load("src/data/mms_voices.json")
    if piper.keys() & mms.keys():
        raise ValueError("Voice catalogues overlap; document the multiple choices explicitly")
    voices = {**piper, **mms}

    def name(code):
        overrides = {"yue": "Cantonais", "zh": "Chinois (mandarin)", "tl": "Tagalog"}
        return overrides.get(code) or by_code[aliases.get(code, code)]["fr"]

    language_count = len({row["code"].split("_")[0] for row in omnilingual["languages"]})
    lines = [START, '<a id="langues"></a>', "## Liste complète des langues et fiabilité", "",
             f"**Complete language inventory / Inventaire intégral — version {__version__}, sources vérifiées le {omnilingual['checked_on']}.** "
             "Toutes les listes figurent ci-dessous dans ce README. Dépliez les tableaux pour parcourir les langues ; "
             "les codes permettent de distinguer les variantes et écritures.", "",
             "[Mesures disponibles](#mesures-langues) · [Omnilingual](#langues-omnilingual) · "
             "[Whisper / Qwen / Parakeet](#langues-autres-asr) · [Traduction](#langues-traduction) · "
             "[Voix](#langues-voix)", "",
             "**Un pourcentage de fiabilité par langue n'est pas disponible.** « Non mesurée » signifie qu'aucune "
             "probabilité validée de restitution correcte du sens n'a été établie pour cette entrée. Cela ne signifie "
             "ni 0 %, ni 100 %. Les pourcentages réellement mesurés ci-dessous sont des **taux d'erreur en caractères "
             "(CER)** sur de petits échantillons de reconnaissance, pas une garantie de compréhension ou de traduction. "
             "Les notes relatives de l'application et ses indices de confiance ne sont pas des taux de fiabilité.", "",
             "| Fonction | Inventaire complet | Fiabilité sémantique (%) |",
             "|---|---:|---|",
             f"| Reconnaissance Omnilingual CTC 1B v2 | {language_count:,} codes de langue ; "
             f"{len(omnilingual['languages']):,} entrées langue/écriture/variété | Non mesurée par langue |".replace(",", " "),
             f"| Whisper large-v3 / Turbo | {len(whisper)} identifiants ; autres Whisper multilingues : 99 | Non mesurée par langue |",
             f"| Qwen3-ASR 1.7B et 0.6B | {len(qwen)} langues et 22 variétés chinoises annoncées | Non mesurée par langue/variété |",
             f"| Parakeet TDT v3 | {len(parakeet)} langues | Non mesurée par langue |",
             f"| Traduction MADLAD | {len(by_code)} jetons langue/écriture/région | Non mesurée par direction |",
             f"| Lecture vocale locale | {len(voices)} choix, {len(piper)} Piper + {len(mms)} MMS | Prononciation non mesurée |", "",
             "Ces couvertures **ne s'additionnent pas**. Une langue reconnue par Omnilingual peut ne pas avoir de "
             "traduction, de détection automatique exploitable ou de voix dans l'application. Les 2 000+ étiquettes "
             "du détecteur textuel GlotLID ne sont pas une liste supplémentaire de langues transcrites. Le matériel, "
             "le modèle préparé et les langues disponibles à chaque étape limitent le parcours complet.", "",
             '<a id="mesures-langues"></a>', "### Pourcentages mesurés : reconnaissance, 35 groupes", "",
             "**Deux extraits par groupe, 70 extraits au total**, identiques pour les deux moteurs ; Whisper large-v3 "
             "sur CUDA et Omnilingual CTC 1B v2 sur CPU, réseau bloqué pendant l'inférence. FLEURS correspond "
             "principalement à de la parole lue ; Casablanca fournit huit groupes arabes, et CMU deux extraits haïtiens. "
             "Les pays ci-dessous décrivent les corpus, pas l'origine déduite d'une personne.", "",
             "**CER plus bas = moins d'erreurs.** Il compte insertions, suppressions et substitutions après "
             "normalisation, divisées par les caractères de référence, avec pondération par longueur. Il peut dépasser "
             "100 %. Même 0 % sur deux extraits ne donne pas une fiabilité générale de 100 %. Ces résultats ne "
             "valident pas tous les accents, locuteurs, niveaux de bruit ou conversations spontanées. "
             "[Méthode, sources, limites et reproduction](docs/VALIDATION_3.1.md).", "",
             "| Langue / groupe de corpus | Extraits | CER Whisper large-v3 (%) ↓ | CER Omnilingual 1B v2 (%) ↓ | Fiabilité du sens (%) |",
             "|---|---:|---:|---:|---|" ]
    for row in diagnostics["groups"]:
        scores = []
        for model in ("whisper_large_v3", "omnilingual_ctc_1b_v2"):
            measured = row[model]
            if measured["samples"] != 2 or measured["reference_characters"] <= 0:
                raise ValueError("Diagnostic methodology changed: update the README explanation")
            scores.append(f"{100 * measured['character_edits'] / measured['reference_characters']:.1f}")
        lines.append(f"| {cell(row['label_fr'])} | 2 | {scores[0]} | {scores[1]} | Non mesurée |")
    lines += ["", "La traduction MADLAD a produit des sorties françaises pendant ces essais, mais sans références "
              "bilingues ni notation humaine du sens : **aucun pourcentage de fiabilité de traduction n'en est tiré**. "
              "Les scores publiés par Meta pour son modèle **7B LLM** ne sont pas attribués au **1B CTC v2** intégré ici.", "",
              '<a id="langues-omnilingual"></a>',
              f"### Reconnaissance étendue : {len(omnilingual['languages']):,} entrées Omnilingual".replace(",", " "), "",
              f"Liste de couverture de l'éditeur : [Meta, `supported_langs`, révision `{omnilingual['revision'][:12]}`]"
              f"({omnilingual['url']}). Les noms viennent des données ISO de "
              "[pycountry](https://github.com/pycountry/pycountry), traduits en français lorsqu'un nom est disponible ; "
              "les autres conservent leur nom anglais. Chaque code officiel `{langue}_{écriture}` reste visible ; "
              "quatre entrées ont aussi un suffixe de variété (`cypr1249`, `gherd`, `valbadia`, `surs1244`). "
              "Il s'agit de couverture annoncée du modèle, pas de 1 672 langues testées dans cette application.", "",
              "Écritures fréquentes : `Latn` latin, `Arab` arabe, `Cyrl` cyrillique, `Deva` devanagari, `Ethi` éthiopien, "
              "`Beng` bengali, `Guru` gurmukhi, `Gujr` gujarati, `Taml` tamoul, `Hans` chinois simplifié, "
              "`Hant` chinois traditionnel, `Jpan` japonais, `Hang` hangul. Plusieurs écritures d'une même langue "
              "constituent des lignes distinctes, sans garantir une conversion d'écriture. "
              "[Essais chiffrés disponibles](#mesures-langues).", "",
              f"<details>\n<summary>Afficher les {len(omnilingual['languages']):,} entrées langue/écriture/variété</summary>".replace(",", " "), "",
              "| Langue | Code officiel langue/écriture/variété | Fiabilité (%) |", "|---|---|---|"]
    for row in sorted(omnilingual["languages"], key=lambda r: (alphabetical(r["name_fr"]), r["code"])):
        label = row["name_fr"]
        if row["name_en"] != label:
            label += " / " + row["name_en"]
        lines.append(f"| {cell(label)} | `{row['code']}` | Non mesurée |")
    lines += ["", "</details>", "", '<a id="langues-autres-asr"></a>',
              "### Whisper, Qwen et Parakeet : toutes les langues", "",
              "Les colonnes décrivent la couverture des modèles, pas une équivalence de précision. « Oui » pour Qwen "
              "vaut pour les deux tailles ; le cantonais est propre aux Whisper large-v3 et Turbo, tandis que les "
              "Whisper `.en` restent anglais uniquement. Les autres Whisper multilingues couvrent les 99 autres "
              "identifiants. L'application normalise `jw` vers `jv`, `tl` vers `fil` et le routage de `yue` vers `zh` ; "
              "ce dernier alias ne fournit pas une voix cantonaise distincte. "
              "[OpenAI Whisper](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py), "
              "[Qwen3-ASR](https://huggingface.co/Qwen/Qwen3-ASR-1.7B), "
              "[NVIDIA Parakeet v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3).", "",
              "<details>\n<summary>Afficher les 100 identifiants Whisper, les 30 langues Qwen et les 25 langues Parakeet</summary>", "",
              "| Langue | Code moteur | Whisper multilingue | Qwen 1.7B / 0.6B | Parakeet v3 | Fiabilité (%) |",
              "|---|---|---|---|---|---|"]
    for code in sorted(whisper, key=lambda code: alphabetical(name(code))):
        normalized_code = aliases.get(code, code)
        lines.append(f"| {cell(name(code))} | `{code}` | {'v3 / Turbo' if code == 'yue' else 'Oui'} | "
                     f"{'Oui' if normalized_code in qwen else '—'} | "
                     f"{'Oui' if normalized_code in parakeet else '—'} | Non mesurée |")
    lines += ["", "</details>", "",
              "**Variétés chinoises supplémentaires annoncées par Qwen** (graphies de l'éditeur, sans sélecteur "
              "de dialecte dédié dans l'application) : Anhui, Dongbei, Fujian, Gansu, Guizhou, Hebei, Henan, Hubei, "
              "Hunan, Jiangxi, Ningxia, Shandong, Shaanxi, Shanxi, Sichuan, Tianjin, Yunnan, Zhejiang, cantonais "
              "(accent de Hong Kong), cantonais (accent du Guangdong), wu et minnan. **Fiabilité : non mesurée pour "
              "chacune de ces 22 variétés** ; cette annonce ne constitue pas une validation locale de tous les dialectes.", "",
              '<a id="langues-traduction"></a>', f"### Traduction : les {len(by_code)} jetons MADLAD disponibles", "",
              "Liste exacte du catalogue de l'application, tirée du vocabulaire de l'" 
              f"[export CTranslate2 épinglé](https://huggingface.co/{catalogue['repository']}/tree/{catalogue['revision']}) "
              "du [modèle Google MADLAD-400 3B](https://huggingface.co/google/madlad400-3b-mt). "
              "Les variantes de script ou de région restent distinctes ; ce nombre n'est pas un décompte de langues "
              "toutes validées. La présence d'un jeton ne prouve pas la justesse d'une direction de traduction. "
              "Le résultat dépend à la fois de la langue source, de la destination, du texte et de la transcription. "
              "La fiabilité du sens n'a été mesurée pour **aucune** de ces directions.", "",
              f"<details>\n<summary>Afficher les {len(by_code)} langues/variantes de traduction</summary>", "",
              "| Langue / variante du catalogue | Code | Fiabilité de traduction (%) |", "|---|---|---|"]
    for row in sorted(by_code.values(), key=lambda r: (alphabetical(r["fr"]), r["code"])):
        lines.append(f"| {cell(row['fr'])} | `{row['code']}` | Non mesurée |")
    lines += ["", "</details>", "", '<a id="langues-voix"></a>',
              f"### Lecture vocale : les {len(voices)} choix de la banque locale", "",
              "Français et anglais sont inclus dans les paquets de bureau. Les autres voix se téléchargent au besoin "
              "après acceptation, puis fonctionnent hors ligne. « Signal testé » signifie qu'une synthèse hors ligne "
              "a produit un fichier audio valide ; la prononciation et le sens perçu n'ont pas été notés par des "
              "locuteurs natifs. Les variantes régionales de la voix sont visibles dans son identifiant. Les voix "
              "système supplémentaires dépendent de ce qui est effectivement installé sur Windows/macOS/Linux "
              "et ne sont pas promises pour toutes les langues. "
              "[Catalogue Piper](src/data/voices.json), [catalogue MMS](src/data/mms_voices.json), "
              "[licences par modèle](docs/MODELS_AND_LICENSES.md).", "",
              "| Langue | Code | Moteur / voix | Fourniture | Signal hors ligne testé | Fiabilité de prononciation (%) |",
              "|---|---|---|---|---|---|"]
    tested_voices = {"fr", "en", "ar", "zh", "ht", "pa", "bn", "yo"}
    for code in sorted(voices, key=lambda code: alphabetical(name(code))):
        voice = voices[code]
        engine = "Piper" if code in piper else "MMS · CC BY-NC 4.0"
        identifier = voice.get("model", voice["repository"].rsplit("/", 1)[-1])
        lines.append(f"| {cell(name(code))} | `{code}` | {engine} / `{cell(identifier)}` | "
                     f"{'Incluse' if code in {'fr', 'en'} else 'À télécharger'} | "
                     f"{'Oui' if code in tested_voices else 'Non'} | Non mesurée |")
    lines += ["", "Les tableaux sont générés depuis les catalogues de la version et les "
              "[instantanés documentaires sourcés](docs/data/README.md). "
              "`python scripts/generate_language_readme.py` les régénère ; `--check` bloque les changements de catalogue "
              "qui laisseraient ce README périmé. Les mesures restent attachées au modèle et au corpus testés.", END]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the README inventory is stale")
    args = parser.parse_args()
    path = ROOT / "README.md"
    readme = path.read_text("utf-8")
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise SystemExit("README must contain one language inventory marker pair")
    start, end = readme.index(START), readme.index(END) + len(END)
    expected = generate().rstrip("\n")
    if readme[start:end] == expected:
        print("README language inventory is current.")
    elif args.check:
        raise SystemExit("README language inventory is stale: run scripts/generate_language_readme.py")
    else:
        path.write_text(readme[:start] + expected + readme[end:], encoding="utf-8", newline="\n")
        print("Updated the complete README language inventory.")


if __name__ == "__main__":
    main()
