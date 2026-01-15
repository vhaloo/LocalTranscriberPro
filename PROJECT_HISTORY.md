# Local Transcriber Project History

## Session: January 13, 2026 (YouTube Feature)

### **Status: Release v0.9.8**
Added integrated YouTube audio downloading and transcription.

### **Current Application State**
*   **Desktop App:** Local Transcriber Pro v0.9.8
*   **Repo:** https://github.com/vhaloo/LocalTranscriberPro

### **Version Changelog**
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