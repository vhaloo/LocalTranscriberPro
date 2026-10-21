"""Publish aggregate diagnostics, never test audio or reference/hypothesis text."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.translation_languages import normalize_language  # noqa: E402

MODELS = ("large-v3", "omnilingual-1b-v2", "qwen3-asr-0.6b")
LOGS = {"large-v3": "evaluate-whisper-gpu-int8.log", "omnilingual-1b-v2": "evaluate-omni-sequential.log",
        "qwen3-asr-0.6b": "evaluate-qwen06.log"}
REPORTS = {model: f"results-{model}.json" for model in MODELS}
REPORTS["large-v3"] = "results-large-v3-cuda-int8_float16.json"
NAMES = {"default": "Créole haïtien", "es_419": "Espagnol (Amérique latine)", "fa_ir": "Persan (Iran)",
    "pa_in": "Pendjabi (Inde)", "ln_cd": "Lingala (RDC)", "yo_ng": "Yoruba (Nigeria)", "so_so": "Somali",
    "ha_ng": "Haoussa", "ig_ng": "Igbo", "am_et": "Amharique", "sw_ke": "Swahili", "tr_tr": "Turc",
    "gu_in": "Gujarati", "fr_fr": "Français", "en_us": "Anglais", "Algeria": "Arabe — Algérie",
    "Egypt": "Arabe — Égypte", "Jordan": "Arabe — Jordanie", "Mauritania": "Arabe — Mauritanie",
    "Morocco": "Arabe — Maroc", "Palestine": "Arabe — Palestine", "UAE": "Arabe — Émirats arabes unis",
    "Yemen": "Arabe — Yémen", "cmn_hans_cn": "Mandarin", "yue_hant_hk": "Cantonais", "hi_in": "Hindi",
    "ur_pk": "Ourdou", "ta_in": "Tamoul", "bn_in": "Bengali", "ps_af": "Pachto", "th_th": "Thaï",
    "vi_vn": "Vietnamien", "id_id": "Indonésien", "ja_jp": "Japonais", "ko_kr": "Coréen"}


def metrics(rows):
    return {"clips": len(rows), "audio_seconds": round(sum(row["duration"] for row in rows), 3),
        "character_edits": sum(row["character_edits"] for row in rows),
        "reference_characters": sum(row["reference_characters"] for row in rows),
        "word_edits": sum(row["word_edits"] for row in rows),
        "reference_words": sum(row["reference_words"] for row in rows),
        "processing_seconds": round(sum(row["processing_seconds"] for row in rows), 3),
        "language_matches": sum((normalize_language(row["detected_language"]) == "zh")
                                if row["config"] == "yue_hant_hk" else row["language_match"] for row in rows)}


def percentage(row, unit):
    return 100 * row[unit + "_edits"] / max(1, row["reference_" + ("characters" if unit == "character" else "words")])


def summarize(folder, manifest_path, output):
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    assert len(manifest) == 280
    groups = list(dict.fromkeys(row["config"] for row in manifest))
    assert len(groups) == 35 and all(sum(row["config"] == code for row in manifest) == 8 for code in groups)
    optional_report = folder / REPORTS["large-v3"]
    optional_log = folder.parent / LOGS["large-v3"]
    include_whisper = (optional_report.is_file() and optional_log.is_file()
        and len(json.loads(optional_report.read_text("utf-8"))) == len(manifest)
        and "Completed 280 clips, with network connections blocked." in optional_log.read_text("utf-8"))
    models = MODELS if include_whisper else MODELS[1:]
    summary = {"version": "3.3.0", "date": "2026-10-21", "clips_in_manifest": len(manifest),
        "manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
        "method": "Eight held-out clips per group; normalized character/whitespace-word edit distance. Not semantic reliability.",
        "network_blocked": True, "timing_limit": "Wall time excluding initial model loading; mixed CPU/GPU and ordinary desktop activity. Not a controlled speed ranking.",
        "models": {}, "not_included": [] if include_whisper else [
            "Expanded Whisper CPU diagnostics were partial and are excluded; the optional CUDA int8_float16 attempt was refused for insufficient actual free VRAM. Historical complete 70-clip Whisper diagnostics remain separately published."],
        "language_match_limit": "Normalized translation-route IDs; Cantonese/Mandarin share zh. This count does not validate dialect identification.",
        "groups": [{"code": code, "label": NAMES[code]} for code in groups],
        "inputs": [{key: row.get(key) for key in ("dataset", "config", "split", "row", "sha256", "duration")} for row in manifest]}
    for model in models:
        rows = json.loads((folder / REPORTS[model]).read_text("utf-8"))
        assert len(rows) == len(manifest), f"Incomplete diagnostics for {model}"
        log = (folder.parent / LOGS[model]).read_text("utf-8")
        assert "Completed 280 clips, with network connections blocked." in log
        loaded = next(line for line in log.splitlines() if line.startswith("Models loaded:"))
        assert f"model_id='{model}'" in loaded and "fallback_reason=''" in loaded
        by_group = defaultdict(list)
        for row in rows:
            if "skipped" not in row:
                by_group[row["config"]].append(row)
        scored = [row for row in rows if "skipped" not in row]
        summary["models"][model] = {"loaded_status": loaded.removeprefix("Models loaded: "),
            "scored": len(scored), "skipped_outside_coverage": len(rows) - len(scored),
            "aggregate": metrics(scored), "by_group": {code: metrics(values) for code, values in by_group.items()}}
        assert all(len(values) == 8 for values in by_group.values())
    output.mkdir(parents=True, exist_ok=True)
    (output / "3.3-language-diagnostics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")
    lines = ["# Diagnostics multilingues 3.3 — 21 octobre 2026", "",
        "280 extraits publics : huit pour chacun de 35 groupes, avec réseau bloqué pendant le chargement et l’inférence. "
        "Les groupes de Casablanca représentent des corpus arabes régionaux, sans identifier l’origine d’une personne. "
        "FLEURS contient surtout de la parole lue ; huit extraits CMU couvrent le créole haïtien. "
        "Les fichiers audio et les textes complets restent locaux. "
        "[Compteurs agrégés et empreintes des entrées](evaluations/3.3-language-diagnostics.json).", "",
        "**Ce tableau mesure des erreurs de reconnaissance, pas la fiabilité du sens ou de la traduction.** "
        "Huit extraits sont insuffisants pour certifier une langue, un dialecte, le bruit, la parole spontanée ou tous les locuteurs. "
        "Les échantillons ne constituent pas une enquête représentative des personnes arrivant au Canada. "
        "Ils ne pilotent pas automatiquement le classement des modèles.", "",
        ("Whisper large-v3 : CUDA int8_float16, configuration diagnostique explicite ; " if include_whisper else "")
        + "Omnilingual CTC 1B v2 : CPU, 280 extraits ; Qwen3-ASR 0.6B : CUDA float16, 168 extraits dans 21 groupes de sa couverture déclarée. "
        "Le choix automatique de l’application conserve sa politique prudente. Les essais Whisper CPU partiels restent séparés et ne sont pas mélangés dans ce tableau. "
        "Le comparatif Qwen 1.7B a été interrompu lorsque les ressources libres ne permettaient pas de charger exactement ce modèle ; "
        "aucun résultat 0.6B n’est publié sous le nom 1.7B. Les autres applications sont restées ouvertes. "
        "Les temps agrégés dans le JSON décrivent cette exécution, pas un classement de vitesse contrôlé.", "",
        "**CER plus bas = moins d’erreurs.** Pondération par nombre de caractères de référence, après normalisation Unicode, "
        "casse, ponctuation, signes arabes et chiffres/lettres. Les insertions peuvent donner plus de 100 %. "
        "Le WER disponible dans le JSON dépend du découpage par espaces et convient mal à certaines écritures. "
        "Une sortie non vide et un code de langue correct ne prouvent pas une restitution correcte.", "",
        "| Langue / groupe | Extraits | " + " | ".join({"large-v3": "CER Whisper large-v3 GPU int8 (%) ↓",
            "omnilingual-1b-v2": "CER Omnilingual 1B v2 (%) ↓", "qwen3-asr-0.6b": "CER Qwen 0.6B (%) ↓"}[model] for model in models) + " |",
        "|---|---:|" + "---:|" * len(models)]
    for code in groups:
        values = []
        for model in models:
            row = summary["models"][model]["by_group"].get(code)
            values.append(f"{percentage(row, 'character'):.1f}" if row else "Hors couverture déclarée")
        lines.append(f"| {NAMES[code]} | 8 | " + " | ".join(values) + " |")
    if not include_whisper:
        lines.extend(["", "La tentative supplémentaire de Whisper en CUDA int8_float16 a été refusée par le contrôle de VRAM réellement libre. "
            "Les autres applications sont restées ouvertes. Les mesures CPU partielles ne remplacent pas un comparatif équilibré et ne sont pas publiées "
            "comme un essai complet. Le [comparatif historique sur 70 extraits](VALIDATION_3.1.md) reste disponible. "
            "Whisper large-v3 CPU passe par ailleurs le test fonctionnel complet de conversation 3.3."])
    lines.extend(["", "Le compteur d’accord des langues dans le JSON utilise les alias de routage de traduction : cantonais et mandarin "
        "y partagent `zh`. Il ne certifie pas une identification de dialecte.", "", "## Reproduction", "", "```text",
        "python scripts/prepare_language_tests.py --samples 8 --folder LOCAL_AUDIO_FOLDER",
        *[f"python scripts/evaluate_languages.py --model {model} --asr-only "
          + ("--device cuda --compute-type int8_float16 " if model == "large-v3" else "")
          + "--folder LOCAL_AUDIO_FOLDER --report-folder artifacts/validation-3.3/languages" for model in models],
        "python scripts/summarize_language_tests.py --manifest LOCAL_AUDIO_FOLDER/manifest.json", "```", "",
        "Les empreintes publiées permettent de vérifier les entrées exactes. La préparation sélectionne les premières lignes admissibles "
        "du test officiel (3 à 14 secondes), sans adaptation sur ces références. Les corpus peuvent évoluer : comparer les empreintes avant "
        "de revendiquer une reproduction exacte. Les jeux de données eux-mêmes ne sont pas tous épinglés à une révision immuable. "
        "Les modèles et leurs charges locales sont épinglés dans le code et les catalogues. "
        "[Sources et licences](MODELS_AND_LICENSES.md), [validation globale](VALIDATION_3.3.md).", ""])
    (output.parent / "LANGUAGE_DIAGNOSTICS_3.3.md").write_text("\n".join(lines), "utf-8")
    return {model: {key: value for key, value in data.items() if key in {"scored", "skipped_outside_coverage"}}
            for model, data in summary["models"].items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--folder", type=Path, default=ROOT / "artifacts/validation-3.3/languages")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evaluations")
    args = parser.parse_args()
    print(json.dumps(summarize(args.folder, args.manifest, args.output), indent=2))
