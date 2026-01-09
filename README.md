# Local Transcriber Pro 🎙️

[![OS - Windows](https://img.shields.io/badge/OS-Windows-blue?logo=windows&logoColor=white)](https://github.com/vhaloo/LocalTranscriberPro/releases)
[![OS - Linux](https://img.shields.io/badge/OS-Linux-orange?logo=linux&logoColor=white)](#-linux-setup)
[![OS - macOS](https://img.shields.io/badge/OS-macOS-lightgrey?logo=apple&logoColor=white)](#-mac-setup)
![Python](https://img.shields.io/badge/python-3.10_%7C_3.11_%7C_3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![GPU](https://img.shields.io/badge/GPU-NVIDIA_CUDA-green)

**The ultimate secure, offline, GPU-accelerated speech-to-text application.**

Local Transcriber Pro allows you to transcribe audio in real-time using OpenAI's Whisper models entirely on your machine. **No data leaves your computer.** Perfect for journalists, researchers, and privacy-conscious users.

---

## ⚡ Quick Start (Windows)

Due to GitHub's file size limits (2GB), the standalone executable is split into two parts.

1.  **Download** both files from the **[Releases Page](../../releases)**:
    *   `LocalTranscriberPro_v0.7.1.exe.001`
    *   `LocalTranscriberPro_v0.7.1.exe.002`
2.  **Merge them:**
    *   Open your Downloads folder.
    *   Right-click empty space -> "Open in Terminal" (or CMD).
    *   Run: `copy /b LocalTranscriberPro_v0.7.1.exe.001 + LocalTranscriberPro_v0.7.1.exe.002 LocalTranscriberPro.exe`
3.  **Run:** Launch the new `LocalTranscriberPro.exe`.
    *   *Note: First launch may take up to 60s to unpack the AI engine.*

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| **🔒 100% Private** | Runs locally. No cloud APIs, no subscriptions, no data leaks. |
| **🚀 GPU Powered** | Automatically detects NVIDIA GPUs (CUDA) for blazing fast performance. |
| **🧠 Smart Models** | Choose from `Tiny` (fastest) to `Large` (most accurate). |
| **📝 Dynamic Layout** | Switch between **Block** (paragraph) and **Stream** (continuous) text styles instantly. |
| **⏱️ Timestamps** | Toggle `[HH:MM:SS]` timestamps on or off at any time. |
| **💾 Auto-Recovery** | Never lose work. Includes crash recovery and auto-save options. |

---

## 🐧 Linux Setup

Prerequisites: `python3.10` or `python3.12`, `ffmpeg`.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/vhaloo/LocalTranscriberPro.git
    cd LocalTranscriberPro
    ```

2.  **Install System Dependencies:**
    ```bash
    # Ubuntu/Debian
    sudo apt update && sudo apt install python3-venv ffmpeg portaudio19-dev

    # Fedora
    sudo dnf install python3-devel ffmpeg portaudio-devel
    ```

3.  **Setup Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Install Libraries (GPU Support):**
    ```bash
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    pip install -r requirements.txt
    ```

5.  **Run:**
    ```bash
    python local_transcriber.py
    ```

---

## 🍎 Mac Setup

Prerequisites: `python3`, `ffmpeg` (install via Homebrew).

1.  **Install Homebrew Dependencies:**
    ```bash
    brew install python@3.12 ffmpeg portaudio
    ```

2.  **Clone & Enter:**
    ```bash
    git clone https://github.com/vhaloo/LocalTranscriberPro.git
    cd LocalTranscriberPro
    ```

3.  **Setup Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Install Libraries (Apple Silicon / Metal):**
    PyTorch automatically supports Apple Silicon (MPS) on Mac.
    ```bash
    pip install torch torchvision torchaudio
    pip install -r requirements.txt
    ```

5.  **Run:**
    ```bash
    python local_transcriber.py
    ```

---

## 🛠️ Building the EXE (Windows Only)

We have included a **One-Click Builder** script to make this easy.

1.  **Install Python 3.12** from [python.org](https://www.python.org/downloads/).
2.  **Clone this repository** (or download as ZIP and extract).
3.  Double-click **`create_installer.bat`**.

The script will automatically:
*   Set up a private virtual environment.
*   Download all necessary AI engines (approx. 3GB).
*   Compile the standalone `LocalTranscriberPro.exe`.

You will find the finished app in the `dist/` folder.

---

## ❓ Troubleshooting

**Q: The app crashes immediately on start.**
*   **A:** Ensure you have installed the correct GPU drivers for your card.

**Q: It says "CUDA Not Available" even though I have an NVIDIA card.**
*   **A:** You may have installed the CPU version of PyTorch. Run this command in your venv to fix it:
    `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --force-reinstall`

**Q: Can I use this on a CPU?**
*   **A:** Yes! Select "CPU" in the device dropdown. It will be slower, so we recommend using the "Tiny" or "Base" models.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
