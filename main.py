import os
import ssl
import sys
import platform
import certifi
from src.utils import setup_logging
from src.gui import TranscriberApp

# --- Fix 0: macOS Finder Crash Fix (Redirect Stdout/Stderr) ---
# GUI apps launched from Finder have no stdout/stderr. Writing to them causes a crash.
if getattr(sys, 'frozen', False) and platform.system() == "Darwin":
    log_dir = os.path.join(os.path.expanduser("~"), "Library", "Logs", "LocalTranscriberPro")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Redirect stdout/stderr to a log file
    log_file = os.path.join(log_dir, "app_debug.log")
    sys.stdout = open(log_file, "w")
    sys.stderr = sys.stdout

# --- Fix 1: SSL Certificates ---
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# --- Fix 2: macOS Environment (PATH for FFmpeg) ---
if platform.system() == "Darwin":
    # Finder launch doesn't inherit .zshrc/.bashrc PATH.
    # We must explicitly add Homebrew paths to find ffmpeg.
    homebrew_paths = [
        "/opt/homebrew/bin",      # Apple Silicon
        "/usr/local/bin",         # Intel
        os.path.expanduser("~/bin")
    ]
    
    current_path = os.environ.get("PATH", "")
    new_paths = []
    for p in homebrew_paths:
        if p not in current_path and os.path.exists(p):
            new_paths.append(p)
            
    if new_paths:
        # Prepend to ensure we find our tools first
        os.environ["PATH"] = ":".join(new_paths) + ":" + current_path

if __name__ == "__main__":
    setup_logging()
    app = TranscriberApp()
    app.mainloop()