"""Prepare verified French/English voices for the self-contained installer."""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.speech_output import CATALOG, LocalSpeechOutput  # noqa: E402

if __name__ == "__main__":
    engine = LocalSpeechOutput()
    output = ROOT / "artifacts/default-voices"
    for language in ("fr", "en"):
        voice, folder, data = engine.prepare(language)
        for name in voice["files"]:
            destination = output / language / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(folder / name, destination)
        for name in CATALOG["common"]["files"]:
            destination = output / "phonemizer" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(data / name, destination)
    print("Verified French and English voices prepared for packaging.")
