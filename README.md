# Local Transcriber Pro 🎙️

[![OS - Windows](https://img.shields.io/badge/OS-Windows-blue?logo=windows&logoColor=white)](https://github.com/vhaloo/LocalTranscriberPro/releases)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-Release%20v0.9.6-brightgreen)

**Local Transcriber Pro** is a high-performance, private, and offline transcription tool developed by **Vhaloo**. It converts spoken audio from your microphone or existing files into text with extreme accuracy using OpenAI's Whisper models, running entirely on your own device.

![Local Transcriber Pro Preview](app_preview.png)

---

## 🌟 Why Local Transcriber Pro?

### 🔒 **Uncompromised Privacy**
*   **100% Offline:** No data ever leaves your computer. No cloud APIs, no subscriptions, no tracking.
*   **Secure:** Perfect for confidential meetings, legal/medical dictation, or personal journals.

### 🎬 **Universal Subtitle Creator**
*   **Any Source:** Create subtitles for **ANY** video or audio file (Movies, TV Shows, Podcasts, Lectures).
*   **Export as .SRT:** Automatically generate time-synced subtitles for YouTube, VLC, or Premiere Pro.
*   **Batch Process:** Drag and drop an entire season of a show to subtitle it overnight.

### ⚡ **High Performance**
*   **GPU Acceleration:** Automatically detects NVIDIA GPUs (CUDA) for blazing fast transcription (up to 10x faster than CPU).
*   **Smart Queue:** Process unlimited files in the background without freezing your PC.

---

## 🛠️ Features at a Glance

| Feature | Description |
| :--- | :--- |
| **Live Recording** | Record meetings or ideas with a real-time waveform visualizer. |
| **Translation** | Instantly translate foreign audio into English text. |
| **Auto-Cleanup** | Smart AI filtering removes repetitive "hallucinations" and loops. |
| **Model Manager** | Easily manage disk space by deleting unused AI models. |
| **Formats** | Supports `.mp3`, `.wav`, `.mp4`, `.mkv`, `.mov`, `.flac`, and more. |

---

## 📥 Installation

1.  **Download:** Go to the [**Releases Page**](https://github.com/vhaloo/LocalTranscriberPro/releases) and download the latest executable (e.g., `LocalTranscriberPro_v0.9.6.exe`).
2.  **Run:** Double-click the file to launch. No installation wizard required—it's a portable app!
3.  **GPU Setup (Optional):** For maximum speed, ensure you have an NVIDIA GPU and the latest [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) installed. If not, the app runs perfectly on CPU (just slower).

---

## 📖 User Guide

### 🎙️ Live Recording
1.  Select your **Microphone** and **Model Size** ("Small" is a good balance of speed/accuracy).
2.  Click **Record** (or press `F1`).
3.  Speak! Text will appear in real-time blocks.
4.  Click **Stop** (`F3`) to finalize. The transcript is automatically saved to your Desktop.

### 📁 File Transcription & Subtitles
1.  Click **Batch Files**.
2.  Select one or more audio/video files (Shift+Click).
3.  The app will process them one by one.
4.  **Export:** Use the "Export..." menu to save as `.srt` (Subtitles) or `.txt` (Text).

---

## ❓ Troubleshooting

### **"CUDA is not available / Running in CPU mode"**
*   **Cause:** The app cannot find an NVIDIA GPU or the correct drivers.
*   **Fix:** 
    1.  Ensure you have an NVIDIA GPU.
    2.  Update your GPU drivers via GeForce Experience.
    3.  Download and install the **[NVIDIA CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads)**.
    4.  Restart your computer.

### **"Antivirus flagged the file"**
*   **Cause:** This app is built with PyInstaller. Some antivirus software (like Windows Defender) generates "False Positives" for unsigned Python executables.
*   **Fix:** Add an exclusion for the folder where you keep the app, or click "Run Anyway" -> "More Info" if Windows SmartScreen blocks it. Since this is open source, you can verify the code yourself!

### **"Transcription is slow"**
*   **Cause:** You are likely running on CPU with a large model.
*   **Fix:** Switch to the **"Tiny"** or **"Base"** model for faster CPU performance, or upgrade your hardware.

### **"The app crashes immediately"**
*   **Fix:** Ensure you have **Visual C++ Redistributable** installed (standard on most Windows PCs). Try running the app as Administrator.

---

## 💻 Requirements
*   **OS:** Windows 10 or Windows 11 (64-bit).
*   **Processor:** Intel Core i5 / AMD Ryzen 5 or better.
*   **RAM:** 8GB recommended (4GB minimum).
*   **Storage:** ~500MB initial space + space for downloaded models (1GB-3GB).

---

## 👨‍💻 Developer
**Developed by Vhaloo**
*   [GitHub Profile](https://github.com/vhaloo)

---

## 📄 License
MIT License. Free to use, modify, and distribute.