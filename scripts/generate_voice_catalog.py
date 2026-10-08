"""Refresh pinned Piper/Sherpa voice metadata explicitly at development time."""
import concurrent.futures
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
PREFERRED = {
    "ar": "ar_JO-kareem-medium", "fr": "fr_FR-siwis-medium", "en": "en_US-lessac-medium",
    "zh": "zh_CN-huayan-medium", "hi": "hi_IN-pratham-medium", "fa": "fa_IR-amir-medium",
    "vi": "vi_VN-vais1000-medium", "id": "id_ID-news_tts-medium", "ne": "ne_NP-google-medium",
    "es": "es_ES-davefx-medium", "pt": "pt_BR-faber-medium", "de": "de_DE-thorsten-medium",
    "it": "it_IT-paola-medium", "ru": "ru_RU-irina-medium", "uk": "uk_UA-ukrainian_tts-medium",
    "tr": "tr_TR-dfki-medium", "sw": "sw_CD-lanfrica-medium", "kk": "kk_KZ-issai-high",
    "nl": "nl_BE-nathalie-medium", "pl": "pl_PL-gosia-medium", "cs": "cs_CZ-jirka-medium",
    "da": "da_DK-talesyntese-medium", "el": "el_GR-rapunzelina-low", "fi": "fi_FI-harri-medium",
    "hu": "hu_HU-anna-medium", "ro": "ro_RO-mihai-medium", "no": "no_NO-talesyntese-medium",
    "sv": "sv_SE-nst-medium", "sk": "sk_SK-lili-medium", "sr": "sr_RS-serbski_institut-medium",
    "sl": "sl_SI-artur-medium", "ka": "ka_GE-natia-medium", "is": "is_IS-salka-medium",
    "ca": "ca_ES-upc_ona-medium", "cy": "cy_GB-gwryw_gogleddol-medium", "lv": "lv_LV-aivars-medium",
}


def metadata(entry):
    language, name = entry
    repository = "csukuangfj/vits-piper-" + name
    response = requests.get("https://huggingface.co/api/models/" + repository, params={"blobs": "true"}, timeout=60)
    response.raise_for_status()
    info = response.json()
    def spec(item):
        return {"size": item["size"], "hash": item.get("lfs", {}).get("sha256", item["blobId"]),
                "algorithm": "sha256" if item.get("lfs") else "git-sha1"}
    files = {item["rfilename"]: spec(item) for item in info["siblings"]
             if item["rfilename"] in {name + ".onnx", "tokens.txt", "MODEL_CARD"}}
    if len(files) != 3:
        raise RuntimeError("Voice has incomplete metadata: " + repository)
    voice = {"repository": repository, "revision": info["sha"], "model": name + ".onnx", "files": files}
    data = {item["rfilename"]: spec(item) for item in info["siblings"] if item["rfilename"].startswith("espeak-ng-data/")}
    return language, voice, data


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        entries = list(pool.map(metadata, PREFERRED.items()))
    voices = {language: voice for language, voice, _ in entries}
    common = next(data for language, _, data in entries if language == "fr")
    payload = {"voices": voices, "common": dict(voices["fr"], files=common)}
    (ROOT / "src/data/voices.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Pinned {len(voices)} voices and {len(common)} shared phonemizer files.")
