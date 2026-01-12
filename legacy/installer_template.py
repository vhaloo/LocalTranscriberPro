import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
import threading
import time
import base64
import shutil
import datetime

# Base64 encoded source code
APP_CODE_B64 = "__APP_BASE64__"

# Setup Paths
APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)

VENV_DIR = os.path.join(APP_DIR, "transcriber_env")
APP_FILE = os.path.join(APP_DIR, "local_transcriber.py")
LOG_FILE = os.path.join(APP_DIR, "installer_debug.log")

# Setup Logging
try:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"Installer Log Started: {datetime.datetime.now()}\n")
except: pass

def log_msg(msg):
    # Log to file
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now()} - {msg}\n")
    except: pass
    
    # Log to UI
    try:
        log_text.configure(state="normal")
        log_text.insert("end", str(msg) + "\n")
        log_text.see("end")
        log_text.configure(state="disabled")
        root.update_idletasks()
    except: pass

def run_command(cmd):
    log_msg(f"Running: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log_msg(line.strip())
        process.wait()
    except Exception as e:
        log_msg(f"Command failed: {e}")

def get_compatible_python():
    # 1. Try py launcher
    for ver in ["-3.12", "-3.11", "-3.10"]:
        try:
            cmd = ["py", ver, "-c", "import sys; print(sys.executable)"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                path = res.stdout.strip()
                log_msg(f"Found Python {ver}: {path}")
                return path
        except: pass

    # 2. Try default python
    try:
        cmd = ["python", "-c", "import sys; print(sys.version_info[:2]); print(sys.executable)"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            lines = res.stdout.strip().split('\n')
            ver = eval(lines[0])
            path = lines[1]
            if (3, 10) <= ver <= (3, 12):
                log_msg(f"Default Python {ver} is compatible.")
                return path
    except: pass
    
    return None

def installer_logic():
    progress.start(10)
    
    # 1. Find Python
    lbl_status.config(text="Searching for Python...")
    sys_python = get_compatible_python()
    if not sys_python:
        progress.stop()
        messagebox.showerror("Error", "Python 3.10, 3.11, or 3.12 not found.\nPlease install Python 3.12 from python.org")
        root.quit()
        return

    # 2. Extract App
    lbl_status.config(text="Extracting App...")
    try:
        code = base64.b64decode(APP_CODE_B64).decode('utf-8')
        with open(APP_FILE, "w", encoding="utf-8") as f:
            f.write(code)
        log_msg("App extracted.")
    except Exception as e:
        log_msg(f"Extraction failed: {e}")
        return

    # 3. Venv
    venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        lbl_status.config(text="Creating Virtual Environment...")
        try:
            subprocess.check_call([sys_python, "-m", "venv", VENV_DIR])
            log_msg("Venv created.")
        except Exception as e:
            log_msg(f"Venv creation failed: {e}")
            return

    # 4. Install
    lbl_status.config(text="Installing Dependencies...")
    
    # Upgrade Pip
    subprocess.call([venv_python, "-m", "pip", "install", "--upgrade", "pip", "--no-cache-dir"])
    
    # Install Torch (CUDA)
    lbl_status.config(text="Downloading AI Engine (2GB+)...")
    run_command([venv_python, "-m", "pip", "install", 
                 "torch", "torchvision", "torchaudio", 
                 "--index-url", "https://download.pytorch.org/whl/cu124", 
                 "--no-cache-dir"])
    
    # Install Requirements
    lbl_status.config(text="Installing Libraries...")
    run_command([venv_python, "-m", "pip", "install", 
                 "customtkinter", "sounddevice", "numpy", "scipy", "openai-whisper",
                 "--no-cache-dir"])

    # 5. Launch
    lbl_status.config(text="Launching...")
    log_msg("Starting app...")
    progress.stop()
    
    subprocess.Popen([venv_python, APP_FILE], 
                     cwd=APP_DIR,
                     creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
    
    time.sleep(2)
    root.quit()

def start_thread():
    threading.Thread(target=installer_logic, daemon=True).start()

# --- GUI Setup ---
root = tk.Tk()
root.title("Local Transcriber Setup")
root.geometry("600x450")

tk.Label(root, text="Local Transcriber Pro Setup", font=("Arial", 16)).pack(pady=10)
lbl_status = tk.Label(root, text="Ready...", font=("Arial", 10))
lbl_status.pack(pady=5)

progress = ttk.Progressbar(root, orient="horizontal", length=500, mode="indeterminate")
progress.pack(pady=10)

log_text = tk.Text(root, height=15, width=70, state="disabled", font=("Consolas", 8))
log_text.pack(pady=10)

root.after(500, start_thread)
root.mainloop()
