# Models and third-party licences — 3.3.0

Application source is MIT. Weight licences, voice/model cards and dependency licences remain independent. The added Qwen, Parakeet, Omnilingual, translation and voice repositories use pinned revisions with local verification. Legacy Whisper uses its engine's official model catalogue and local cache. Downloads contain no repository-provided executable Python. Prepared model files work offline.

| Component | Publisher/reference | Licence / qualification |
|---|---|---|
| Whisper | [OpenAI](https://github.com/openai/whisper) | MIT; every previous model choice retained |
| Qwen3-ASR and aligner | [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) | Apache 2.0 model family; pinned revisions in `src/models.py` |
| Parakeet ONNX | [Sherpa export](https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8) | Consult original NVIDIA and export model cards |
| Omnilingual CTC 1B v2 | [Meta project](https://github.com/facebookresearch/omnilingual-asr), [pinned Sherpa export](https://huggingface.co/csukuangfj2/sherpa-onnx-omnilingual-asr-1600-languages-1B-ctc-v2-2026-02-05) | Apache 2.0; model LICENSE downloaded with files |
| GlotLID v3 / fastText runtime | [LMU model](https://huggingface.co/cis-lmu/glotlid) | Apache 2.0 plus notices; 2,000+ language/script labels, separate from speech recognition |
| MADLAD-400 3B | [Google model](https://huggingface.co/google/madlad400-3b-mt), [CTranslate2 conversion](https://huggingface.co/santhosh/madlad400-3b-ct2) | Apache 2.0; language tokens do not imply equal accuracy |
| Optional MADLAD-400 7B MT-BT | [Google model](https://huggingface.co/google/madlad400-7b-mt-bt), [Nextcloud-AI int8 conversion](https://huggingface.co/Nextcloud-AI/madlad400-7b-mt-bt-ct2-int8) | Apache 2.0; pinned revision, sizes and hashes in `src/data/translation_7b.json`; optional 8.33 GB model, not bundled |
| Piper/Sherpa voices | [Sherpa voice documentation](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html) | Individual voice MODEL_CARD retained; licences vary |
| Bundled French Siwis voice | [Voice card](https://huggingface.co/rhasspy/piper-voices/blob/main/fr/fr_FR/siwis/medium/MODEL_CARD) | CC BY 4.0 dataset; retain voice attribution/model card |
| Bundled English Lessac voice | [Voice card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/lessac/medium/MODEL_CARD) | Voice card's dataset/model terms apply |
| MMS voices | [Meta MMS](https://huggingface.co/facebook/mms-tts) | **CC BY-NC 4.0**; not bundled, individually proposed with licence notice |
| eSpeak NG phonemizer data | [eSpeak NG](https://github.com/espeak-ng/espeak-ng) | GPL 3.0; distributed phonemizer data/licence retained; upstream source linked |
| SepFormer WHAMR | [SpeechBrain model](https://huggingface.co/speechbrain/sepformer-whamr16k) | Apache 2.0; English-trained experimental two-source separation |

Voice manifests `src/data/voices.json` and `mms_voices.json` record source repositories, immutable revisions, filenames, sizes and hashes. `omnilingual.json` records recognition and GlotLID model provenance. The French and English voice folders retain model cards. Other voice downloads are ordinary files in the per-user cache, without cloud synthesis.

Test-only audio is not part of the application or public repository. Casablanca CC BY-NC-ND samples are evaluated locally without redistribution. FLEURS and Haitian corpus references are listed in [historical validation](VALIDATION_3.1.md); the [3.3 validation report](VALIDATION_3.3.md) identifies the expanded diagnostics. Published diagnostics contain aggregate metrics, not the recordings or complete reference/hypothesis text.

TranslateGemma was not added as an automatic backend because access to its official model files required external account/model authorization during preparation. Larger Omnilingual 3B/7B variants require a native fairseq2n runtime unavailable as a Windows binary wheel in this build environment. Their absence does not reduce the retained 1B model's published language inventory. No gated credentials, accepted terms or platform support are invented.

The packaged runtime also includes Python, PyTorch, CTranslate2, Sherpa ONNX, SpeechBrain, FFmpeg, customtkinter, yt-dlp, Node and their transitive dependencies. Preserve their licence notices when distributing. Node's exact-version licence is included in `js-runtime/LICENSE.txt`.
