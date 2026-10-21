"""Prepare a selected conversation profile, then exercise local ASR/MT/TTS.

No inference API is used. offline=True disables Hub downloads in the ASR
loader; preparation of optional voices is explicit. Missing voices are listed.
"""
from __future__ import annotations

from dataclasses import replace


def prepare_profile(engine, voices, options, model, device, languages, download=False):
    options = replace(options, offline=not download, original_callback=None, activity_callback=None)
    with engine._load_lock:
        status = engine.load_model(model, device, options=options)
        results = [f"ASR: {status.model_id} · {status.device}"]
        if options.target_language:
            for code in languages:
                translated = engine.translator.translate("Bonjour. Hello. 123.", code)
                if not translated:
                    raise RuntimeError(f"Empty local translation: {code}")
                results.append(f"MT: {code} ✓")
        probe = None
        for code in languages:
            if not voices.supports(code):
                results.append(f"TTS: {code} — no local voice in catalogue")
                continue
            if not download and not voices.ready(code):
                results.append(f"TTS: {code} — not prepared")
                continue
            voices.prepare(code, allow_download=download)
            audio, rate = voices.synthesize("Bonjour" if code == "fr" else "Hello", code, allow_download=False)
            if len(audio) == 0:
                raise RuntimeError(f"Empty local voice: {code}")
            if probe is None and rate == 22050:
                from scipy.signal import resample_poly
                probe = resample_poly(audio, 320, 441).astype("float32")
            results.append(f"TTS: {code} ✓")
        if probe is not None:
            result = engine.transcribe_audio(probe, replace(options, target_language=None, conversation=False,
                                                           overlap_separation=False, word_timestamps=False))
            if not result.get("text", "").strip():
                raise RuntimeError("Local voice-to-recognition test returned no text")
            results.append("ASR local audio ✓")
        return "\n".join(results)
