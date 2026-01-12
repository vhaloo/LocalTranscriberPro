# Local Transcriber Project History

## Session: January 12, 2026 (YOLO Mode)

### **Status: Release v0.9.6**
Major update with universal subtitle support and UI improvements.

### **Current Application State**
*   **Desktop App:** Local Transcriber Pro v0.9.6
*   **Repo:** https://github.com/vhaloo/LocalTranscriberPro

### **Version Changelog**
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