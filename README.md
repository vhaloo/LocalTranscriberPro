# Local Transcriber Pro 3.1.0

**Private transcription. Offline conversation translation. Readable, speakable results.**

[Français](#francais) · [Download Windows 3.1.0](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v3.1.0/LocalTranscriberPro-3.1.0-Windows-x64-Setup.exe) · [All releases](https://github.com/vhaloo/LocalTranscriberPro/releases) · [Conversation guide](docs/TRANSLATION.md) · [Validation](docs/VALIDATION_3.1.md)

![Local Transcriber Pro 3.1.0: Arabic original, French translation and optional English](docs/images/local-transcriber-pro-3.1.0-universal.jpg)

*Real application, illustrative demonstration text. No private conversation is shown.*

Local Transcriber Pro turns microphone recordings, audio/video files and explicitly requested online videos into text on your own computer. Version 3.1 adds **Universal live translation**: original speech in white, translation underneath in green, an optional third language in blue, automatic two-language routing, local speech playback and a large reading view.

No API key, subscription or cloud inference is required. Download speech/translation models once; prepared models work offline. English and French reading voices are included in the Windows installer. Other voices are downloaded individually with your acceptance.

## Install

| Platform | Recommended package | Status |
|---|---|---|
| Windows 10/11 x64 | [3.1.0 installer](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v3.1.0/LocalTranscriberPro-3.1.0-Windows-x64-Setup.exe) | Self-contained, per-user installation; CUDA and CPU runtimes included |
| macOS | [Previous 2.2.0 release](https://github.com/vhaloo/LocalTranscriberPro/releases/tag/v2.2.0) | 3.1 source/build support; a 3.1 desktop package has not been validated on a Mac |
| Linux x86-64 | [Previous 2.2.0 release](https://github.com/vhaloo/LocalTranscriberPro/releases/tag/v2.2.0) | 3.1 source/build support; a 3.1 desktop package has not been validated on Linux |

Run the Windows installer, then choose **Files**, **Conference**, **Dictation**, **Universal live translation**, or **Online video**. Python, FFmpeg and a CUDA toolkit do not need separate installation. An installed NVIDIA driver is still needed for NVIDIA acceleration. Allow storage for the application runtime and selected models. The first download can take several minutes; the interface stays responsive and explains preparation.

Windows checks the official GitHub release at startup and proposes a newer stable version. Accepting downloads and verifies its size and SHA-256, saves the session, installs and relaunches. The check can be disabled. macOS/Linux currently open the release page for manual installation. [How updates work](docs/UPDATES.md).

## Universal live translation

1. Choose your destination language and, optionally, the other person's language. Both selectors are searchable.
2. Leave the conversation partner on **Detect both languages** when unknown. The first two sufficiently confident supported detections form the conversation pair; each side then translates into the other language. You can fix the pair manually before recording.
3. Optionally select **Also translate everything into…** for a third-language record.
4. Record and take turns. The app ends a speech chunk after a pause, shows the original before translation, and displays capture/processing/queue status.
5. Use **A− / A+**, **F11** or **Escape** for a readable, adjustable conversation view. Select lines and choose **Read lines**, or right-click to read/replay audio.

The default multilingual profile favors Omnilingual CTC 1B v2 on a compatible computer, falling back to the strongest compatible Whisper model. **Omnilingual CTC 1B v2** adds 1,600+ language recognition for broader coverage. Choosing a conversation language outside Whisper's language list selects Omnilingual when the computer can run it. Its separate GlotLID v3 text detector covers 2,000+ language/script labels; recognition and automatic identification have distinct coverage and limitations. Recognition, translation and speech synthesis have different coverage and quality. [Language coverage and priorities](docs/LANGUAGES.md).

The translation catalogue exposes **452 MADLAD language tokens/variants**. This is a catalogue count, not a claim of equal accuracy in 452 languages. Short speech, code-switching, dialects, names, numbers, noisy microphones and underrepresented languages can fail. Our small tests include Haitian Creole, South Asian and African languages, East/Southeast Asian languages and eight Arabic dialect groups; results and weaknesses are published in the [validation report](docs/VALIDATION_3.1.md).

## Voices, indices and overlapping speech

- **Voice bank:** 47 downloadable local voice choices, plus compatible voices already installed in Windows/macOS/Linux. Auto chooses a prepared matching local voice, then a matching installed system voice; an available missing voice is offered for download. No voice is promised for an unsupported language.
- **English/French included:** bundled Piper voices need no first-use download in the Windows package. Slow reading, stop playback and selected-line reading are available. Microphone capture pauses during playback to avoid retranscribing the app's voice.
- **Optional confidence indices:** small transcription/translation/language captions can be hidden. They are model-derived, uncalibrated indications, **not a probability that the meaning is correct**. A model without a score shows unavailable rather than an invented number.
- **Two overlapping voices (experimental, off by default):** an optional local SepFormer model attempts two-source separation. Channels are temporary hypotheses, not stable speaker identities; the model was trained on English and can omit or duplicate speech. Taking turns remains the dependable workflow.

Piper voice licences vary by model; model cards are kept with downloads. MMS voices are labelled **CC BY-NC 4.0** and their download prompt explains the noncommercial restriction. The application code's MIT licence does not replace model licences. [Third-party models and licences](docs/MODELS_AND_LICENSES.md).

## Existing workflows retained

- Audio/video batches, folder drag-and-drop and optional neighbouring video subtitles.
- Live microphone waveform, level and VU meter; automatic input selection; pause/resume/stop.
- Unlimited dictation and conference recording; optional speaker labels.
- Online video audio retrieval through the bundled FFmpeg/Node/yt-dlp stack.
- All Whisper sizes, local Qwen3-ASR and Parakeet, automatic CPU/GPU selection and manual model/device controls.
- Model list ordered by indicative multilingual accuracy, with separate relative speed and language-coverage scores and hardware admission reasons.
- Plain transcript corrections, custom vocabulary, block/line layouts, timestamps and durations.
- Automatic TXT, SRT, VTT, CSV and JSON exports; bilingual exports keep the original and translations together, with logical Unicode text.
- Session history, output-folder selection, crash recovery and progressive TXT/JSON recording checkpoints.
- Cancellation, bounded live queues and preserved captured audio when processing fails.
- English/French interface, contextual explanations and in-app conversation help.

Bilingual text is protected against accidental rewriting of original/translation associations. Export JSON to preserve all structured metadata. Translator-produced timings correspond to source speech segments, not translated word-level alignment.

## Local models and hardware

| Recognizer | Coverage advertised by publisher | Typical model download | Practical role |
|---|---:|---:|---|
| Qwen3-ASR 1.7B | 30 languages | ~6.2 GB including aligner | General accuracy auto on a compatible strong GPU; manual CPU choice |
| Qwen3-ASR 0.6B | 30 languages | ~2.9 GB including aligner | Smaller Qwen option |
| Whisper large-v3 | 100 language IDs | ~3.1 GB | Broad multilingual alternative; preferred on smaller compatible computers |
| Omnilingual CTC 1B v2 | 1,600+ recognition languages | ~5.60 GB including GlotLID | Universal auto on capable computers; CPU, 16 GB total RAM / 10 GB available |
| Parakeet TDT v3 int8 | 25 European languages | ~0.64 GB | Fast CPU profile |
| Whisper Tiny → Medium, Large v1/v2, Turbo and English variants | Model dependent | ~0.08–3.1 GB | All previous choices remain available |

Universal translation adds **MADLAD-400 3B int8 (~2.96 GB)** and requires at least 12 GB total / 6 GB currently available system RAM. It uses a compatible GPU if enough VRAM remains after loading recognition; otherwise it runs on CPU. A CPU-only computer can be slower than conversation speed. Optional separation adds ~113 MB; downloadable voices typically add ~60–150 MB each.

Admission checks total and available RAM, disk space, usable backends and free VRAM before loading. Accuracy/speed/coverage scores are relative catalogue guides, not measured cross-language accuracy percentages. [Exact hardware policy](docs/HARDWARE.md).

## Privacy

Speech, transcript, translation, voice synthesis and speaker analysis run locally. Models, requested videos and enabled update checks use Internet; no audio/text is sent to an inference service. Prepared models can be required offline. Settings/history/recovery remain outside the application runtime and survive upgrades. Exports and optional saved audio are ordinary local files under your chosen output folder (default `Documents/Transcriptions`).

No application analytics or telemetry is enabled. TLS verification stays enabled. Releases have SHA-256 manifests; Windows installers currently have no Authenticode signature. [Privacy details](docs/PRIVACY.md).

## Developers and releases

Python 3.12, Git and Node 22+ are the supported build baseline:

```text
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pip install -r requirements-diarization.txt
.venv/Scripts/python main.py
.venv/Scripts/python -m ruff check main.py src tests scripts
.venv/Scripts/python -m pytest
.venv/Scripts/python scripts/check_release_docs.py
```

`scripts/build_windows.ps1` prepares icons, the video JavaScript runtime and bundled English/French voices, then builds the app. Inno Setup builds the installer. Documentation/version/screenshot checks fail a release whose GitHub instructions are stale. [Build, validation and release procedure](docs/BUILDING.md) · [Changelog](CHANGELOG.md).

<a id="francais"></a>
## Français

**Transcrire, traduire et relire à voix haute sur votre ordinateur.** La 3.1.0 conserve les fonctions de transcription existantes et ajoute **Traduction universelle live**. [Installer Windows 3.1.0](https://github.com/vhaloo/LocalTranscriberPro/releases/download/v3.1.0/LocalTranscriberPro-3.1.0-Windows-x64-Setup.exe).

Choisissez votre langue, lancez l'enregistrement et parlez chacun votre tour. L'original apparaît en blanc, la traduction juste dessous en vert. Deux langues détectées avec suffisamment de confiance forment automatiquement une paire : chaque interlocuteur est traduit vers l'autre. Vous pouvez fixer l'autre langue et ajouter une troisième traduction en bleu. Les menus permettent une recherche par nom ou code de langue.

**A− / A+** règlent la taille du texte de 14 à 48 ; **F11** agrandit la lecture sur l'écran courant et **Échap** revient à l'interface. Les indicateurs montrent l'écoute, le découpage après une pause, la transcription, la traduction et le nombre de fragments en attente. L'original s'affiche avant la fin de la traduction.

Sélectionnez une ou plusieurs lignes, puis **Lire les lignes**, ou utilisez le clic droit. La banque propose 47 voix locales et les voix compatibles déjà installées dans le système. Le français et l'anglais sont inclus dans l'installateur Windows ; les autres voix se téléchargent au besoin avec votre accord. Une lecture lente et un bouton d'arrêt sont disponibles. Pendant la lecture, le microphone est mis en pause puis reprend s'il n'avait pas été mis en pause manuellement.

Les petits **indices de confiance** s'activent ou se masquent. Ils reflètent les scores internes disponibles, pas une certitude sur le sens. **2 voix superposées · essai** est une option expérimentale désactivée par défaut : elle tente de séparer deux voix, sans garantir leur reconstruction ni leur identité.

La reconnaissance utilise Whisper, Qwen, Parakeet ou le nouveau **Omnilingual 1B v2**, selon le profil choisi et le matériel. Omnilingual annonce plus de 1 600 langues de reconnaissance ; la traduction expose 452 langues/variantes MADLAD. Ces nombres décrivent des couvertures différentes, avec une précision variable. La sélection automatique multilingue privilégie Omnilingual sur une machine compatible, avec repli vers Whisper ; les autres modèles restent sélectionnables. Les langues fréquemment utiles au Canada sont placées en accès rapide, avec des essais réels en créole haïtien, en langues sud-asiatiques et africaines, dans huit groupes de dialectes arabes et en langues asiatiques. [Couverture, priorités et limites](docs/LANGUAGES.md).

L'application conserve les fichiers audio/vidéo, les conférences, la dictée sans fin, les vidéos en ligne, les étiquettes de personnes, le vocabulaire, l'historique, la récupération et les exports TXT/SRT/VTT/CSV/JSON. Les modèles préparés fonctionnent hors ligne ; seul leur téléchargement initial, les vidéos explicitement demandées et la vérification activée des mises à jour utilisent Internet. Les voix MMS ont une licence non commerciale indiquée dans la banque.

Au démarrage, une nouvelle version officielle est proposée. Sous Windows, accepter lance le téléchargement vérifié, la sauvegarde, l'installation et le redémarrage de l'application. Les données existantes sont conservées. [Mode d'emploi complet](docs/TRANSLATION.md) · [Résultats des tests 3.1.0](docs/VALIDATION_3.1.md).

## Licence and archive

Application code: MIT, by [Vhaloo](https://github.com/vhaloo). Models and bundled dependencies retain their own licences. The original version remains in [archive-v1.1-before-v2.0](https://github.com/vhaloo/LocalTranscriberPro/releases/tag/archive-v1.1-before-v2.0).
