# Local Transcriber Pro 🎙️

**A secure, offline, GPU-accelerated speech-to-text application for Windows.**

Local Transcriber Pro allows you to transcribe audio in real-time using OpenAI's Whisper models entirely on your machine. No data leaves your computer.

![Version](https://img.shields.io/badge/version-v0.7.1-blue)
![Python](https://img.shields.io/badge/python-3.12-yellow)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

*   **🔒 100% Privacy:** Runs locally. No cloud APIs, no subscriptions, no data leaks.
*   **🚀 GPU Acceleration:** Automatically detects NVIDIA GPUs (CUDA) for blazing fast transcription.
*   **🧠 Model Selection:** Choose from `Tiny` (fastest) to `Large` (most accurate) based on your hardware.
*   **📝 Dynamic Formatting:**
    *   **Block Mode:** Standard paragraph style.
    *   **Stream Mode:** Continuous text stream.
    *   **Timestamps:** Optional `[HH:MM:SS]` or `[MM:SS]` tags.
*   **💾 Auto-Save & Recovery:** Never lose a session. Includes crash recovery and auto-save options.
*   **🛠️ Standalone:** Available as a single `.exe` file (no Python installation required).

## 🚀 Installation

### Option 1: Standalone (Recommended for Users)
Download the latest `LocalTranscriberPro.exe` from the [Releases](releases) page.
*   *Note: First launch may take up to 60s to initialize the AI engine.*

### Option 2: Run from Source (Developers)
Requirements: Python 3.10 - 3.12 (Python 3.14 is not yet supported by Torch/CUDA).

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/LocalTranscriberPro.git
    cd LocalTranscriberPro
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install GPU-Enabled PyTorch (Vital):**
    ```bash
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run:**
    ```bash
    python local_transcriber.py
    ```

## 🎮 Usage

1.  **Select Microphone:** Choose your input device.
2.  **Select Model:** `Small` is recommended for most GPUs. `Tiny` for CPUs.
3.  **Record:** Press **F1** or click Record.
4.  **Format:** Toggle timestamps or layout styles in real-time.
5.  **Stop:** Press **F3** to finish. The file will auto-open (if enabled).

## 🏗️ Building the EXE
If you want to build the executable yourself:
```bash
build_standalone.bat
```
This uses PyInstaller to bundle the Python environment and CUDA libraries into a single file.

## 📄 License
MIT License. Free to use and modify.
