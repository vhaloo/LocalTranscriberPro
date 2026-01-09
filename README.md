# Local Transcriber Pro 🎙️

[![OS - Windows](https://img.shields.io/badge/OS-Windows-blue?logo=windows&logoColor=white)](https://github.com/vhaloo/LocalTranscriberPro/releases)
[![OS - Linux](https://img.shields.io/badge/OS-Linux-orange?logo=linux&logoColor=white)](#-linux-setup)
[![OS - macOS](https://img.shields.io/badge/OS-macOS-lightgrey?logo=apple&logoColor=white)](#-mac-setup)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![GPU](https://img.shields.io/badge/GPU-NVIDIA_%7C_Apple_Silicon-green)

![App Preview](./app_preview.png)

**Secure, offline, speech-to-text for everyone.**
Runs entirely on your machine. No cloud. No fees. No data leaks.

---

## ✨ Features

*   **🌍 Universal Compatibility:** Runs on everything from high-end Gaming PCs to modest Laptops and MacBooks.
*   **🚀 GPU Acceleration:** 
    *   **Windows/Linux:** Supports NVIDIA CUDA for blazing speeds.
    *   **Mac:** Supports **Apple Metal (MPS)** on M1/M2/M3 chips.
*   **🐢 CPU Mode:** Works on standard computers without dedicated graphics cards (using optimized "Tiny" or "Base" models).
*   **📁 File Transcription:** Drag & drop audio/video files to transcribe meetings, podcasts, or lectures.
*   **🌍 99 Languages:** Auto-detects and transcribes nearly any language.
*   **📝 Dynamic Layout:** Toggle between Block (paragraph) and Stream (continuous) text styles.
*   **💾 Auto-Recovery:** Never lose work. Sessions are auto-saved.

---

## 💻 System Requirements

| | **Minimum (CPU Only)** | **Recommended (GPU)** |
| :--- | :--- | :--- |
| **Windows** | Intel i5 / AMD Ryzen 5<br>8GB RAM | NVIDIA GTX 1060 or higher<br>16GB RAM |
| **Mac** | Intel MacBook (2018+)<br>8GB RAM | Apple M1 / M2 / M3<br>8GB RAM |
| **Linux** | Modern Quad-Core CPU<br>8GB RAM | NVIDIA GPU (CUDA 12)<br>16GB RAM |

*   **CPU Mode:** Slower (1x-2x real-time), best for "Tiny" or "Base" models.
*   **GPU Mode:** Extremely fast (10x-50x real-time), enables "Small", "Medium", and "Large" models.

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
| **App crashes on start** | Ensure you have installed [NVIDIA Drivers](https://www.nvidia.com/Download/index.aspx) (Windows/Linux). |
| **"CUDA Not Available"** | Reinstall using **Option 1** to force GPU libraries. If you don't have an NVIDIA card, this is normal; the app will use CPU. |
| **Mac M1/M2 Slow?** | Ensure you are on macOS 12.3+ for Metal acceleration. |

---

## 📄 License
MIT License. Free to use and modify.