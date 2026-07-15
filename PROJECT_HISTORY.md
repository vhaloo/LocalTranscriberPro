# Local Transcriber Project History

## Session: July 15, 2026 (v2.1 interface and v2.0 rewrite)

### Status: Release candidate

- Added the playful two-step Simple mode, permanent live tape-recorder VU meter, automatic microphone confirmation and expanded hover help for v2.1.
- Added Simple and Advanced bilingual interfaces.
- Added the complete OpenAI Whisper model catalogue with hardware-aware maximum-quality defaults.
- Added faster-whisper/CTranslate2, MLX and PyTorch compatibility backends.
- Added conference, endless dictation, online video and batch presets.
- Added hardware proof, learned ETA, VTT, improved recovery and secure cache handling.
- Added reproducible Windows, macOS and Linux packaging workflows.
- Archived the v1.1 base as `archive-v1.1-before-v2.0`.

## Session: February 26, 2026 (v1.1 Update)

### **Status: Release v1.1**
Added comprehensive tooltips, exhaustive help manual, and intelligent hardware-based model selection.

### **Version Changelog**
*   **v1.1 (Windows):**
    *   **Auto-Detect Model:** The application now intelligently scans available system RAM and NVIDIA VRAM to automatically recommend and select the most accurate AI model your PC can handle without crashing.
    *   **Comprehensive Tooltips:** Added hover-over pop-up explanations for *every single* button, dropdown, and checkbox in the interface.
    *   **Detailed Manual:** Completely rewrote the internal Help dialog to be an exhaustive, feature-by-feature manual.
    *   **Model Requirements Guidance:** The model selection dropdown now features a detailed tooltip explicitly outlining the hardware requirements for each model tier (Tiny to Large).

## Session: February 25, 2026 (v1.0 Release)

### **Status: Release v1.0**
Comprehensive installer overhaul for absolute maximum compatibility on blank Windows 11 machines.

### **Current Application State**
*   **Desktop App:** Local Transcriber Pro v1.0
*   **Repo:** https://github.com/vhaloo/LocalTranscriberPro

### **Version Changelog**
*   **v1.0 (Windows):**
    *   **Distribution:** `Web_Builder.cmd` rewritten to handle completely blank Windows 11 installations.
    *   **Prerequisites:** Automatically installs Python 3.12, FFmpeg, and Visual C++ Redistributables silently via Winget and official installers.
    *   **Desktop Integration:** Creates a dedicated installation directory (`%USERPROFILE%\Desktop\Local Transcriber Pro`) and a proper `.lnk` shortcut with the correct working directory.
    *   **Stability:** Preserves all advanced features (Speaker Diarization, Smart Subtitles, Auto-Cleanup, Drag & Drop) while ensuring strict build checks (Size > 100MB) before replacing existing installations.
    *   **UX:** Improved logging to Desktop (`LT_Install_Log.txt`) for debugging failed installations.

## Session: February 25, 2026 (CUDA Optimization)

### **Status: v0.9.13 (Dev)**
System verified with CUDA 13.1 support.

### **Current Application State**
*   **Runtime:** `LocalTranscriberPro.exe` detected running (PID 62976).
*   **Resources:** High GPU Usage (~11GB VRAM). 
*   **Goal:** Optimize memory usage and verify CUDA acceleration path.

## Session: January 13, 2026 (Speaker Detection)

### **Status: Release v0.9.12**
Added Speaker Diarization ("Detect Speakers") and critical Mac fixes.

### **Current Application State**
*   **Desktop App:** Local Transcriber Pro v0.9.12
*   **Repo:** https://github.com/vhaloo/LocalTranscriberPro

### **Version Changelog**
*   **v0.9.12 (Desktop):**
    *   **Feature:** **Speaker Detection**. Added a "Detect Speakers" checkbox. Uses `speechbrain` to identify distinct speakers in audio files and tag them (e.g., [Speaker 1]). Best for podcasts/interviews.
    *   **Fix (Mac):** Made Drag-and-Drop optional to prevent crashes on systems where the library fails to load.
    *   **Fix (Mac):** Installer now recursively signs all internal libraries, fixing the "Bounce" crash on Apple Silicon.
    *   **Fix (Mac):** Installer now forces Python 3.12 installation to avoid compatibility issues with 3.13/3.14.

*   **v0.9.11 (Universal):**
    *   **Mac Support:** Full M1/M2/M3/M4/M5 hardware acceleration (Metal/MPS).
    *   **Mac Installer:** Custom `.command` script builds and installs a native `.app` bundle to `/Applications`.
    *   **Stability:** Fixed "Bouncing/Crash" on Mac by correctly handling working directories and code signing.
    *   **Architecture:** Moved internal data (logs, temp files) to `AppData`/`Application Support` for better OS compliance on all platforms.
    *   **Smart Subtitles:** Auto-generated `.srt` files for video inputs.

*   **v0.9.10 (Desktop):**
    *   **Feature:** **Drag & Drop Support**. Drag audio/video files directly into the app window to start batch transcription.
    *   **Compatibility:** Fixed file opening logic to work on macOS (`open`) and Linux (`xdg-open`).
    *   **Compatibility:** Used `os.path.expanduser` for correct Desktop/Documents path detection on non-Windows systems.
    *   **Dependency:** Added `tkinterdnd2` for DnD functionality.

*   **v0.9.9 (Desktop):**
    *   **Feature:** **Autosave to Documents**. Sessions are now automatically saved to `Documents/Transcriptions/` upon completion.
    *   **UX:** Added **pulsating record button** animation to indicate active recording/loading states.
    *   **UX:** Enhanced tooltips and added explanatory labels for model selection and context window.
    *   **Docs:** Completely revamped "Help" dialog with detailed resource usage guide.
    *   **Export:** Added JSON and CSV export options for developers.
    *   **Default:** Context window now defaults to 30s for better coherence.

*   **v0.9.8 (Desktop):**
    *   **Feature:** **YouTube Transcription Tab**. Paste a URL to automatically download audio and generate a transcript/subtitle file.
    *   **Dependency:** Added `yt-dlp` for robust video extraction.
    *   **UI:** Added dedicated tab interface for switching between "General" and "YouTube" modes.

*   **v0.9.7 (Desktop):**
    *   **Fix:** Completely rewritten `Web_Builder.cmd` (v14) with Desktop logging and integrity checks.
    *   **Fix:** Resolved "This app can't run on your PC" error by fixing partial/corrupt builds.
    *   **Fix:** Added missing `tbb` and `numba` DLLs to PyInstaller bundle.
    *   **Fix:** Dynamic detection of `customtkinter` paths during build.
    *   **Compatibility:** Verified support for Python 3.12.

*   **v0.9.6 (Desktop):**
    *   **Feature:** **Universal Subtitle Creator** (Create .srt from any video/audio).
    *   **UI:** Added **Clear Log Button** and **Tooltips** for better UX.
    *   **Distribution:** Switched to `Web_Builder.cmd` for installation (due to GitHub size limits).
    *   **Fixes:** Various bug fixes and stability improvements.

*   **v0.9 (Desktop):**
    *   **Architecture:** Split monolithic code into modular `src/` structure (`gui`, `audio`, `transcriber`, `utils`).
    *   **Feature:** Added **Subtitle Export (.srt)** with timestamp support.
    *   **Feature:** Added **Translation Toggle** (Translate foreign audio to English).
    *   **UI:** Modernized settings layout and status indicators.
    *   **Engine:** Prepared for `faster-whisper` integration (currently fallback to standard `whisper` for compatibility).

*   **v0.8 (Desktop):**
    *   File Transcription & Smart Optimization.
    *   Dynamic Formatting.

### **Technical Notes**
*   **Build:** Updated `build_exe.bat` to handle `src` directory inclusion.
*   **Backup:** Previous v0.8 logic preserved in `local_transcriber_v0.8_backup.py`.
