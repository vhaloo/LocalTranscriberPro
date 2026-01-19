import customtkinter as ctk
import threading
import datetime
import os
import sys
import json
import csv
import logging
import webbrowser
import numpy as np
import subprocess
import platform
import tkinter as tk
from tkinter import messagebox, filedialog

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    class TkinterDnD:
        class DnDWrapper: pass
    DND_FILES = ""

from src.audio import AudioRecorder, SAMPLE_RATE
from src.transcriber import TranscriberEngine, MODEL_SIZES, REVERSE_MODEL_MAP
from src.utils import StdErrRedirector, create_srt_content
from src.tooltip import ToolTip
from src.youtube_utils import download_youtube_audio
from src.diarizer import Diarizer

APP_VERSION = "v0.9.12"
DEV_CREDIT = "Developed by Vhaloo"

CHUNK_OPTIONS = {
    "5s (Fastest)": 5,
    "10s (Balanced)": 10,
    "15s": 15,
    "20s": 20,
    "30s (Best Context)": 30
}

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.wmv', '.m4v'}

class HelpDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Detailed Guide")
        self.geometry("700x700")
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        try:
            x = parent.winfo_x() + 50
            y = parent.winfo_y() + 50
            self.geometry(f"{x}+{y}")
        except: pass
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="Local Transcriber Pro - User Manual", font=("Roboto Medium", 22)).pack(pady=10)
        
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        info = (
            "1. AI Models & Hardware:\n"
            "   - Tiny/Base: Fast, low RAM (<1GB). Good for quick dictation.\n"
            "   - Small: Balanced. Standard for most real-time use.\n"
            "   - Medium: High accuracy. Needs ~5GB RAM.\n"
            "   - Large: Professional accuracy (near perfect). Needs ~8GB+ RAM.\n"
            "     *Note: Large model is slow on CPU. Use NVIDIA GPU for best results.*\n\n"
            "2. Smart Features:\n"
            "   - Detect Speakers: Identifies who is speaking (Speaker 1, Speaker 2).\n"
            "     *Best for interviews/podcasts. Adds processing time.*\n"
            "   - Smart Subtitles: Drag a video to auto-create a .SRT file.\n"
            "   - Auto-Cleanup: Removes repetitive AI hallucinations.\n\n"
            "3. Context Window (30s Default):\n"
            "   - This controls how much 'audio history' the AI sees.\n"
            "   - 30s provides the best sentence coherence and grammar.\n\n"
            "4. YouTube & Files:\n"
            "   - The app downloads video audio automatically.\n"
            "   - Progress bar shows download -> model load -> transcription.\n\n"
            "5. Exporting:\n"
            "   - TXT: Plain text document.\n"
            "   - SRT: Subtitle file for YouTube/VLC (Time-synced).\n"
            "   - JSON/CSV: Structured data for developers/databases.\n"
        )
        lbl = ctk.CTkLabel(scroll, text=info, justify="left", font=("Roboto", 14), anchor="w")
        lbl.pack(padx=10, pady=10, fill="both")
        
        ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=10)

class ModelManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent, engine):
        super().__init__(parent)
        self.title("Model Manager")
        self.geometry("500x400")
        self.engine = engine
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        try:
            x = parent.winfo_x() + 80
            y = parent.winfo_y() + 80
            self.geometry(f"{x}+{y}")
        except: pass
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
        if messagebox.askyesno("Confirm", "Delete this model file?\nIt will be re-downloaded if needed.", parent=self):
            if self.engine.delete_model_file(path):
                self.refresh_list()
            else:
                messagebox.showerror("Error", "Could not delete file.", parent=self)

class ModelAdviceDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_model, on_switch, on_keep):
        super().__init__(parent)
        self.title("Optimization Tip")
        self.geometry("450x250")
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        try:
            x = parent.winfo_x() + 100
            y = parent.winfo_y() + 100
            self.geometry(f"{x}+{y}")
        except: pass
        
        self.on_switch = on_switch
        self.on_keep = on_keep
        
        lbl = ctk.CTkLabel(self, text="For best results with files/videos,\nwe recommend switching to the 'Large' model.", font=("Roboto", 14), justify="center")
        lbl.pack(pady=20, padx=20)
        
        info = ctk.CTkLabel(self, text="Note: 'Large' (~3GB) provides the highest accuracy\nbut requires downloading once and uses more RAM.", text_color="gray", font=("Roboto", 12))
        info.pack(pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        
        ctk.CTkButton(btn_frame, text="Switch to Large (Recommended)", fg_color="#00b894", hover_color="#00cec9", command=self.switch).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text=f"Keep '{current_model}'", fg_color="gray", hover_color="gray40", command=self.keep).pack(side="right", expand=True, padx=5)

    def switch(self):
        self.on_switch()
        self.destroy()

    def keep(self):
        self.on_keep()
        self.destroy()

class TranscriberApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        
        self.title(f"Local Transcriber Pro {APP_VERSION}")
        self.geometry("1100x950")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Drag and Drop
        self.TkdndVersion = None
        if HAS_DND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception as e:
                logging.error(f"DnD Init Failed: {e}")
        
        self.recorder = AudioRecorder()
        self.engine = TranscriberEngine()
        self.diarizer = Diarizer()
        self.transcription_thread = None
        self.running = True
        self.animate_id = None
        
        self.transcript_data = [] 
        self.session_start_time = None
        self.is_loading_model = False
        self.batch_queue = []
        self.full_audio_buffer = [] # Store raw audio for Diarization
        self.backup_file = os.path.join(os.getcwd(), ".unsaved_session.json")
        self.advice_given = False
        
        # Autosave setup (Cross-platform)
        self.autosave_dir = os.path.join(os.path.expanduser("~"), "Documents", "Transcriptions")
        if not os.path.exists(self.autosave_dir): os.makedirs(self.autosave_dir)

        self.setup_ui()
        self.setup_bindings()
        self.setup_dnd()
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
        
        title_box = ctk.CTkFrame(h_box, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text=f"Local Transcriber Pro", font=("Roboto Medium", 24)).pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"{APP_VERSION} | {DEV_CREDIT}", font=("Roboto", 12), text_color="#0984e3").pack(anchor="w")
        
        btn_box = ctk.CTkFrame(h_box, fg_color="transparent")
        btn_box.pack(side="right")
        
        self.tools_btn = ctk.CTkButton(btn_box, text="Tools", width=80, command=self.open_tools_menu)
        self.tools_btn.pack(side="right", padx=5)
        ToolTip(self.tools_btn, "Manage AI models and disk space")
        
        self.help_btn = ctk.CTkButton(btn_box, text="Help", width=60, fg_color="gray", hover_color="gray40", command=self.open_help)
        self.help_btn.pack(side="right", padx=5)
        ToolTip(self.help_btn, "View detailed manual")

        # Tabview for Modes
        self.tab_view = ctk.CTkTabview(self, height=100, command=self.on_tab_change)
        self.tab_view.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        self.tab_view.add("General")
        self.tab_view.add("YouTube")
        
        # --- General Tab (Settings) ---
        gen_tab = self.tab_view.tab("General")
        
        r1 = ctk.CTkFrame(gen_tab, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(r1, text="Mic:", font=("Roboto", 14)).pack(side="left", padx=5)
        self.device_combo = ctk.CTkComboBox(r1, width=220)
        self.device_combo.pack(side="left", padx=5)
        self.populate_devices()

        ctk.CTkLabel(r1, text="Model:", font=("Roboto", 14)).pack(side="left", padx=(15, 5))
        self.model_combo = ctk.CTkComboBox(r1, values=list(MODEL_SIZES.values()), width=140)
        self.model_combo.set(MODEL_SIZES["small"])
        self.model_combo.pack(side="left", padx=5)
        ToolTip(self.model_combo, "Select AI model size. Bigger = Slower but more Accurate.")

        ctk.CTkLabel(r1, text="Context:", font=("Roboto", 14)).pack(side="left", padx=(15, 5))
        self.chunk_combo = ctk.CTkComboBox(r1, values=list(CHUNK_OPTIONS.keys()), width=130)
        self.chunk_combo.set("30s (Best Context)") 
        self.chunk_combo.pack(side="left", padx=5)
        ToolTip(self.chunk_combo, "Larger context (30s) helps AI understand full sentences better.")

        ctk.CTkLabel(r1, text="Device:", font=("Roboto", 14)).pack(side="left", padx=(15, 5))
        proc_values = ["Auto", "CPU"]
        if self.engine.torch_cuda_available: proc_values.insert(1, "GPU (CUDA)")
        if self.engine.mps_available: proc_values.insert(1, "GPU (MPS)")
        self.proc_combo = ctk.CTkComboBox(r1, values=proc_values, width=120)
        self.proc_combo.set("Auto")
        self.proc_combo.pack(side="left", padx=5)

        # Explanatory Sub-labels
        r1_sub = ctk.CTkFrame(gen_tab, fg_color="transparent", height=15)
        r1_sub.pack(fill="x", padx=10)
        ctk.CTkLabel(r1_sub, text="Tip: Use 'Large' model for complex audio (requires 8GB RAM).", font=("Roboto", 10), text_color="gray").pack(side="left", padx=5)

        # Row 2 (General)
        r2 = ctk.CTkFrame(gen_tab, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=5)
        
        self.translate_var = ctk.BooleanVar(value=False)
        t_chk = ctk.CTkCheckBox(r2, text="Translate (EN)", variable=self.translate_var, font=("Roboto", 12), text_color="#fdcb6e")
        t_chk.pack(side="left", padx=5)

        self.cleanup_var = ctk.BooleanVar(value=True)
        c_chk = ctk.CTkCheckBox(r2, text="Auto-Cleanup", variable=self.cleanup_var, font=("Roboto", 12))
        c_chk.pack(side="left", padx=15)

        self.diarization_var = ctk.BooleanVar(value=False)
        d_chk = ctk.CTkCheckBox(r2, text="Detect Speakers", variable=self.diarization_var, font=("Roboto", 12), text_color="#00cec9")
        d_chk.pack(side="left", padx=15)
        ToolTip(d_chk, "Identify different speakers (Speaker 1, Speaker 2...). Best for files/YouTube.")

        self.time_fmt_var = ctk.StringVar(value="[HH:MM:SS]")
        time_menu = ctk.CTkOptionMenu(r2, values=["[HH:MM:SS]", "[MM:SS]", "None"], variable=self.time_fmt_var, command=self.refresh_display, width=110)
        time_menu.pack(side="left", padx=(20, 5))
        ToolTip(time_menu, "Timestamp style for the log window.")
        
        self.layout_var = ctk.StringVar(value="Block")
        layout_menu = ctk.CTkOptionMenu(r2, values=["Block", "Stream"], variable=self.layout_var, command=self.refresh_display, width=110)
        layout_menu.pack(side="left", padx=5)
        ToolTip(layout_menu, "Block: Paragraphs (Better reading). Stream: Continuous lines.")

        self.open_file_var = ctk.BooleanVar(value=True)
        open_chk = ctk.CTkCheckBox(r2, text="Open Result", variable=self.open_file_var, font=("Roboto", 12))
        open_chk.pack(side="right", padx=10)

        # --- YouTube Tab ---
        yt_tab = self.tab_view.tab("YouTube")
        yt_frame = ctk.CTkFrame(yt_tab, fg_color="transparent")
        yt_frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(yt_frame, text="YouTube URL:", font=("Roboto", 14)).pack(side="left", padx=5)
        self.yt_url_entry = ctk.CTkEntry(yt_frame, width=400, placeholder_text="Paste link here (https://www.youtube.com/watch?v=...)")
        self.yt_url_entry.pack(side="left", padx=10, fill="x", expand=True)
        self.yt_btn = ctk.CTkButton(yt_frame, text="Download & Transcribe", fg_color="#c4302b", hover_color="#e62e2d", command=self.start_youtube_process)
        self.yt_btn.pack(side="left", padx=10)

        # Visualizer Frame & Clear Button
        self.vis_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", height=70)
        self.vis_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        
        self.clear_btn = ctk.CTkButton(self.vis_frame, text="\U0001f5d1️ Clear Log", width=80, height=30, 
                                       fg_color="#444", hover_color="#666", command=self.clear_log)
        self.clear_btn.place(relx=0.95, rely=0.5, anchor="center")
        
        self.loading_label = ctk.CTkLabel(self.vis_frame, text="", font=("Roboto", 12), text_color="#dfe6e9")
        self.loading_label.place(relx=0.5, rely=0.3, anchor="center")

        self.progress_bar = ctk.CTkProgressBar(self.vis_frame, width=400, height=10, progress_color="#00b894")
        self.progress_bar.place(relx=0.5, rely=0.7, anchor="center")
        self.progress_bar.set(0)
        self.progress_bar.place_forget()

        self.vis_canvas = ctk.CTkCanvas(self.vis_frame, bg="#2b2b2b", highlightthickness=0, height=70)
        self.vis_canvas.pack(fill="both", expand=True, padx=(0, 100))
        
        # Text Area
        self.textbox = ctk.CTkTextbox(self, font=("Consolas", 14), corner_radius=10)
        self.textbox.grid(row=4, column=0, sticky="nsew", padx=20, pady=10)
        self.textbox.configure(state="disabled")
        try: self.textbox._textbox.tag_config("alert", foreground="#ff5555", font=("Consolas", 14, "bold"))
        except: pass

        # Controls
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=20)
        
        self.hotkey_label = ctk.CTkLabel(self.controls_frame, text="[F1] Record | [F2] Pause | [F3] Stop", font=("Consolas", 11), text_color="gray")
        self.hotkey_label.pack(side="top", pady=(0, 5))

        self.btn_inner = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.btn_inner.pack()

        self.record_btn = ctk.CTkButton(self.btn_inner, text="● Record", fg_color="#d63031", hover_color="#ff7675", width=120, height=45, font=("Roboto", 15, "bold"), command=self.start_recording)
        self.record_btn.pack(side="left", padx=10)
        
        self.pause_btn = ctk.CTkButton(self.btn_inner, text="❚❚ Pause", fg_color="#e17055", hover_color="#fab1a0", width=100, height=45, font=("Roboto", 15, "bold"), state="disabled", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=10)
        
        self.stop_btn = ctk.CTkButton(self.btn_inner, text="■ Stop", fg_color="#636e72", hover_color="#b2bec3", width=100, height=45, font=("Roboto", 15, "bold"), state="disabled", command=self.stop_recording)
        self.stop_btn.pack(side="left", padx=10)
        
        self.file_btn = ctk.CTkButton(self.btn_inner, text="📁 Batch Files", fg_color="#0984e3", hover_color="#74b9ff", width=140, height=45, font=("Roboto", 15, "bold"), command=self.transcribe_batch)
        self.file_btn.pack(side="left", padx=(30, 10))
        
        self.action_menu = ctk.CTkOptionMenu(self.btn_inner, 
                                             values=["Export...", "Export TXT", "Export SRT", "Export JSON", "Export CSV", "Save As...", "Set Autosave Folder"],
                                             command=self.perform_export, width=120, height=45, font=("Roboto", 13))
        self.action_menu.set("Export...")
        self.action_menu.pack(side="left", padx=10)
        
        self.status_bar = ctk.CTkLabel(self, text="Ready", anchor="e", text_color="gray")
        self.status_bar.grid(row=6, column=0, sticky="ew", padx=25, pady=(0, 10))

    # --- Cross-Platform Helpers ---
    def open_file_safe(self, path):
        """Cross-platform file opener."""
        try:
            if platform.system() == 'Windows':
                os.startfile(path)
            elif platform.system() == 'Darwin':
                subprocess.call(['open', path])
            else: # Linux
                subprocess.call(['xdg-open', path])
        except Exception as e:
            self.log_sys(f"Could not open file: {e}")

    # --- Drag & Drop ---
    def setup_dnd(self):
        if not self.TkdndVersion: return
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.drop_files)

    def drop_files(self, event):
        if self.is_loading_model: return
        raw_files = event.data
        if not raw_files: return
        
        files = self.parse_tcl_list(raw_files)
        if files:
            self.check_model_advice()
            self.batch_queue = files
            self.set_loading(True, "Processing dropped files...")
            self.lock_ui(True)
            threading.Thread(target=self.process_batch_thread, daemon=True).start()

    def parse_tcl_list(self, raw_str):
        files = []
        current = ""
        in_brace = False
        for char in raw_str:
            if char == '{': in_brace = True
            elif char == '}': in_brace = False
            elif char == ' ' and not in_brace:
                if current: files.append(current)
                current = ""
            else: current += char
        if current: files.append(current)
        return [f.strip('{}') for f in files]

    # --- Visualizer & Animations ---
    def update_visualizer(self):
        if self.running:
            if self.is_loading_model: 
                self.vis_canvas.pack_forget()
                self.progress_bar.place(relx=0.5, rely=0.7, anchor="center")
                self.loading_label.place(relx=0.5, rely=0.3, anchor="center")
            else:
                self.progress_bar.place_forget()
                self.loading_label.place_forget()
                if not self.vis_canvas.winfo_ismapped():
                    self.vis_canvas.pack(fill="both", expand=True, padx=(0, 100))
                
                self.vis_canvas.delete("wave")
                if self.recorder.recording and not self.recorder.paused:
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

    def pulsate_record_btn(self):
        if not self.running: return
        if self.is_loading_model:
            current = self.record_btn.cget("fg_color")
            next_col = "#e17055" if current == "#fab1a0" else "#fab1a0"
            self.record_btn.configure(fg_color=next_col, text="● Loading...")
            self.animate_id = self.after(500, self.pulsate_record_btn)
        elif self.recorder.recording and not self.recorder.paused:
            current = self.record_btn.cget("fg_color")
            next_col = "#d63031" if current == "#ff7675" else "#ff7675"
            self.record_btn.configure(fg_color=next_col, text="● Recording")
            self.animate_id = self.after(800, self.pulsate_record_btn)
        else:
            self.record_btn.configure(fg_color="#d63031", text="● Record")
            self.animate_id = None

    def on_tab_change(self):
        if self.tab_view.get() == "YouTube" and not self.advice_given:
            self.check_model_advice()

    def check_model_advice(self):
        current_model = REVERSE_MODEL_MAP.get(self.model_combo.get(), "small")
        if current_model != "large":
            ModelAdviceDialog(self, self.model_combo.get(), 
                              on_switch=lambda: self.model_combo.set(MODEL_SIZES["large"]),
                              on_keep=lambda: None)
            self.advice_given = True 

    # --- Progress & Logging ---
    def set_loading(self, show, msg=""):
        self.is_loading_model = show
        self.loading_label.configure(text=msg)
        if show:
            if not self.animate_id: self.pulsate_record_btn()
        else:
            if not self.recorder.recording:
                self.record_btn.configure(fg_color="#d63031", text="● Record")
            self.progress_bar.set(0)

    def update_progress(self, val):
        self.progress_bar.set(val)

    def log_sys(self, msg):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"\n[System] {msg}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    # --- YouTube Logic ---
    def start_youtube_process(self):
        url = self.yt_url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a valid YouTube URL.")
            return
        
        self.set_loading(True, "Initializing YouTube Process...")
        self.lock_ui(True)
        self.yt_btn.configure(state="disabled")
        threading.Thread(target=self.process_youtube_thread, args=(url,), daemon=True).start()

    def process_youtube_thread(self, url):
        self.redirector = StdErrRedirector(self.update_progress)
        self.redirector.start()
        try:
            temp_dir = os.path.join(os.getcwd(), "temp_downloads")
            if not os.path.exists(temp_dir): os.makedirs(temp_dir)
            
            self.after(0, lambda: self.log_sys("Step 1/3: Downloading audio from YouTube..."))
            self.after(0, lambda: self.set_loading(True, "Downloading Audio (0%)..."))
            
            def dl_progress(pct):
                self.after(0, lambda: self.set_loading(True, f"Downloading Audio ({pct:.1f}%)..."))
                self.after(0, lambda: self.update_progress(pct / 100.0))

            audio_file = download_youtube_audio(url, temp_dir, dl_progress)
            self.after(0, lambda: self.log_sys(f"Download complete: {os.path.basename(audio_file)}"))

            self.after(0, lambda: self.set_loading(True, "Step 2/3: Loading AI Model (May take ~1 min)..."))
            self.engine.load_model(self.model_combo.get(), self.proc_combo.get())
            
            task = "translate" if self.translate_var.get() else "transcribe"
            self.after(0, lambda: self.set_loading(True, "Step 3/3: Transcribing (Please wait)..."))
            self.after(0, lambda: self.log_sys("Step 3/3: Transcribing..."))
            self.session_start_time = datetime.datetime.now()
            
            result = self.engine.transcribe_file(audio_file, task=task, verbose=False)
            
            if result and "segments" in result:
                # Optional Diarization
                if self.diarization_var.get():
                    self.after(0, lambda: self.set_loading(True, "Step 4/4: Detecting Speakers (Diarization)..."))
                    self.after(0, lambda: self.log_sys("Step 4/4: Analyzing voices..."))
                    result['segments'] = self.diarizer.process(audio_file, result['segments'], callback=self.log_sys)

                for segment in result["segments"]:
                    text = segment["text"].strip()
                    if self.cleanup_var.get(): text = self.engine.cleanup_text(text)
                    if text:
                        start = segment['start']
                        end = segment['end']
                        abs_time = self.session_start_time + datetime.timedelta(seconds=start)
                        self.after(0, lambda t=text, time=abs_time, s=start, e=end: self.add_segment(t, time, s, e))
                    
                    # Generate side-by-side SRT for videos
                    self.save_smart_subtitle(audio_file, result["segments"])

            self.after(0, lambda: self.log_sys("✅ Transcription Complete."))
            self.after(0, lambda: self.autosave_all())
            
            try: os.remove(audio_file)
            except: pass

        except Exception as e:
            self.log_sys(f"YouTube Error: {e}")
        finally:
            self.redirector.stop()
            self.after(0, lambda: self.set_loading(False))
            self.after(0, lambda: self.lock_ui(False))
            self.after(0, lambda: self.yt_btn.configure(state="normal"))

    # --- Batch Logic ---
    def transcribe_batch(self):
        if self.is_loading_model: return
        self.check_model_advice()
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
            self.after(0, lambda: self.set_loading(True, "Loading AI Model..."))
            self.engine.load_model(self.model_combo.get(), self.proc_combo.get())
            task = "translate" if self.translate_var.get() else "transcribe"
            total = len(self.batch_queue)
            
            for i, filepath in enumerate(self.batch_queue):
                filename = os.path.basename(filepath)
                self.after(0, lambda: self.set_loading(True, f"Processing {i+1}/{total}: {filename}"))
                self.after(0, lambda: self.log_sys(f"--- Processing {i+1}/{total}: {filename} ---"))
                
                self.session_start_time = datetime.datetime.now()
                result = self.engine.transcribe_file(filepath, task=task, verbose=False)
                
                # Smart Subtitle Generation
                if result and "segments" in result:
                    # Optional Diarization
                    if self.diarization_var.get():
                        self.after(0, lambda: self.set_loading(True, "Detecting Speakers..."))
                        self.after(0, lambda: self.log_sys("Analysing voices (Diarization)..."))
                        result['segments'] = self.diarizer.process(filepath, result['segments'], callback=self.log_sys)

                    # Generate autosave/UI segments
                    for segment in result["segments"]:
                        text = segment["text"].strip()
                        if self.cleanup_var.get(): text = self.engine.cleanup_text(text)
                        if text:
                            start = segment['start']
                            end = segment['end']
                            abs_time = self.session_start_time + datetime.timedelta(seconds=start)
                            self.after(0, lambda t=text, time=abs_time, s=start, e=end: self.add_segment(t, time, s, e))
                    
                    # Generate side-by-side SRT for videos
                    self.save_smart_subtitle(filepath, result["segments"])

                self.after(0, lambda: self.autosave_all())
            
            self.after(0, lambda: self.log_sys("✅ Batch Processing Complete."))
        except Exception as e: 
            self.log_sys(f"Batch Error: {e}")
        finally:
            self.redirector.stop()
            self.after(0, lambda: self.set_loading(False))
            self.after(0, lambda: self.lock_ui(False))

    def save_smart_subtitle(self, filepath, segments):
        """Creates a .srt file next to the video if it's a known video format."""
        try:
            ext = os.path.splitext(filepath)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                srt_path = os.path.splitext(filepath)[0] + ".srt"
                content = create_srt_content(segments)
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.after(0, lambda: self.log_sys(f"\U0001f4f9 Smart Subtitle created: {os.path.basename(srt_path)}"))
        except Exception as e:
            logging.error(f"Smart Subtitle Error: {e}")

    # --- Core Logic & Helpers ---
    def populate_devices(self):
        devices, sel = self.recorder.get_devices()
        self.device_combo.configure(values=devices)
        if sel: self.device_combo.set(sel)
        elif devices: self.device_combo.set(devices[0])

    def clear_log(self):
        if messagebox.askyesno("Clear Log", "Are you sure you want to clear the transcript?"):
            self.transcript_data = []
            self.refresh_display()
            self.log_sys("Log cleared.")

    def open_tools_menu(self): ModelManagerDialog(self, self.engine)
    def open_help(self): HelpDialog(self)

    def start_recording(self):
        if self.is_loading_model: return
        self.set_loading(True, "Initializing Model (~30s)...")
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
            self.full_audio_buffer = [] # Reset buffer
            chunk_s = CHUNK_OPTIONS.get(self.chunk_combo.get(), 30)
            self.recorder.start(dev, chunk_s) 
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
            
            # Store data for Diarization
            self.full_audio_buffer.append(data.copy())
            
            try:
                fp16 = (self.engine.device == "cuda")
                res = self.engine.transcribe_audio(data.flatten(), task=task, fp16=fp16)
                text = res["text"].strip()
                if self.cleanup_var.get(): text = self.engine.cleanup_text(text)
                
                # Calculate start/end relative to session start
                # Assuming simple concatenation of chunks
                current_duration = sum(len(c) for c in self.full_audio_buffer[:-1]) / SAMPLE_RATE
                chunk_len = len(data) / SAMPLE_RATE
                
                if text: 
                    self.after(0, lambda t=text, s=current_duration, e=current_duration+chunk_len: self.add_segment(t, start=s, end=e))
            except Exception as e: logging.error(f"Transcribe fail: {e}")
        
        # Recording Stopped - Post Process
        self.after(0, self.post_process_recording)

    def post_process_recording(self):
        self.status_bar.configure(text="Processing complete.")
        
        # Run Diarization if enabled
        if self.diarization_var.get() and self.full_audio_buffer and sf:
            try:
                self.set_loading(True, "Finalizing: Detecting Speakers...")
                self.log_sys("--- Analyzing recorded session for speakers ---")
                
                # Save temp file
                temp_wav = os.path.join(os.getcwd(), "temp_rec_session.wav")
                full_audio = np.concatenate(self.full_audio_buffer)
                
                # Convert float32 to PCM_16 for compatibility if needed, but sf handles it
                sf.write(temp_wav, full_audio, SAMPLE_RATE)
                
                # Process
                # We need to construct a 'segments' list from our transcript_data that matches this session
                # Filter transcript_data to only include items from this session (based on time?)
                # Simplification: Assume transcript_data is mostly from this session if clear was clicked, 
                # or just process the last N segments.
                # Better: Filter by session_start_time
                
                session_segments = []
                indices = []
                for i, seg in enumerate(self.transcript_data):
                    if seg['time'] >= self.session_start_time:
                        session_segments.append(seg)
                        indices.append(i)
                
                if session_segments:
                    updated_segments = self.diarizer.process(temp_wav, session_segments, callback=self.log_sys)
                    
                    # Update main list
                    for idx, updated in zip(indices, updated_segments):
                        self.transcript_data[idx] = updated
                    
                    self.refresh_display()
                    self.log_sys("✅ Speaker detection applied.")
                
                try: os.remove(temp_wav)
                except: pass
                
            except Exception as e:
                self.log_sys(f"Diarization Error: {e}")
            finally:
                self.set_loading(False)
        elif self.diarization_var.get() and not sf:
             self.log_sys("Error: 'soundfile' library missing. Cannot process recording.")

        self.lock_ui(False)
        self.autosave_all()

    def on_rec_start(self):
        self.pause_btn.configure(state="normal", fg_color="#e17055")
        self.stop_btn.configure(state="normal", fg_color="#d63031")
        self.status_bar.configure(text="● RECORDING...")
        self.textbox.configure(state="normal")
        self.textbox.insert("end", "\n[System] ", "default")
        self.textbox.insert("end", "!!! RECORDING AND TRANSCRIBING !!!\n", "alert")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")
        self.pulsate_record_btn()

    def lock_ui(self, lock):
        state = "disabled" if lock else "normal"
        self.record_btn.configure(state=state)
        self.file_btn.configure(state=state)
        self.device_combo.configure(state=state)
        self.model_combo.configure(state=state)
        self.yt_btn.configure(state=state)
        if not lock:
            self.pause_btn.configure(state="disabled", text="❚❚ Pause")
            self.stop_btn.configure(state="disabled")

    def toggle_pause(self):
        if self.recorder.paused:
            self.recorder.resume()
            self.pause_btn.configure(text="❚❚ Pause", fg_color="#e17055")
            self.status_bar.configure(text="● Recording...")
            self.pulsate_record_btn() 
        else:
            self.recorder.pause()
            self.pause_btn.configure(text="▶ Resume", fg_color="#00b894")
            self.status_bar.configure(text="❚❚ Paused")
            if self.animate_id: self.after_cancel(self.animate_id) 
            self.record_btn.configure(fg_color="#d63031", text="● Record") 

    def stop_recording(self):
        self.recorder.stop()
        self.status_bar.configure(text="Finalizing...")
        self.recorder.audio_queue.put(None)
        if self.animate_id: self.after_cancel(self.animate_id)
        self.record_btn.configure(fg_color="#d63031", text="● Record")

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
        if self.layout_var.get() == "Block":
            ts_str = ""
            if ts_mode == "[HH:MM:SS]":
                ts_str = f"[{segment['time'].strftime('%H:%M:%S')}] "
            elif ts_mode == "[MM:SS]":
                ts_str = f"[{segment['time'].strftime('%M:%S')}] "
            return f"{ts_str}{segment['text']}\n"
        else: 
            return f"{segment['text']} "

    def refresh_display(self, _=None):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        full_text = "".join(self.format_segment(s) for s in self.transcript_data)
        if not full_text: self.textbox.insert("0.0", "--- Transcript Log ---\n\n")
        else: self.textbox.insert("0.0", full_text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def perform_export(self, choice):
        if choice == "Export...": return
        if choice == "Set Autosave Folder":
            self.change_autosave_folder()
            self.action_menu.set("Export...")
            return
            
        if not self.transcript_data:
            self.log_sys("Nothing to export.")
            self.action_menu.set("Export...")
            return
            
        if choice == "Export SRT": self.save_srt()
        elif choice == "Export TXT": self.save_txt()
        elif choice == "Export JSON": self.save_json()
        elif choice == "Export CSV": self.save_csv()
        elif choice == "Save As...": self.save_txt(ask=True)
        self.action_menu.set("Export...")

    def autosave_all(self):
        """Autosaves to the designated Documents folder."""
        if not self.transcript_data: return
        try:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            base = os.path.join(self.autosave_dir, f"Autosave_{timestamp}")
            
            full_text = "".join(self.format_segment(s) for s in self.transcript_data)
            with open(base + ".txt", "w", encoding="utf-8") as f: f.write(full_text)
            
            serializable = []
            for item in self.transcript_data:
                entry = item.copy()
                if isinstance(entry['time'], datetime.datetime): entry['time'] = entry['time'].isoformat()
                serializable.append(entry)
            with open(base + ".json", "w", encoding="utf-8") as f: json.dump(serializable, f, indent=4)
            
            self.log_sys(f"\U0001f4be Session Autosaved to: {self.autosave_dir}")
        except Exception as e:
            self.log_sys(f"Autosave failed: {e}")

    def change_autosave_folder(self):
        new_dir = filedialog.askdirectory(title="Select Autosave Folder")
        if new_dir:
            self.autosave_dir = new_dir
            self.log_sys(f"Autosave location updated: {self.autosave_dir}")

    def save_txt(self, ask=False, auto=False):
        fname = f"Transcript_{{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}}.txt"
        if ask:
            path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=fname, filetypes=[("Text", "*.txt")])
        else:
            path = os.path.join(os.path.expanduser("~"), 'Desktop', fname) # Safe Desktop Path
        if path:
            try:
                full_text = "".join(self.format_segment(s) for s in self.transcript_data)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                self.log_sys(f"Saved TXT: {path}")
                if self.open_file_var.get() and not auto: self.open_file_safe(path)
            except Exception as e: self.log_sys(f"Error: {e}")

    def save_srt(self):
        fname = f"Subs_{{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}}.srt"
        path = os.path.join(os.path.expanduser("~"), 'Desktop', fname) # Safe Desktop Path
        try:
            content = create_srt_content(self.transcript_data)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log_sys(f"Saved SRT: {path}")
            if self.open_file_var.get(): self.open_file_safe(path)
        except Exception as e: self.log_sys(f"Error: {e}")

    def save_json(self):
        fname = f"Data_{{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}}.json"
        path = os.path.join(os.path.expanduser("~"), 'Desktop', fname) # Safe Desktop Path
        try:
            serializable = []
            for item in self.transcript_data:
                entry = item.copy()
                if isinstance(entry['time'], datetime.datetime): entry['time'] = entry['time'].isoformat()
                serializable.append(entry)
            with open(path, "w", encoding="utf-8") as f: json.dump(serializable, f, indent=4)
            self.log_sys(f"Saved JSON: {path}")
        except Exception as e: self.log_sys(f"Error: {e}")

    def save_csv(self):
        fname = f"Data_{{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}}.csv"
        path = os.path.join(os.path.expanduser("~"), 'Desktop', fname) # Safe Desktop Path
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Start(s)", "End(s)", "Text"])
                for item in self.transcript_data:
                    writer.writerow([item['time'], item.get('start',0), item.get('end',0), item['text']])
            self.log_sys(f"Saved CSV: {path}")
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