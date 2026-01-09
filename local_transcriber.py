import customtkinter as ctk
import sounddevice as sd
import numpy as np
import threading
import queue
import whisper
import datetime
import os
import sys
import logging
import torch
import subprocess
import webbrowser
import re
import json
from tkinter import messagebox, filedialog

# Setup logging
logging.basicConfig(filename='app_debug.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
APP_VERSION = "v0.7.1"

MODEL_SIZES = {
    "tiny": "tiny (~75 MB)",
    "base": "base (~145 MB)",
    "small": "small (~461 MB)",
    "medium": "medium (~1.5 GB)",
    "large": "large (~3 GB)"
}
REVERSE_MODEL_MAP = {v: k for k, v in MODEL_SIZES.items()}

CHUNK_OPTIONS = {
    "5s (Fastest)": 5,
    "10s (Balanced)": 10,
    "15s": 15,
    "20s": 20,
    "30s (Best Context)": 30
}

class StdErrRedirector:
    def __init__(self, callback):
        self.callback = callback
        self.original_stderr = sys.stderr

    def write(self, buf):
        if self.original_stderr:
            self.original_stderr.write(buf)
        match = re.search(r'(\d+)%', buf)
        if match:
            try:
                self.callback(int(match.group(1)) / 100.0)
            except: pass

    def flush(self):
        if self.original_stderr:
            self.original_stderr.flush()

    def start(self):
        sys.stderr = self

    def stop(self):
        sys.stderr = self.original_stderr

class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.paused = False
        self.audio_queue = queue.Queue()
        self.stream = None
        self.device_index = None
        self.audio_buffer = []
        self.buffer_sample_count = 0
        self.chunk_duration_samples = 0
        self.lock = threading.Lock()

    def start(self, device_index, chunk_duration):
        logging.info(f"Starting recorder on device {device_index} with chunk {chunk_duration}s")
        self.device_index = device_index
        self.chunk_duration_samples = int(SAMPLE_RATE * chunk_duration)
        self.audio_buffer = []
        self.buffer_sample_count = 0
        self.recording = True
        self.paused = False
        try:
            self.stream = sd.InputStream(
                device=self.device_index, channels=CHANNELS, samplerate=SAMPLE_RATE,
                callback=self.audio_callback, blocksize=4096 
            )
            self.stream.start()
        except Exception as e:
            logging.error(f"Error starting stream: {e}")
            raise

    def audio_callback(self, indata, frames, time, status):
        if status: logging.warning(f"Audio status: {status}")
        if self.recording and not self.paused:
            with self.lock:
                self.audio_buffer.append(indata.copy())
                self.buffer_sample_count += frames
                if self.buffer_sample_count >= self.chunk_duration_samples:
                    full_data = np.concatenate(self.audio_buffer)
                    chunk = full_data[:self.chunk_duration_samples]
                    remainder = full_data[self.chunk_duration_samples:]
                    self.audio_queue.put(chunk)
                    self.audio_buffer = [remainder] if len(remainder) > 0 else []
                    self.buffer_sample_count = len(remainder)

    def pause(self): self.paused = True
    def resume(self): self.paused = False
    def stop(self):
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        with self.lock:
            if self.audio_buffer:
                remaining_data = np.concatenate(self.audio_buffer)
                if len(remaining_data) > int(SAMPLE_RATE * 0.1):
                    self.audio_queue.put(remaining_data)
                self.audio_buffer = []
                self.buffer_sample_count = 0

class TranscriberApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Local Transcriber Pro {APP_VERSION}")
        self.geometry("1000x850")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.recorder = AudioRecorder()
        self.model = None
        self.model_name = None
        self.transcription_thread = None
        self.running = True
        
        # Data Storage
        self.transcript_data = [] # List of dicts: {'time': datetime, 'text': str}
        self.session_start_time = None
        self.is_loading_model = False
        self.backup_file = os.path.join(os.getcwd(), ".unsaved_session.json")

        self.check_hardware_status()
        self.setup_ui()
        self.setup_bindings()
        self.check_recovery()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def check_hardware_status(self):
        self.has_nvidia_gpu = False
        try:
            subprocess.check_output("nvidia-smi", stderr=subprocess.STDOUT, shell=True)
            self.has_nvidia_gpu = True
        except: self.has_nvidia_gpu = False
        self.torch_cuda_available = torch.cuda.is_available()
        self.cuda_missing = self.has_nvidia_gpu and not self.torch_cuda_available
        # Check for Apple Silicon (MPS)
        self.mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1) 

        # Header
        self.header_frame = ctk.CTkFrame(self, corner_radius=10)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        ctk.CTkLabel(self.header_frame, text=f"Local Transcriber Pro {APP_VERSION}", font=("Roboto Medium", 24)).pack(pady=(10, 5))
        ctk.CTkLabel(self.header_frame, text="Secure, local speech-to-text with GPU acceleration.", font=("Roboto", 12), text_color="gray70").pack(pady=(0, 10))

        # Settings
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        
        # Row 1: Hardware & Model
        r1 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(r1, text="Mic:", font=("Roboto", 14)).pack(side="left", padx=5)
        self.device_combo = ctk.CTkComboBox(r1, width=200)
        self.device_combo.pack(side="left", padx=5)
        self.populate_devices()

        ctk.CTkLabel(r1, text="Model:", font=("Roboto", 14)).pack(side="left", padx=(15, 5))
        self.model_combo = ctk.CTkComboBox(r1, values=list(MODEL_SIZES.values()), width=140)
        self.model_combo.set(MODEL_SIZES["small"])
        self.model_combo.pack(side="left", padx=5)

        ctk.CTkLabel(r1, text="Context:", font=("Roboto", 14)).pack(side="left", padx=(15, 5))
        self.chunk_combo = ctk.CTkComboBox(r1, values=list(CHUNK_OPTIONS.keys()), width=130)
        self.chunk_combo.set("10s (Balanced)")
        self.chunk_combo.pack(side="left", padx=5)

        ctk.CTkLabel(r1, text="Device:", font=("Roboto", 14)).pack(side="left", padx=(15, 5))
        
        # Dynamic Device List
        proc_values = ["Auto", "CPU"]
        if self.torch_cuda_available:
            proc_values.insert(1, "GPU (CUDA)")
        if self.mps_available:
            proc_values.insert(1, "GPU (MPS)")
            
        self.proc_combo = ctk.CTkComboBox(r1, values=proc_values, width=120, command=self.on_device_change)
        self.proc_combo.set("Auto")
        self.proc_combo.pack(side="left", padx=5)

        # Row 2: Formatting Options (New)
        r2 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(r2, text="Format:", font=("Roboto", 14, "bold")).pack(side="left", padx=5)
        
        # Time Format
        self.time_fmt_var = ctk.StringVar(value="[HH:MM:SS]")
        self.time_fmt_menu = ctk.CTkOptionMenu(r2, values=["[HH:MM:SS]", "[MM:SS]", "None"], 
                                             variable=self.time_fmt_var, command=self.refresh_display, width=120)
        self.time_fmt_menu.pack(side="left", padx=5)

        # Layout Format
        self.layout_var = ctk.StringVar(value="Block (Lines)")
        self.layout_menu = ctk.CTkOptionMenu(r2, values=["Block (Lines)", "Stream (One Line)"], 
                                             variable=self.layout_var, command=self.refresh_display, width=150)
        self.layout_menu.pack(side="left", padx=5)

        # Open File Checkbox
        self.open_file_var = ctk.BooleanVar(value=True)
        self.open_file_chk = ctk.CTkCheckBox(r2, text="Open File", variable=self.open_file_var, font=("Roboto", 12))
        self.open_file_chk.pack(side="right", padx=10)

        # Loading
        self.load_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.load_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=5)
        self.loading_label = ctk.CTkLabel(self.load_frame, text="", font=("Roboto", 11), text_color="gray")
        self.loading_label.pack()
        self.progress_bar = ctk.CTkProgressBar(self.load_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", expand=True)
        self.load_frame.grid_remove()

        # Text Area
        self.textbox = ctk.CTkTextbox(self, font=("Consolas", 14), corner_radius=10)
        self.textbox.grid(row=4, column=0, sticky="nsew", padx=20, pady=10)
        self.textbox.configure(state="disabled")

        # Controls
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=20)
        
        self.btn_inner = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.btn_inner.pack()

        self.record_btn = ctk.CTkButton(self.btn_inner, text="● Record", fg_color="#d63031", hover_color="#ff7675", width=140, height=40, font=("Roboto", 16, "bold"), command=self.start_recording)
        self.record_btn.pack(side="left", padx=15)

        self.pause_btn = ctk.CTkButton(self.btn_inner, text="❚❚ Pause", fg_color="#e17055", hover_color="#fab1a0", width=140, height=40, font=("Roboto", 16, "bold"), state="disabled", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=15)

        self.stop_btn = ctk.CTkButton(self.btn_inner, text="■ Stop", fg_color="#636e72", hover_color="#b2bec3", width=140, height=40, font=("Roboto", 16, "bold"), state="disabled", command=self.stop_recording)
        self.stop_btn.pack(side="left", padx=15)

        # Save Mode
        self.save_mode_var = ctk.StringVar(value="Save: Desktop")
        self.save_mode_menu = ctk.CTkOptionMenu(self.btn_inner, values=["Save: Desktop", "Save: Custom...", "Save: Ask"],
                                                command=self.on_save_mode_change, width=140, height=40, font=("Roboto", 14))
        self.save_mode_menu.pack(side="left", padx=15)
        self.custom_save_path = ""

        self.status_bar = ctk.CTkLabel(self, text="Ready (Autosave: Desktop)", anchor="e", text_color="gray")
        self.status_bar.grid(row=6, column=0, sticky="ew", padx=25, pady=(0, 10))

    def on_device_change(self, choice):
        if choice == "GPU (CUDA)" and not self.torch_cuda_available:
            messagebox.showwarning("Hardware Warning", "CUDA is not available.\nRunning in CPU mode.")
            self.proc_combo.set("CPU")

    def populate_devices(self):
        devices = sd.query_devices()
        input_devices = []
        default_idx = sd.default.device[0]
        sel = None
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                name = f"{i}: {d['name']}"
                input_devices.append(name)
                if i == default_idx: sel = name
        self.device_combo.configure(values=input_devices)
        if sel: self.device_combo.set(sel)
        elif input_devices: self.device_combo.set(input_devices[0])

    # --- Formatting Logic ---
    def format_segment(self, segment):
        """Format a single segment dict {'time': dt, 'text': str} based on current settings."""
        ts_mode = self.time_fmt_var.get()
        layout_mode = self.layout_var.get()
        
        ts_str = ""
        if ts_mode == "[HH:MM:SS]":
            ts_str = f"[{segment['time'].strftime('%H:%M:%S')}] "
        elif ts_mode == "[MM:SS]":
            ts_str = f"[{segment['time'].strftime('%M:%S')}] "
        
        text = segment['text']
        
        if layout_mode == "Stream (One Line)":
            return f"{ts_str}{text} " # Trailing space for stream
        else:
            return f"{ts_str}{text}\n"

    def refresh_display(self, _=None):
        """Re-render the entire text box based on current data and settings."""
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        
        if not self.transcript_data:
            self.textbox.insert("0.0", "--- Transcript Log ---\n\n")
        else:
            full_text = ""
            for seg in self.transcript_data:
                full_text += self.format_segment(seg)
            self.textbox.insert("0.0", full_text)
            
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def add_segment(self, text):
        now = datetime.datetime.now()
        segment = {'time': now, 'text': text}
        self.transcript_data.append(segment)
        self.save_backup()
        
        # Efficient append to UI
        formatted = self.format_segment(segment)
        self.textbox.configure(state="normal")
        self.textbox.insert("end", formatted)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    # --- Backup & Recovery ---
    def check_recovery(self):
        if os.path.exists(self.backup_file):
            try:
                with open(self.backup_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if data:
                    # Convert isoformat string back to datetime
                    for item in data:
                        item['time'] = datetime.datetime.fromisoformat(item['time'])
                    
                    self.transcript_data = data
                    self.refresh_display()
                    self.log_sys("⚠️ RECOVERED UNSAVED SESSION")
                    messagebox.showinfo("Recovered", "Unsaved session restored.")
            except Exception as e:
                logging.error(f"Recovery failed: {e}")

    def save_backup(self):
        try:
            # Serialize datetime
            serializable_data = []
            for item in self.transcript_data:
                serializable_data.append({'time': item['time'].isoformat(), 'text': item['text']})
            
            with open(self.backup_file, "w", encoding="utf-8") as f:
                json.dump(serializable_data, f)
        except: pass

    def clear_backup(self):
        try:
            if os.path.exists(self.backup_file): os.remove(self.backup_file)
        except: pass

    # --- Core Logic ---
    def start_recording(self):
        if self.is_loading_model: return
        self.load_frame.grid()
        self.progress_bar.set(0)
        self.loading_label.configure(text="Initializing...")
        
        dev_idx = int(self.device_combo.get().split(":")[0])
        model_name = REVERSE_MODEL_MAP.get(self.model_combo.get(), "small")
        chunk = CHUNK_OPTIONS.get(self.chunk_combo.get(), 10)
        proc = self.proc_combo.get()
        
        # Disable UI
        self.record_btn.configure(state="disabled")
        self.device_combo.configure(state="disabled")
        self.model_combo.configure(state="disabled")
        
        threading.Thread(target=self.init_and_record, args=(dev_idx, model_name, proc, chunk), daemon=True).start()

    def init_and_record(self, dev, model, proc, chunk):
        self.is_loading_model = True
        self.redirector = StdErrRedirector(self.update_progress)
        self.redirector.start()
        try:
            device = "cpu"
            if proc == "GPU (CUDA)": 
                device = "cuda"
            elif proc == "GPU (MPS)": 
                device = "mps"
            elif proc == "Auto": 
                if torch.cuda.is_available():
                    device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    device = "mps"
                else:
                    device = "cpu"
            
            if self.model is None or self.model_name != model:
                self.after(0, lambda: self.loading_label.configure(text=f"Loading {model} on {device}..."))
                self.model = whisper.load_model(model, device=device)
                self.model_name = model

            self.session_start_time = datetime.datetime.now()
            # New session implies clearing data if it was previously saved, 
            # BUT for safety we append if user didn't clear. 
            # (Simple approach: append to existing) 
            
            self.recorder.start(dev, chunk)
            self.after(0, self.on_rec_start)
            self.transcription_thread = threading.Thread(target=self.process_queue, daemon=True)
            self.transcription_thread.start()
        except Exception as e:
            self.log_sys(f"Error: {e}")
            self.after(0, self.reset_ui)
        finally:
            self.redirector.stop()
            self.is_loading_model = False
            self.after(0, lambda: self.load_frame.grid_remove())

    def process_queue(self):
        while True:
            data = self.recorder.audio_queue.get()
            if data is None: break
            try:
                fp16 = (self.model.device.type == "cuda")
                res = self.model.transcribe(data.flatten(), fp16=fp16)
                text = res["text"].strip()
                if text:
                    self.after(0, lambda t=text: self.add_segment(t))
            except Exception as e:
                logging.error(f"Transcribe fail: {e}")
        
        self.after(0, self.perform_save)
        self.after(0, self.reset_ui)

    def perform_save(self):
        if not self.transcript_data:
            self.log_sys("No text to save.")
            return

        # Generate Full Text based on CURRENT settings
        full_text = ""
        for seg in self.transcript_data:
            full_text += self.format_segment(seg)

        mode = self.save_mode_menu.get()
        fname = f"Transcript_{self.session_start_time.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        
        path = None
        if mode == "Save: Ask":
            path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=fname, filetypes=[("Text", "*.txt")])
        elif mode == "Save: Custom..." and self.custom_save_path:
            path = os.path.join(self.custom_save_path, fname)
        else:
            path = os.path.join(os.environ['USERPROFILE'], 'Desktop', fname)

        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"SESSION: {self.session_start_time}\nMODEL: {self.model_name}\n")
                    f.write("="*60 + "\n\n")
                    f.write(full_text)
                self.log_sys(f"Saved: {path}")
                
                # Auto-open
                if self.open_file_var.get():
                    try:
                        os.startfile(path)
                    except Exception as e:
                        logging.error(f"Could not open file: {e}")

                self.transcript_data = [] # Clear
                self.clear_backup()
                self.refresh_display()
            except Exception as e:
                self.log_sys(f"Save Failed: {e}")
        else:
            self.log_sys("Save Cancelled. Data kept.")

    def on_rec_start(self):
        self.pause_btn.configure(state="normal", fg_color="#e17055")
        self.stop_btn.configure(state="normal", fg_color="#d63031")
        self.status_bar.configure(text="● Recording...")
        self.log_sys("Session Started.")

    def log_sys(self, msg):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"\n[System] {msg}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def update_progress(self, val):
        self.after(0, lambda: self._update_progress_gui(val))
    def _update_progress_gui(self, val):
        self.progress_bar.set(val)
        self.loading_label.configure(text=f"Downloading... {int(val*100)}%")

    def toggle_pause(self):
        if self.recorder.paused:
            self.recorder.resume()
            self.pause_btn.configure(text="❚❚ Pause", fg_color="#e17055")
            self.status_bar.configure(text="● Recording...")
        else:
            self.recorder.pause()
            self.pause_btn.configure(text="▶ Resume", fg_color="#00b894")
            self.status_bar.configure(text="❚❚ Paused")

    def stop_recording(self):
        self.recorder.stop()
        self.status_bar.configure(text="Finalizing...")
        self.recorder.audio_queue.put(None)

    def reset_ui(self):
        self.record_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled", text="❚❚ Pause")
        self.stop_btn.configure(state="disabled")
        self.device_combo.configure(state="normal")
        self.model_combo.configure(state="normal")
        self.on_save_mode_change(self.save_mode_menu.get()) # Restore status bar text

    def on_save_mode_change(self, choice):
        if choice == "Save: Custom...":
            path = filedialog.askdirectory()
            if path:
                self.custom_save_path = path
                self.status_bar.configure(text=f"Ready (Save: {os.path.basename(path)})")
            else:
                self.save_mode_menu.set("Save: Desktop")
                self.status_bar.configure(text="Ready (Save: Desktop)")
        elif choice == "Save: Desktop":
            self.status_bar.configure(text="Ready (Save: Desktop)")
        else:
            self.status_bar.configure(text="Ready (Ask on Stop)")

    def open_cuda_help(self): webbrowser.open("https://developer.nvidia.com/cuda-downloads")
    
    def setup_bindings(self):
        self.bind("<F1>", lambda e: self.start_recording())
        self.bind("<F2>", lambda e: self.toggle_pause())
        self.bind("<F3>", lambda e: self.stop_recording())

    def on_close(self):
        self.running = False
        if self.recorder.recording: self.recorder.stop()
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = TranscriberApp()
    app.mainloop()
