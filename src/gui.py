import customtkinter as ctk
import threading
import datetime
import os
import sys
import json
import logging
import webbrowser
import numpy as np
import tkinter as tk
from tkinter import messagebox, filedialog

from src.audio import AudioRecorder, SAMPLE_RATE
from src.transcriber import TranscriberEngine, MODEL_SIZES
from src.utils import StdErrRedirector, create_srt_content

APP_VERSION = "v0.9.3"
DEV_CREDIT = "Developed by Vhaloo"

CHUNK_OPTIONS = {
    "5s (Fastest)": 5,
    "10s (Balanced)": 10,
    "15s": 15,
    "20s": 20,
    "30s (Best Context)": 30
}

class HelpDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Quick Guide")
        self.geometry("600x500")
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="Local Transcriber Pro Guide", font=("Roboto Medium", 20)).pack(pady=10)
        
        info = (
            "1. Microphone & Model:\n"
            "   - Select your input device and the AI model size.\n"
            "   - 'Small' is a good balance. 'Large' is best for files.\n\n"
            "2. Recording:\n"
            "   - Press 'Record' or F1 to start.\n"
            "   - The waveform shows your voice input level.\n"
            "   - Text appears in blocks as you speak.\n\n"
            "3. File Transcription:\n"
            "   - Click 'Batch Files' to process audio/video files.\n"
            "   - Supports .mp3, .wav, .mp4, .mkv, and more.\n\n"
            "4. Tools:\n"
            "   - 'Translate': Converts foreign audio to English text.\n"
            "   - 'Auto-Cleanup': Removes repetitive AI errors.\n"
            "   - 'Model Manager': Delete unused models to save space.\n\n"
            "5. Export:\n"
            "   - Save as Text (.txt) or Subtitles (.srt)."
        )
        
        lbl = ctk.CTkLabel(self, text=info, justify="left", font=("Roboto", 14), anchor="w")
        lbl.pack(padx=20, pady=10, fill="both")
        
        ctk.CTkLabel(self, text=DEV_CREDIT, font=("Roboto", 12), text_color="#0984e3").pack(side="bottom", pady=10)

class ModelManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent, engine):
        super().__init__(parent)
        self.title("Model Manager")
        self.geometry("500x400")
        self.engine = engine
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="Downloaded Models (Cache)", font=("Roboto Medium", 16)).pack(pady=10)
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=5)
        self.refresh_list()
        ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=10)

    def refresh_list(self):
        for w in self.scroll.winfo_children(): w.destroy()
        models = self.engine.get_downloaded_models()
        if not models:
            ctk.CTkLabel(self.scroll, text="No models found in cache.").pack(pady=20)
            return
        for m in models:
            row = ctk.CTkFrame(self.scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{m['name']} ({m['size']})", anchor="w").pack(side="left", padx=5)
            ctk.CTkButton(row, text="Delete", fg_color="#d63031", width=60, 
                          command=lambda p=m['path']: self.delete_model(p)).pack(side="right", padx=5)

    def delete_model(self, path):
        if messagebox.askyesno("Confirm", "Delete this model file?\nIt will be re-downloaded if needed."):
            if self.engine.delete_model_file(path):
                self.refresh_list()
            else:
                messagebox.showerror("Error", "Could not delete file.")

class TranscriberApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title(f"Local Transcriber Pro {APP_VERSION}")
        self.geometry("1100x900")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.recorder = AudioRecorder()
        self.engine = TranscriberEngine()
        self.transcription_thread = None
        self.running = True
        
        self.transcript_data = [] 
        self.session_start_time = None
        self.is_loading_model = False
        self.batch_queue = []
        self.backup_file = os.path.join(os.getcwd(), ".unsaved_session.json")

        self.setup_ui()
        self.setup_bindings()
        self.check_recovery()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.update_visualizer()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1) 

        # Header
        self.header_frame = ctk.CTkFrame(self, corner_radius=10)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        h_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        h_box.pack(fill="x", padx=10, pady=10)
        
        # Branding
        title_box = ctk.CTkFrame(h_box, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text=f"Local Transcriber Pro", font=("Roboto Medium", 24)).pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"{APP_VERSION} | {DEV_CREDIT}", font=("Roboto", 12), text_color="#0984e3").pack(anchor="w")
        
        # Header Buttons
        btn_box = ctk.CTkFrame(h_box, fg_color="transparent")
        btn_box.pack(side="right")
        ctk.CTkButton(btn_box, text="Tools", width=80, command=self.open_tools_menu).pack(side="right", padx=5)
        ctk.CTkButton(btn_box, text="Help", width=60, fg_color="gray", hover_color="gray40", command=self.open_help).pack(side="right", padx=5)

        # Settings
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        
        # Row 1
        r1 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(r1, text="Mic:", font=("Roboto", 14)).pack(side="left", padx=5)
        self.device_combo = ctk.CTkComboBox(r1, width=220)
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
        proc_values = ["Auto", "CPU"]
        if self.engine.torch_cuda_available: proc_values.insert(1, "GPU (CUDA)")
        if self.engine.mps_available: proc_values.insert(1, "GPU (MPS)")
        self.proc_combo = ctk.CTkComboBox(r1, values=proc_values, width=120)
        self.proc_combo.set("Auto")
        self.proc_combo.pack(side="left", padx=5)

        if self.engine.cuda_missing:
            ctk.CTkButton(r1, text="⚠️ GPU", fg_color="#e67e22", hover_color="#d35400", 
                          command=lambda: webbrowser.open("https://developer.nvidia.com/cuda-downloads"), width=60).pack(side="right", padx=10)

        # Row 2
        r2 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=5)
        
        self.translate_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(r2, text="Translate (EN)", variable=self.translate_var, font=("Roboto", 12), text_color="#fdcb6e").pack(side="left", padx=5)

        self.cleanup_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r2, text="Auto-Cleanup", variable=self.cleanup_var, font=("Roboto", 12)).pack(side="left", padx=15)

        self.time_fmt_var = ctk.StringVar(value="[HH:MM:SS]")
        ctk.CTkOptionMenu(r2, values=["[HH:MM:SS]", "[MM:SS]", "None"], variable=self.time_fmt_var, command=self.refresh_display, width=110).pack(side="left", padx=(20, 5))
        
        self.layout_var = ctk.StringVar(value="Block")
        ctk.CTkOptionMenu(r2, values=["Block", "Stream"], variable=self.layout_var, command=self.refresh_display, width=110).pack(side="left", padx=5)

        self.open_file_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r2, text="Open Result", variable=self.open_file_var, font=("Roboto", 12)).pack(side="right", padx=10)

        # Visualizer Frame
        self.vis_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", height=60)
        self.vis_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        self.vis_canvas = ctk.CTkCanvas(self.vis_frame, bg="#2b2b2b", highlightthickness=0, height=60)
        self.vis_canvas.pack(fill="both", expand=True)
        
        self.loading_label = ctk.CTkLabel(self.vis_frame, text="", font=("Roboto", 11), text_color="gray")
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")

        # Text Area
        self.textbox = ctk.CTkTextbox(self, font=("Consolas", 14), corner_radius=10)
        self.textbox.grid(row=4, column=0, sticky="nsew", padx=20, pady=10)
        self.textbox.configure(state="disabled")

        # Controls
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=20)
        
        self.hotkey_label = ctk.CTkLabel(self.controls_frame, text="[F1] Record | [F2] Pause | [F3] Stop", font=("Consolas", 11), text_color="gray")
        self.hotkey_label.pack(side="top", pady=(0, 5))

        self.btn_inner = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.btn_inner.pack()

        # Record Buttons
        self.record_btn = ctk.CTkButton(self.btn_inner, text="● Record", fg_color="#d63031", hover_color="#ff7675", width=120, height=45, font=("Roboto", 15, "bold"), command=self.start_recording)
        self.record_btn.pack(side="left", padx=10)

        self.pause_btn = ctk.CTkButton(self.btn_inner, text="❚❚ Pause", fg_color="#e17055", hover_color="#fab1a0", width=100, height=45, font=("Roboto", 15, "bold"), state="disabled", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=10)

        self.stop_btn = ctk.CTkButton(self.btn_inner, text="■ Stop", fg_color="#636e72", hover_color="#b2bec3", width=100, height=45, font=("Roboto", 15, "bold"), state="disabled", command=self.stop_recording)
        self.stop_btn.pack(side="left", padx=10)
        
        # Batch File Button
        self.file_btn = ctk.CTkButton(self.btn_inner, text="📁 Batch Files", fg_color="#0984e3", hover_color="#74b9ff", width=140, height=45, font=("Roboto", 15, "bold"), command=self.transcribe_batch)
        self.file_btn.pack(side="left", padx=(30, 10))

        self.action_menu = ctk.CTkOptionMenu(self.btn_inner, values=["Export...", "Export TXT", "Export SRT", "Save As..."], command=self.perform_export, width=120, height=45, font=("Roboto", 13))
        self.action_menu.set("Export...")
        self.action_menu.pack(side="left", padx=10)

        self.status_bar = ctk.CTkLabel(self, text="Ready", anchor="e", text_color="gray")
        self.status_bar.grid(row=6, column=0, sticky="ew", padx=25, pady=(0, 10))

    def update_visualizer(self):
        if self.running:
            self.vis_canvas.delete("wave")
            
            if self.is_loading_model:
                pass
            elif self.recorder.recording and not self.recorder.paused:
                width = self.vis_canvas.winfo_width()
                height = self.vis_canvas.winfo_height()
                data = self.recorder.wave_data
                points = []
                bar_width = width / len(data)
                mid_y = height / 2
                
                for i, val in enumerate(data):
                    x = i * bar_width
                    amp = val * height * 5 
                    y1 = mid_y - amp
                    y2 = mid_y + amp
                    points.append(x)
                    points.append(y1)
                    points.append(x)
                    points.append(y2)
                
                if points:
                    self.vis_canvas.create_line(points, fill="#00b894", width=2, tag="wave", smooth=True)
            
            self.after(50, self.update_visualizer)

    def open_tools_menu(self):
        ModelManagerDialog(self, self.engine)

    def open_help(self):
        HelpDialog(self)

    def populate_devices(self):
        devices, sel = self.recorder.get_devices()
        self.device_combo.configure(values=devices)
        if sel: self.device_combo.set(sel)
        elif devices: self.device_combo.set(devices[0])

    # --- Core Logic ---
    def start_recording(self):
        if self.is_loading_model: return
        self.set_loading(True, "Initializing Model...")
        self.lock_ui(True)
        try: dev_idx = int(self.device_combo.get().split(":")[0])
        except: dev_idx = 0
        threading.Thread(target=self.init_and_record, args=(dev_idx,), daemon=True).start()

    def init_and_record(self, dev):
        self.redirector = StdErrRedirector(self.update_progress)
        self.redirector.start()
        try:
            self.engine.load_model(self.model_combo.get(), self.proc_combo.get())
            self.session_start_time = datetime.datetime.now()
            self.recorder.start(dev, 10) # 10s chunk
            self.after(0, self.on_rec_start)
            self.transcription_thread = threading.Thread(target=self.process_queue, daemon=True)
            self.transcription_thread.start()
        except Exception as e:
            self.log_sys(f"Error: {e}")
            self.after(0, lambda: self.lock_ui(False))
        finally:
            self.redirector.stop()
            self.after(0, lambda: self.set_loading(False))

    def process_queue(self):
        task = "translate" if self.translate_var.get() else "transcribe"
        while True:
            data = self.recorder.audio_queue.get()
            if data is None: break
            try:
                fp16 = (self.engine.device == "cuda")
                res = self.engine.transcribe_audio(data.flatten(), task=task, fp16=fp16)
                text = res["text"].strip()
                if self.cleanup_var.get(): text = self.engine.cleanup_text(text)
                if text: self.after(0, lambda t=text: self.add_segment(t))
            except Exception as e: logging.error(f"Transcribe fail: {e}")
        self.after(0, lambda: self.status_bar.configure(text="Processing complete."))
        self.after(0, lambda: self.lock_ui(False))

    def transcribe_batch(self):
        if self.is_loading_model: return
        filepaths = filedialog.askopenfilenames(filetypes=[("Media Files", "*.wav *.mp3 *.m4a *.mp4 *.flac *.ogg *.mkv *.mov"), ("All", "*.*")])
        if not filepaths: return
        self.batch_queue = list(filepaths)
        self.set_loading(True, "Preparing batch...")
        self.lock_ui(True)
        threading.Thread(target=self.process_batch_thread, daemon=True).start()

    def process_batch_thread(self):
        self.redirector = StdErrRedirector(self.update_progress)
        self.redirector.start()
        try:
            self.engine.load_model(self.model_combo.get(), self.proc_combo.get())
            task = "translate" if self.translate_var.get() else "transcribe"
            total = len(self.batch_queue)
            for i, filepath in enumerate(self.batch_queue):
                filename = os.path.basename(filepath)
                self.after(0, lambda: self.set_loading(True, f"Processing {i+1}/{total}: {filename}"))
                self.session_start_time = datetime.datetime.now()
                result = self.engine.transcribe_file(filepath, task=task)
                self.after(0, lambda f=filename: self.log_sys(f"--- Start {f} ---"))
                if result and "segments" in result:
                    for segment in result["segments"]:
                        text = segment["text"].strip()
                        if self.cleanup_var.get(): text = self.engine.cleanup_text(text)
                        if text:
                            start = segment['start']
                            end = segment['end']
                            abs_time = self.session_start_time + datetime.timedelta(seconds=start)
                            self.after(0, lambda t=text, time=abs_time, s=start, e=end: self.add_segment(t, time, s, e))
                self.after(0, lambda f=filename: self.log_sys(f"--- End {f} ---"))
                self.after(0, lambda: self.save_txt(ask=False, auto=True))
            self.after(0, lambda: self.log_sys("Batch Complete."))
        except Exception as e:
            self.log_sys(f"Batch Error: {e}")
        finally:
            self.redirector.stop()
            self.after(0, lambda: self.set_loading(False))
            self.after(0, lambda: self.lock_ui(False))

    # --- Helpers ---
    def set_loading(self, show, msg=""):
        self.is_loading_model = show
        self.loading_label.configure(text=msg)

    def update_progress(self, val):
        pass

    def on_rec_start(self):
        self.pause_btn.configure(state="normal", fg_color="#e17055")
        self.stop_btn.configure(state="normal", fg_color="#d63031")
        self.status_bar.configure(text="● Recording...")
        self.log_sys("Session Started.")

    def lock_ui(self, lock):
        state = "disabled" if lock else "normal"
        self.record_btn.configure(state=state)
        self.file_btn.configure(state=state)
        self.device_combo.configure(state=state)
        self.model_combo.configure(state=state)
        if not lock:
            self.pause_btn.configure(state="disabled", text="❚❚ Pause")
            self.stop_btn.configure(state="disabled")

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

    def add_segment(self, text, custom_time=None, start=0.0, end=0.0):
        if not custom_time: custom_time = datetime.datetime.now()
        segment = {'time': custom_time, 'text': text, 'start': start, 'end': end}
        self.transcript_data.append(segment)
        self.save_backup()
        formatted = self.format_segment(segment)
        self.textbox.configure(state="normal")
        self.textbox.insert("end", formatted)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def format_segment(self, segment):
        ts_mode = self.time_fmt_var.get()
        ts_str = ""
        if ts_mode == "[HH:MM:SS]":
            ts_str = f"[{segment['time'].strftime('%H:%M:%S')}] "
        elif ts_mode == "[MM:SS]":
            ts_str = f"[{segment['time'].strftime('%M:%S')}] "
        return f"{ts_str}{segment['text']}\n"

    def refresh_display(self, _=None):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        full_text = "".join(self.format_segment(s) for s in self.transcript_data)
        if not full_text: self.textbox.insert("0.0", "--- Transcript Log ---\n\n")
        else: self.textbox.insert("0.0", full_text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def log_sys(self, msg):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"\n[System] {msg}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def perform_export(self, choice):
        if choice == "Export...": return
        if not self.transcript_data:
            self.log_sys("Nothing to export.")
            self.action_menu.set("Export...")
            return
        if choice == "Export SRT": self.save_srt()
        elif choice == "Export TXT": self.save_txt()
        elif choice == "Save As...": self.save_txt(ask=True)
        self.action_menu.set("Export...")

    def save_txt(self, ask=False, auto=False):
        fname = f"Transcript_{{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}}.txt"
        if ask:
            path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=fname, filetypes=[("Text", "*.txt")])
        else:
            path = os.path.join(os.environ['USERPROFILE'], 'Desktop', fname)
        if path:
            try:
                full_text = "".join(self.format_segment(s) for s in self.transcript_data)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                self.log_sys(f"Saved TXT: {path}")
                if self.open_file_var.get() and not auto: os.startfile(path)
            except Exception as e: self.log_sys(f"Error: {e}")

    def save_srt(self):
        fname = f"Subs_{{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}}.srt"
        path = os.path.join(os.environ['USERPROFILE'], 'Desktop', fname)
        try:
            content = create_srt_content(self.transcript_data)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log_sys(f"Saved SRT: {path}")
            if self.open_file_var.get(): os.startfile(path)
        except Exception as e: self.log_sys(f"Error: {e}")

    def check_recovery(self):
        if os.path.exists(self.backup_file):
            try:
                with open(self.backup_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    for item in data:
                        if isinstance(item.get('time'), str):
                            item['time'] = datetime.datetime.fromisoformat(item['time'])
                        if 'start' not in item: item['start'] = 0.0
                        if 'end' not in item: item['end'] = 0.0
                    self.transcript_data = data
                    self.refresh_display()
                    self.log_sys("⚠️ RECOVERED UNSAVED SESSION")
            except: pass

    def save_backup(self):
        try:
            serializable_data = []
            for item in self.transcript_data:
                entry = item.copy()
                if isinstance(entry['time'], datetime.datetime):
                    entry['time'] = entry['time'].isoformat()
                serializable_data.append(entry)
            with open(self.backup_file, "w", encoding="utf-8") as f:
                json.dump(serializable_data, f)
        except: pass

    def on_close(self):
        self.running = False
        if self.recorder.recording: self.recorder.stop()
        self.destroy()
        sys.exit()

    def setup_bindings(self):
        self.bind("<F1>", lambda e: self.start_recording())
        self.bind("<F2>", lambda e: self.toggle_pause())
        self.bind("<F3>", lambda e: self.stop_recording())