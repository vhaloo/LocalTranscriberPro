# Hardware detection and safe model selection

Local Transcriber Pro 2.2 treats a model as available only after its complete runtime route has passed conservative admission checks. Merely finding a GPU name is never considered proof that GPU inference works.

## What is measured at startup

- operating system and architecture
- processor and logical thread count
- physical RAM and currently available RAM
- swap/page-file capacity for diagnostics (not used to justify an unsafe model)
- free space on the model-cache drive
- NVIDIA model, driver, total VRAM and currently free VRAM
- CTranslate2 CPU compute types and CUDA device availability
- PyTorch CUDA or Apple MPS availability
- MLX availability on Apple Silicon

The same free-memory and free-storage snapshot is refreshed immediately before a model is loaded. This protects against an old saved setting or another application consuming memory after Local Transcriber Pro started.

The admitted maximum-quality model is preloaded during the startup splash. Changing the model or processor starts a background replacement load immediately. Record therefore uses the already-armed engine in the normal case; the full-window initialization message remains only as a truthful fallback if preloading has not completed or the resource check changed.

## Device routing

Automatic mode checks routes in this order for each individual model:

1. NVIDIA CUDA, if its runtime, host RAM, total VRAM and free VRAM all pass
2. Apple Silicon MLX/MPS, using unified-memory safety limits
3. quantized CTranslate2 CPU

A powerful GPU that cannot fit a particular model does not disqualify the model if the CPU route has enough RAM. Automatic mode can therefore choose a slow CPU route when it is the only safe way to preserve maximum quality.

Manual CUDA and Metal choices appear only when their packaged runtime has actually passed detection. Manual CPU remains available whenever CTranslate2 reports a supported CPU compute type.

## Conservative minimums

| Model family | First download | CPU total RAM | CPU free RAM at load | GPU VRAM | Minimum host RAM on GPU |
|---|---:|---:|---:|---:|---:|
| Large v1/v2/v3 | 3.10 GB | 12 GB | 5.0 GB | 7.0 GB | 8.0 GB |
| Large v3 Turbo | 1.62 GB | 8 GB | 3.0 GB | 5.0 GB | 5.2 GB |
| Medium | 1.53 GB | 8 GB | 3.0 GB | 4.0 GB | 5.2 GB |
| Small | 0.49 GB | 5 GB | 1.6 GB | 2.0 GB | 4.0 GB |
| Base | 0.15 GB | 4.5 GB | 1.0 GB | 1.0 GB | 4.0 GB |
| Tiny | 0.08 GB | 3.5 GB | 0.65 GB | 0.8 GB | 4.0 GB |

The first download also requires approximately `model size × 1.35 + 0.25 GB` of free storage for temporary files and the final cache. A downloaded model no longer needs that download-space reserve.

These are admission floors, not promises of speed. A 4 GB Windows computer is deliberately routed to Tiny on CPU; it can be slow but remains supported.

## What the user sees

The **Models and minimum requirements** window always shows the entire official Whisper catalogue. Each row contains its CPU RAM, GPU VRAM and download requirement.

- safe rows have a **Select** button and state which device will be used
- unsafe rows are greyed out, disabled and state the exact missing resource
- temporary pressure is distinguished from a permanent hardware limit
- **Safest maximum quality (Auto)** names the model it will actually use

The engine repeats the check even if a caller bypasses the interface. A stale or unsafe explicit model is replaced by the largest safe choice. If a native engine still refuses a valid allocation, up to two smaller admitted routes are attempted without closing the application.

## Packaged prerequisites

Release packages include Python, CTranslate2/faster-whisper, the platform AI runtime, microphone libraries, speaker-identification libraries and a platform-specific FFmpeg binary. Users do not install Python, a CUDA toolkit or FFmpeg separately.

An NVIDIA display driver is supplied by the computer/GPU manufacturer, not modified by Local Transcriber Pro. If it is absent or incompatible, Automatic mode simply uses the packaged CPU engine.

## ETA calibration

Before the first transcription, estimates use conservative real-time factors by model and device. Every successful run stores an exponential moving average of actual processing time divided by audio duration for that exact model/device pair. No audio, text, specification or benchmark is uploaded.
