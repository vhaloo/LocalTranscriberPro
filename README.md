# Local Transcriber Pro 🎙️

[![OS - Windows](https://img.shields.io/badge/OS-Windows-blue?logo=windows&logoColor=white)](https://github.com/vhaloo/LocalTranscriberPro/releases)
[![OS - Linux](https://img.shields.io/badge/OS-Linux-orange?logo=linux&logoColor=white)](#-linux-setup)
[![OS - macOS](https://img.shields.io/badge/OS-macOS-lightgrey?logo=apple&logoColor=white)](#-mac-setup)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![GPU](https://img.shields.io/badge/GPU-NVIDIA_CUDA-green)

![App Preview](./app_preview.png)

**Secure, offline, GPU-accelerated speech-to-text.**
No cloud APIs. No subscriptions. No data leaks. Runs entirely on your machine using OpenAI's Whisper.

---

## ✨ Features

*   **📁 File Transcription:** (New in v0.8) Drag & drop audio/video files to transcribe them automatically.
*   **🚀 GPU Powered:** Automatically detects NVIDIA GPUs (CUDA) and Apple Silicon (MPS) for 10x faster transcription.
*   **🌍 Multi-Language:** Supports **99 languages** (English, Spanish, French, Chinese, etc.).
*   **🧠 Smart Models:**
    *   **Tiny:** Instant speed (good for dictation).
    *   **Small/Medium:** High accuracy (good for meetings).
    *   **Large:** Professional precision (requires 8GB+ RAM).
*   **📝 Dynamic Formatting:** Toggle between **Block** (paragraph) and **Stream** (continuous) text styles.
*   **⏱️ Timestamps:** Toggle `[HH:MM:SS]` timestamps on/off instantly.
*   **💾 Auto-Recovery:** Crashed? Your session is auto-saved.

---

## 📥 Installation (Choose One)

### Option 1: Automatic Web Installer (Recommended) 🏆
*The easiest way. It downloads and builds the app for you automatically.*

**Prerequisite:** [Download Python 3.12](https://www.python.org/downloads/release/python-3128/) (Check "Add to PATH" during install).

#### Windows
1.  **Download** `Web_Builder.cmd` from the **[Releases Page](../../releases/latest)**.
2.  Double-click the file.
3.  Wait for the script to finish (~3GB download).
4.  The app will appear on your **Desktop**.

#### Linux / Raspberry Pi / Mac
Run this command in your terminal:
```bash
curl -sL https://github.com/vhaloo/LocalTranscriberPro/releases/latest/download/web_builder.sh | bash
```

### Option 2: Direct Download (Windows Standalone)
*If you prefer downloading the exe directly.*

1.  Go to the **[Releases Page](../../releases/latest)**.
2.  Download these **3 files**:
    *   `Merge_Installer_v0.8.cmd`
    *   `LocalTranscriberPro_v0.8.exe.001`
    *   `LocalTranscriberPro_v0.8.exe.002`
3.  Place them in the **same folder**.
4.  Double-click **`Merge_Installer_v0.8.cmd`**.
5.  Launch the resulting `LocalTranscriberPro.exe`.

### Option 3: Run from Source (Devs)

**Prerequisite:** [Python 3.12](https://www.python.org/downloads/release/python-3128/).

#### Windows
```bash
git clone https://github.com/vhaloo/LocalTranscriberPro.git
cd LocalTranscriberPro
create_installer.bat
```

#### Linux / macOS
```bash
git clone https://github.com/vhaloo/LocalTranscriberPro.git
cd LocalTranscriberPro
python3 -m venv venv
source venv/bin/activate
pip install torch torchvision torchaudio
pip install -r requirements.txt
python local_transcriber.py
```

---

## ❓ Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **App crashes on start** | Ensure you have installed [NVIDIA Drivers](https://www.nvidia.com/Download/index.aspx). |
| **"CUDA Not Available"** | Reinstall using **Option 1** (Web Builder) to force GPU libraries. |
| **Mac M1/M2 Slow?** | Ensure you are on macOS 12.3+ for Metal acceleration. |

---

## 📄 License
MIT License. Free to use and modify.
