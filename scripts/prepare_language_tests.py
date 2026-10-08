"""Download a deterministic, small held-out sample for local ASR diagnostics.

Audio and reference text stay under ignored artifacts. Casablanca CC BY-NC-ND
samples are used for evaluation only and are not redistributed with the app.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import io
import json
from pathlib import Path

import requests
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1] / "artifacts/dialect-tests"
ROOT.mkdir(parents=True, exist_ok=True)
ASIAN = ["cmn_hans_cn", "yue_hant_hk", "hi_in", "ur_pk", "ta_in", "bn_in", "ps_af",
         "th_th", "vi_vn", "id_id", "ja_jp", "ko_kr"]
PRIORITY = ["es_419", "fa_ir", "pa_in", "ln_cd", "yo_ng", "so_so", "ha_ng", "ig_ng", "am_et", "sw_ke", "tr_tr", "gu_in", "fr_fr", "en_us"]
ARABIC = ["Algeria", "Egypt", "Jordan", "Mauritania", "Morocco", "Palestine", "UAE", "Yemen"]


def get_json(endpoint, **params):
    response = requests.get("https://datasets-server.huggingface.co/" + endpoint, params=params, timeout=90)
    response.raise_for_status()
    return response.json()


def fetch(entry):
    dataset, config = entry
    target = ROOT / (dataset.split("/")[-1] + "-" + config + ".json")
    if target.is_file():
        return json.loads(target.read_text(encoding="utf-8"))
    try:
        data = get_json("first-rows", dataset=dataset, config=config, split="test")
    except requests.HTTPError:
        data = {}
    rows = data.get("rows", [])
    if not rows and dataset == "google/fleurs":
        # Some official test shards exceed the viewer's 300 MB scan limit.
        # Download that test shard and read its first row group locally.
        import pyarrow.parquet as pq

        shards = get_json("parquet", dataset=dataset)["parquet_files"]
        shard = next(item for item in shards if item["config"] == config and item["split"] == "test")
        response = requests.get(shard["url"], timeout=180)
        response.raise_for_status()
        table = pq.ParquetFile(io.BytesIO(response.content)).read_row_group(0).slice(0, 100)
        rows = [{"row_idx": index, "row": item} for index, item in enumerate(table.to_pylist())]
    selected = []
    for entry in rows:
        row = entry["row"]
        raw_audio = row.get("audio")
        if isinstance(raw_audio, list):
            response = requests.get(raw_audio[0]["src"], timeout=60)
            response.raise_for_status()
            audio_bytes = response.content
        else:
            audio_bytes = raw_audio["bytes"]
        samples, rate = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        duration = len(samples) / rate
        if not 3 <= duration <= 14:
            continue
        name = f"{dataset.split('/')[-1]}-{config}-{entry['row_idx']}.wav"
        (ROOT / name).write_bytes(audio_bytes)
        selected.append({"dataset": dataset, "config": config, "split": "test", "row": entry["row_idx"],
                         "file": name, "sha256": hashlib.sha256(audio_bytes).hexdigest(), "duration": duration,
                         "reference": row.get("transcription", row.get("raw_transcription", ""))})
        if len(selected) == 2:
            break
    if len(selected) != 2:
        raise RuntimeError("Insufficient held-out clips: " + config)
    target.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
    print(config, "downloaded", flush=True)
    return selected


if __name__ == "__main__":
    entries = ([("phatjmo/cmu_haitian", "default")]
               + [("google/fleurs", config) for config in PRIORITY]
               + [("UBC-NLP/Casablanca", config) for config in ARABIC]
               + [("google/fleurs", config) for config in ASIAN if config not in PRIORITY])
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        samples = [item for result in pool.map(fetch, entries) for item in result]
    (ROOT / "manifest.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(samples)} original test clips.", flush=True)
