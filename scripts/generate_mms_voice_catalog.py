"""Pin additional voices for languages missing from the Piper bank."""
import concurrent.futures
import json
from pathlib import Path

import requests

LANGUAGES = {"ht": "hat", "pa": "pan", "bn": "ben", "yo": "yor", "so": "som",
             "ti": "tir", "ur": "urd-script_arabic", "ta": "tam", "ha": "hau", "ig": "ibo",
             "am": "amh", "gu": "guj", "si": "sin"}


def metadata(entry):
    language, iso3 = entry
    repository = "facebook/mms-tts-" + iso3
    response = requests.get("https://huggingface.co/api/models/" + repository, params={"blobs": "true"}, timeout=60)
    if response.status_code in {401, 404}:
        print("No public voice:", repository)
        return language, None
    response.raise_for_status()
    data = response.json()
    files = {item["rfilename"]: {"size": item["size"], "hash": item.get("lfs", {}).get("sha256", item["blobId"]),
              "algorithm": "sha256" if item.get("lfs") else "git-sha1"}
             for item in data["siblings"] if item["rfilename"].endswith(".json") or item["rfilename"] in {"README.md", "model.safetensors"}}
    if "model.safetensors" not in files:
        raise RuntimeError("No safe tensor voice: " + repository)
    return language, {"repository": repository, "revision": data["sha"], "files": files,
                      "backend": "mms", "license": "CC-BY-NC-4.0"}


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        voices = {code: voice for code, voice in pool.map(metadata, LANGUAGES.items()) if voice}
    target = Path(__file__).resolve().parents[1] / "src/data/mms_voices.json"
    target.write_text(json.dumps(voices, indent=2) + "\n", encoding="utf-8")
    print("Pinned", len(voices), "additional noncommercial voices.")
