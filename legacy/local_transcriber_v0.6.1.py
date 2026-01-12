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
from tkinter import messagebox, filedialog

# Setup logging
logging.basicConfig(filename='app_debug.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
APP_VERSION = "v0.6.1"

# Model sizes map
MODEL_SIZES = {
    "tiny": "tiny (~75 MB)",
    "base": "base (~145 MB)",
    "small": "small (~461 MB)",
    "medium": "medium (~1.5 GB)",
    "large": "large (~3 GB)"
}
REVERSE_MODEL_MAP = {v: k for k, v in MODEL_SIZES.items()}

# Chunk options (Label -> Seconds)
CHUNK_OPTIONS = {
    "5s (Fastest)": 5,
    "10s (Balanced)": 10,
    "15s": 15,
    "20s": 20,
    "30s (Best Context)": 30
}
REVERSE_CHUNK_MAP = {v: k for k, v in CHUNK_OPTIONS.items()}

class StdErrRedirector:
    """Captures stderr (tqdm progress bars) to update the GUI."""
    def __init__(self, callback):
        self.callback = callback
        self.original_stderr = sys.stderr

    def write(self, buf):
        # Only write to original stderr if it exists (it might be None in pythonw)
        if self.original_stderr:
            self.original_stderr.write(buf)
            
        match = re.search(r'(\d+)%', buf)
        if match:
            try:
                percent = int(match.group(1))
                self.callback(percent / 100.0)
            except:
                pass

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
                device=self.device_index,
                channels=CHANNELS,
                samplerate=SAMPLE_RATE,
                callback=self.audio_callback,
                blocksize=4096 
            )
            self.stream.start()
            logging.info("Stream started successfully")
        except Exception as e:
            logging.error(f"Error starting stream: {e}")
            raise

    def audio_callback(self, indata, frames, time, status):
        if status:
            logging.warning(f"Audio callback status: {status}")
        if self.recording and not self.paused:
            with self.lock:
                self.audio_buffer.append(indata.copy())
                self.buffer_sample_count += frames
                
                # Check if we have enough data for a full chunk
                if self.buffer_sample_count >= self.chunk_duration_samples:
                    # Combine buffered blocks
                    full_data = np.concatenate(self.audio_buffer)
                    
                    # Extract chunk and remainder
                    chunk = full_data[:self.chunk_duration_samples]
                    remainder = full_data[self.chunk_duration_samples:]
                    
                    # Send the full chunk
                    self.audio_queue.put(chunk)
                    
                    # Reset buffer with remainder
                    self.audio_buffer = [remainder] if len(remainder) > 0 else []
                    self.buffer_sample_count = len(remainder)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        # Flush any remaining audio in the buffer
        with self.lock:
            if self.audio_buffer:
                remaining_data = np.concatenate(self.audio_buffer)
                # Only transcribe if there is significant audio left (>0.1s)
                if len(remaining_data) > int(SAMPLE_RATE * 0.1):
                    logging.info(f"Flushing final buffer: {len(remaining_data)} samples")
                    self.audio_queue.put(remaining_data)
                self.audio_buffer = []
                self.buffer_sample_count = 0

class TranscriberApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title(f"Local Transcriber Pro {APP_VERSION}")
        self.geometry("950x800")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.recorder = AudioRecorder()
        self.model = None
        self.model_name = None
        self.transcription_thread = None
        self.running = True
        self.full_transcript = []
        self.session_start_time = None
        self.is_loading_model = False
        self.cuda_missing = False
        self.redirector = None
        self.backup_file = os.path.join(os.getcwd(), ".unsaved_session.txt")

        self.check_hardware_status()
        self.setup_ui()
        self.setup_bindings()
        self.check_recovery()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def check_recovery(self):
        if os.path.exists(self.backup_file):
            try:
                with open(self.backup_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                
                if content:
                    lines = content.split('\n')
                    self.full_transcript = lines
                    self.log_message("\n[System] ⚠️ RECOVERED UNSAVED SESSION FROM PREVIOUS RUN:")
                    for line in lines:
                        self.log_message(line)
                    self.log_message("-" * 40 + "\n")
                    messagebox.showinfo("Session Recovered", "We found an unsaved transcript from a previous session and restored it.")
            except Exception as e:
                logging.error(f"Recovery failed: {e}")

    def append_to_backup(self, text):
        try:
            with open(self.backup_file, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception as e:
            logging.error(f"Backup failed: {e}")

    def clear_backup(self):
        try:
            if os.path.exists(self.backup_file):
                os.remove(self.backup_file)
        except Exception as e:
            logging.error(f"Clear backup failed: {e}")

    def check_hardware_status(self):
        self.has_nvidia_gpu = False
        try:
            subprocess.check_output("nvidia-smi", stderr=subprocess.STDOUT, shell=True)
            self.has_nvidia_gpu = True
        except Exception:
            self.has_nvidia_gpu = False

        self.torch_cuda_available = torch.cuda.is_available()
        self.cuda_missing = self.has_nvidia_gpu and not self.torch_cuda_available

    def setup_bindings(self):
        self.bind("<F1>", lambda event: self.start_recording())
        self.bind("<F2>", lambda event: self.toggle_pause())
        self.bind("<F3>", lambda event: self.stop_recording())

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) 

        # --- 1. Header ---
        self.header_frame = ctk.CTkFrame(self, corner_radius=10)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        self.title_label = ctk.CTkLabel(self.header_frame, text=f"Local Transcriber Pro {APP_VERSION}", font=("Roboto Medium", 24))
        self.title_label.pack(pady=(10, 5))
        
        self.desc_label = ctk.CTkLabel(self.header_frame, text="Secure, local speech-to-text. Configure settings below.", 
                                       font=("Roboto", 12), text_color="gray70")
        self.desc_label.pack(pady=(0, 10))

        # --- 2. Configuration Panel ---
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        
        # Microphone
        ctk.CTkLabel(self.settings_frame, text="Mic:", font=("Roboto", 14)).pack(side="left", padx=(10, 5), pady=10)
        self.device_combo = ctk.CTkComboBox(self.settings_frame, width=220)
        self.device_combo.pack(side="left", padx=5, pady=10)
        self.populate_devices()

        # Model
        ctk.CTkLabel(self.settings_frame, text="Model:", font=("Roboto", 14)).pack(side="left", padx=(10, 5), pady=10)
        self.model_combo = ctk.CTkComboBox(self.settings_frame, values=list(MODEL_SIZES.values()), width=140)
        self.model_combo.set(MODEL_SIZES["small"])
        self.model_combo.pack(side="left", padx=5, pady=10)

        # Chunk Size (Segment)
        ctk.CTkLabel(self.settings_frame, text="Context:", font=("Roboto", 14)).pack(side="left", padx=(10, 5), pady=10)
        self.chunk_combo = ctk.CTkComboBox(self.settings_frame, values=list(CHUNK_OPTIONS.keys()), width=130)
        self.chunk_combo.set("10s (Balanced)")
        self.chunk_combo.pack(side="left", padx=5, pady=10)

        # Processing Unit
        ctk.CTkLabel(self.settings_frame, text="Device:", font=("Roboto", 14)).pack(side="left", padx=(10, 5), pady=10)
        self.proc_combo = ctk.CTkComboBox(self.settings_frame, values=["Auto", "GPU (CUDA)", "CPU"], width=100, command=self.on_device_change)
        self.proc_combo.set("Auto")
        self.proc_combo.pack(side="left", padx=5, pady=10)

        if self.cuda_missing:
            self.fix_cuda_btn = ctk.CTkButton(self.settings_frame, text="⚠️ GPU", fg_color="#e67e22", hover_color="#d35400", 
                                          command=self.open_cuda_help, width=60)
            self.fix_cuda_btn.pack(side="right", padx=10)

        # --- 3. Loading Indicator ---
        self.load_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.load_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(5, 5))
        
        self.loading_label = ctk.CTkLabel(self.load_frame, text="", font=("Roboto", 11), text_color="gray")
        self.loading_label.pack(pady=(0, 2))
        
        self.progress_bar = ctk.CTkProgressBar(self.load_frame, orientation="horizontal", mode="determinate")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", expand=True)
        self.load_frame.grid_remove() 

        # --- 4. Transcript Log ---
        self.textbox = ctk.CTkTextbox(self, font=("Consolas", 14), corner_radius=10)
        self.textbox.grid(row=3, column=0, sticky="nsew", padx=20, pady=10)
        self.textbox.insert("0.0", "--- Transcript Log ---\n\n")
        self.textbox.configure(state="disabled")

        # --- 5. Controls ---
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 20))

        self.hotkey_label = ctk.CTkLabel(self.controls_frame, text="Hotkeys: [F1] Record  |  [F2] Pause  |  [F3] Stop", 
                                         font=("Consolas", 11), text_color="gray")
        self.hotkey_label.pack(side="top", pady=(0, 5))

        self.btn_inner = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.btn_inner.pack()

        self.record_btn = ctk.CTkButton(self.btn_inner, text="● Record", fg_color="#d63031", hover_color="#ff7675", width=140, height=40, font=("Roboto", 16, "bold"), command=self.start_recording)
        self.record_btn.pack(side="left", padx=15)

        self.pause_btn = ctk.CTkButton(self.btn_inner, text="❚❚ Pause", fg_color="#e17055", hover_color="#fab1a0", width=140, height=40, font=("Roboto", 16, "bold"), state="disabled", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=15)

        self.stop_btn = ctk.CTkButton(self.btn_inner, text="■ Stop", fg_color="#636e72", hover_color="#b2bec3", width=140, height=40, font=("Roboto", 16, "bold"), state="disabled", command=self.stop_recording)
        self.stop_btn.pack(side="left", padx=15)

        # Save Mode Menu
        self.save_mode_var = ctk.StringVar(value="Save: Desktop")
        self.save_mode_menu = ctk.CTkOptionMenu(self.btn_inner, values=["Save: Desktop", "Save: Custom...", "Save: Ask"],
                                                command=self.on_save_mode_change, width=140, height=40, font=("Roboto", 14))
        self.save_mode_menu.pack(side="left", padx=15)
        self.custom_save_path = ""

        self.status_bar = ctk.CTkLabel(self, text="Ready (Autosave: Desktop)", anchor="e", text_color="gray")
        self.status_bar.grid(row=5, column=0, sticky="ew", padx=25, pady=(0, 10))

    def on_save_mode_change(self, choice):
        if choice == "Save: Custom...":
            path = filedialog.askdirectory(title="Select Auto-Save Folder")
            if path:
                self.custom_save_path = path
                self.log_message(f"[System] Auto-save folder set to: {path}")
                self.status_bar.configure(text=f"Ready (Autosave: {os.path.basename(path)})")
            else:
                self.save_mode_menu.set("Save: Desktop") # Revert if cancelled
                self.status_bar.configure(text="Ready (Autosave: Desktop)")
        elif choice == "Save: Desktop":
            self.status_bar.configure(text="Ready (Autosave: Desktop)")
        else: # Save: Ask
            self.status_bar.configure(text="Ready (Ask on Stop)")

    def on_device_change(self, choice):
        if choice == "GPU (CUDA)" and not self.torch_cuda_available:
            messagebox.showwarning("Hardware Warning", "CUDA is not available on this system.\nRunning in CPU mode instead.")
            self.proc_combo.set("CPU")

    def open_cuda_help(self):
        webbrowser.open("https://developer.nvidia.com/cuda-downloads")

    def populate_devices(self):
        devices = sd.query_devices()
        input_devices = []
        default_idx = sd.default.device[0]
        default_selection = None
        
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                name = f"{i}: {d['name']}"
                input_devices.append(name)
                if i == default_idx:
                    default_selection = name
                    
        self.device_combo.configure(values=input_devices)
        if default_selection:
            self.device_combo.set(default_selection)
        elif input_devices:
            self.device_combo.set(input_devices[0])

    def log_message(self, message):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", message + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def update_progress(self, val):
        self.after(0, lambda: self._update_progress_gui(val))

    def _update_progress_gui(self, val):
        self.progress_bar.set(val)
        self.loading_label.configure(text=f"Downloading Model... {int(val*100)}%")

    def start_recording(self):
        if self.is_loading_model: return
        selected_device_str = self.device_combo.get()
        if not selected_device_str:
            self.status_bar.configure(text="Error: No microphone selected")
            return
        
        device_index = int(selected_device_str.split(":")[0])
        model_display_name = self.model_combo.get()
        model_name = REVERSE_MODEL_MAP.get(model_display_name, "small")
        
        chunk_display = self.chunk_combo.get()
        chunk_duration = CHUNK_OPTIONS.get(chunk_display, 10)

        proc_mode = self.proc_combo.get()

        self.record_btn.configure(state="disabled", fg_color="#555555")
        self.device_combo.configure(state="disabled")
        self.model_combo.configure(state="disabled")
        self.chunk_combo.configure(state="disabled")
        self.proc_combo.configure(state="disabled")
        self.save_mode_menu.configure(state="disabled")
        
        self.load_frame.grid()
        self.progress_bar.set(0)
        self.loading_label.configure(text="Initializing...")
        
        threading.Thread(target=self.init_and_record, args=(device_index, model_name, proc_mode, chunk_duration), daemon=True).start()

    def init_and_record(self, device_index, model_name, proc_mode, chunk_duration):
        self.is_loading_model = True
        self.redirector = StdErrRedirector(self.update_progress)
        self.redirector.start()
        
        try:
            device_str = "cpu"
            if proc_mode == "GPU (CUDA)":
                device_str = "cuda"
            elif proc_mode == "Auto":
                device_str = "cuda" if torch.cuda.is_available() else "cpu"
            
            if self.model is None or self.model_name != model_name:
                self.after(0, lambda: self.loading_label.configure(text=f"Loading {model_name} on {device_str.upper()}..."))
                self.log_message(f"[System] Loading Whisper model '{model_name}' on {device_str.upper()}...")
                
                self.model = whisper.load_model(model_name, device=device_str)
                self.model_name = model_name
                self.log_message("[System] Model loaded successfully.")

            self.session_start_time = datetime.datetime.now()
            if not self.full_transcript:
                self.full_transcript = []
            
            self.recorder.start(device_index, chunk_duration)
            self.after(0, self.update_ui_recording_started)
            
            self.transcription_thread = threading.Thread(target=self.process_audio_queue, daemon=True)
            self.transcription_thread.start()

        except Exception as e:
            msg = f"[Error] Failed to start: {str(e)}"
            self.log_message(msg)
            logging.error(msg)
            self.after(0, self.reset_ui)
        finally:
            if self.redirector:
                self.redirector.stop()
            self.is_loading_model = False
            self.after(0, lambda: self.load_frame.grid_remove())

    def update_ui_recording_started(self):
        self.pause_btn.configure(state="normal", fg_color="#e17055")
        self.stop_btn.configure(state="normal", fg_color="#d63031")
        self.status_bar.configure(text="● Recording in progress...")
        self.log_message(f"\n>>> Session Started: {self.session_start_time.strftime('%H:%M:%S')}")

    def toggle_pause(self):
        if self.recorder.paused:
            self.recorder.resume()
            self.pause_btn.configure(text="❚❚ Pause", fg_color="#e17055")
            self.status_bar.configure(text="● Recording...")
            self.log_message("[System] Resumed.")
        else:
            self.recorder.pause()
            self.pause_btn.configure(text="▶ Resume", fg_color="#00b894")
            self.status_bar.configure(text="❚❚ Paused")
            self.log_message("[System] Paused.")

    def stop_recording(self):
        self.recorder.stop()
        self.status_bar.configure(text="Stopping & Finalizing...")
        self.recorder.audio_queue.put(None) 

    def process_audio_queue(self):
        while True:
            audio_data = self.recorder.audio_queue.get()
            if audio_data is None: break
            
            flattened_audio = audio_data.flatten()
            try:
                fp16_val = (self.model.device.type == "cuda")
                result = self.model.transcribe(flattened_audio, fp16=fp16_val) 
                text = result["text"].strip()
                if text:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    line = f"[{timestamp}] {text}"
                    self.full_transcript.append(line)
                    self.append_to_backup(line) # Auto-Backup immediately
                    self.after(0, lambda t=line: self.log_message(t))
            except Exception as e:
                logging.error(f"Transcription error: {e}")

        self.after(0, self.perform_save)
        self.after(0, self.reset_ui)

    def perform_save(self):
        if not self.full_transcript:
            self.log_message("[System] No text recorded.")
            return

        mode = self.save_mode_menu.get()
        filename = f"Transcript_{self.session_start_time.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        filepath = None

        if mode == "Save: Ask":
            default_name = f"Transcript_{self.session_start_time.strftime('%Y-%m-%d_%H-%M-%S')}"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialfile=default_name,
                filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")],
                title="Save Transcript As"
            )
        elif mode == "Save: Custom..." and self.custom_save_path:
             filepath = os.path.join(self.custom_save_path, filename)
        else: # Save: Desktop (Default)
             desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
             filepath = os.path.join(desktop, filename)

        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"TRANSCRIPT SESSION\nDate: {self.session_start_time}\nModel: {self.model_name}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write("\n".join(self.full_transcript))
                
                self.log_message(f"\n[System] ✔ Saved to:\n{filepath}")
                self.full_transcript = [] # Clear only after successful save
                self.clear_backup() # Clean up the backup file
                self.log_message("[System] Backup file cleared.")
            except Exception as e:
                self.log_message(f"[Error] Could not save file: {e}")
                messagebox.showerror("Save Error", f"Could not save file:\n{e}")
        else:
            self.log_message("[System] Save cancelled. Text retained in backup.")

    def reset_ui(self):
        self.record_btn.configure(state="normal", fg_color="#d63031")
        self.pause_btn.configure(state="disabled", text="❚❚ Pause", fg_color="#e17055")
        self.stop_btn.configure(state="disabled", fg_color="#636e72")
        self.device_combo.configure(state="normal")
        self.model_combo.configure(state="normal")
        self.chunk_combo.configure(state="normal")
        self.proc_combo.configure(state="normal")
        self.save_mode_menu.configure(state="normal")
        
        # Restore status bar to show current save mode
        mode = self.save_mode_menu.get()
        if mode == "Save: Desktop":
             self.status_bar.configure(text="Ready (Autosave: Desktop)")
        elif mode == "Save: Custom..." and self.custom_save_path:
             self.status_bar.configure(text=f"Ready (Autosave: {os.path.basename(self.custom_save_path)})")
        else:
             self.status_bar.configure(text="Ready (Ask on Stop)")

    def on_close(self):
        self.running = False
        if self.recorder.recording:
            self.recorder.stop()
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = TranscriberApp()
    app.mainloop()