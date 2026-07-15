# Hardware detection and model selection

Local Transcriber Pro separates **hardware detected** from **acceleration proven available**.

At startup it records:

- operating system and architecture
- processor and logical thread count
- physical RAM
- NVIDIA model and VRAM from `nvidia-smi`, when present
- CTranslate2 CUDA device availability
- PyTorch CUDA or Apple MPS availability
- MLX availability on Apple Silicon

The Hardware panel exposes these results to the user. Automatic mode never forces a GPU backend that failed its runtime probe.

## Automatic device priority

1. NVIDIA CUDA through faster-whisper/CTranslate2
2. Apple Silicon through MLX
3. PyTorch GPU compatibility fallback
4. Quantized CTranslate2 CPU

Manual CPU mode is always available.

## Maximum-quality model policy

The default is `Maximum quality (Auto)`, not a speed-first recommendation:

- NVIDIA with 7+ GB VRAM and 12+ GB RAM: `large-v3`
- NVIDIA with 5+ GB VRAM: `large-v3-turbo`
- NVIDIA with 4+ GB VRAM: `medium`
- NVIDIA with 2+ GB VRAM: `small`
- Apple Silicon with 16+ GB unified memory: `large-v3`
- Apple Silicon with 8+ GB: `large-v3-turbo`
- CPU with 16+ GB RAM: `large-v3` (slow but maximum quality)
- CPU with 8+ GB RAM: `medium`
- CPU with 5+ GB RAM: `small`
- CPU near 4 GB RAM: `tiny`

Every model remains manually selectable. The app never silently changes an explicit manual model choice.

## NVIDIA prerequisites

The Windows package includes a CUDA-enabled PyTorch compatibility runtime. CTranslate2 acceleration uses the NVIDIA CUDA 12/cuDNN runtime when present and falls back automatically if it is incomplete.

Linux NVIDIA acceleration requires a current driver plus CUDA 12 and cuDNN supported by the installed CTranslate2 version. The AppImage always retains CPU fallback.

## ETA calibration

Before the first run, estimates use conservative real-time factors by model and device. After every successful file, the app stores an exponential moving average of actual processing time divided by audio duration for that exact model/device pair. No audio, text or benchmark is uploaded.
