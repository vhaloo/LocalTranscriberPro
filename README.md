# Local Transcriber Pro 🎙️

[![OS - Windows](https://img.shields.io/badge/OS-Windows-blue?logo=windows&logoColor=white)](https://github.com/vhaloo/LocalTranscriberPro/releases)
[![OS - Linux](https://img.shields.io/badge/OS-Linux-orange?logo=linux&logoColor=white)](#-linux-setup)
[![OS - macOS](https://img.shields.io/badge/OS-macOS-lightgrey?logo=apple&logoColor=white)](#-mac-setup)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![GPU](https://img.shields.io/badge/GPU-NVIDIA_CUDA-green)

**Secure, offline, GPU-accelerated speech-to-text.**
No cloud APIs. No subscriptions. No data leaks. Runs entirely on your machine using OpenAI's Whisper.

---

## 📥 Installation (Choose One)

### Option 1: Automatic Web Installer (Recommended) 🏆
*The easiest way. It downloads and builds the app for you automatically.*

1.  **Download** `Web_Builder.cmd` from the **[Releases Page](../../releases/latest)**.
2.  Double-click the file.
3.  Wait for the script to finish (it downloads ~3GB of AI engines).
4.  The app will appear on your **Desktop**.

*(Note: Requires Python 3.12 installed. If missing, the script will guide you.)*

### Option 2: Direct Download (Split Files)
*If you prefer downloading the exe directly.*

1.  Go to the **[Releases Page](../../releases/latest)**.
2.  Download these **3 files**:
    *   `Merge_Installer.cmd`
    *   `LocalTranscriberPro_v0.7.1.exe.001`
    *   `LocalTranscriberPro_v0.7.1.exe.002`
3.  Place them in the **same folder** (e.g., Downloads).
4.  Double-click **`Merge_Installer.cmd`**.
5.  Launch the resulting `LocalTranscriberPro.exe`.

### Option 3: Run from Source (Linux/Mac/Devs)
*For developers or non-Windows users.*

#### Windows
```bash
git clone https://github.com/vhaloo/LocalTranscriberPro.git
cd LocalTranscriberPro
create_installer.bat
```

#### Linux / macOS
Prerequisites: `python3.12`, `ffmpeg` (install via package manager).

```bash
git clone https://github.com/vhaloo/LocalTranscriberPro.git
cd LocalTranscriberPro
python3 -m venv venv
source venv/bin/activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
python local_transcriber.py
```

---

## ✨ Features

*   **🚀 GPU Powered:** Automatically detects NVIDIA GPUs (CUDA) for 10x faster transcription.
*   **🧠 Smart Models:**
    *   **Tiny:** Instant speed (good for dictation).
    *   **Small/Medium:** High accuracy (good for meetings).
    *   **Large:** Professional precision (requires 8GB+ VRAM).
*   **📝 Dynamic Formatting:**
    *   **Block Mode:** Standard paragraph layout.
    *   **Stream Mode:** Continuous text stream (like a book).
*   **⏱️ Timestamps:** Toggle `[HH:MM:SS]` timestamps on/off instantly.
*   **💾 Auto-Recovery:** Crashed? No problem. Your session is auto-saved.
*   **📂 Auto-Open:** Transcript opens in Notepad immediately after saving.

---

## ❓ Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **App crashes on start** | Ensure you have installed [NVIDIA Drivers](https://www.nvidia.com/Download/index.aspx). |
| **"CUDA Not Available"** | You might be using the CPU version. Reinstall using **Option 1** (Web Builder) to force GPU libraries. |
| **"Permission Denied"** | Close any running instances of the app or Python before updating/building. |

---

## 📄 License
MIT License. Free to use and modify.
