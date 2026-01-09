# Local Transcriber Project History

## Session: January 8, 2026

### **Status: Major Release v0.8**
Added File Transcription capability with smart optimization prompts.

### **Current Application State**
*   **Desktop App:** Local Transcriber Pro v0.8
*   **Mobile App:** Local Transcriber Mobile v0.2
*   **Repo:** https://github.com/vhaloo/LocalTranscriberPro

### **Version Changelog**
*   **v0.8 (Desktop):**
    *   **File Transcription:** Added "Transcribe File" button to process existing audio/video files.
    *   **Smart Optimization:** Automatically suggests upgrading to "Large" model + "30s" context when processing files for maximum accuracy.
    *   **Format:** Supports .wav, .mp3, .m4a, .mp4, .flac, .ogg, .mkv, .mov.
*   **v0.7.1 (Desktop):**
    *   Dynamic Formatting (Block/Stream, Timestamps).
    *   Auto-Open file option.
    *   One-Click Builder.
*   **v0.2 (Mobile):**
    *   Feature parity with Desktop v0.7.

### **Technical Notes**
*   **File Processing:** Uses `model.transcribe(path)` directly, bypassing the real-time audio queue for efficiency on long files.
*   **Threading:** File transcription runs in a background thread to keep UI responsive.