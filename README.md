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

## 📥 Choose Your Installation Method

### Option A: Instant Run (Recommended)
*Best for users who want to run the app immediately without installing Python.*

1.  Go to the **[Releases Page](../../releases/latest)**.
2.  Download these **3 files**:
    *   `Merge_Installer.cmd`
    *   `LocalTranscriberPro_v0.7.1.exe.001`
    *   `LocalTranscriberPro_v0.7.1.exe.002`
3.  Place them in the **same folder** (e.g., Downloads).
4.  Double-click **`Merge_Installer.cmd`**.
5.  The app will launch automatically!

*(Why split files? GitHub limits file sizes to 2GB, and the AI engine is 3GB. The merger script combines them back into one app.)*

---

### Option B: Web Builder (Tiny Download)
*Best if you have a fast internet connection but don't want to download split files manually.*

1.  Download **`Web_Builder.cmd`** from the [Releases Page](../../releases/latest).
2.  Double-click it.
3.  The script will:
    *   Download the source code.
    *   Download the AI engine (3GB).
    *   Compile the `.exe` for you.
    *   Place the finished app on your **Desktop**.

*Note: Requires Python 3.12 installed on your system. If missing, the script will tell you.*

---

### Option C: Run from Source (Developers/Linux/Mac)
*Best for developers or non-Windows users.*

#### Windows
```bash
# 1. Clone
git clone https://github.com/vhaloo/LocalTranscriberPro.git
cd LocalTranscriberPro

# 2. Setup (One-Click)
create_installer.bat
```

#### Linux / macOS
Prerequisites: `python3.12`, `ffmpeg`.

```bash
# 1. Clone
git clone https://github.com/vhaloo/LocalTranscriberPro.git
cd LocalTranscriberPro

# 2. Setup Env
python3 -m venv venv
source venv/bin/activate

# 3. Install GPU Libraries
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt

# 4. Run
python local_transcriber.py
```

---

## ✨ Features

*   **🚀 GPU Acceleration:** Automatically detects NVIDIA GPUs (CUDA) for 10x faster transcription.
*   **📝 Dynamic Formatting:**
    *   **Block Mode:** Standard paragraphs.
    *   **Stream Mode:** Continuous text stream (like a book).
*   **⏱️ Timestamps:** Toggle `[HH:MM:SS]` timestamps on/off in real-time.
*   **💾 Auto-Recovery:** Crashed? No problem. Your session is auto-saved.
*   **📂 Auto-Open:** File opens instantly in Notepad when you stop recording.

---

## ❓ Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **App crashes on start** | Ensure you have installed [NVIDIA Drivers](https://www.nvidia.com/Download/index.aspx). |
| **"CUDA Not Available"** | You might be using the CPU version. Reinstall using the "Option B" web builder to force GPU libraries. |
| **FFmpeg Error** | Ensure `ffmpeg` is installed and added to your PATH (Linux/Mac only). |

---

## 📄 License
MIT License. Free to use and modify.