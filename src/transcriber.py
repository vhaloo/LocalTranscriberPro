import whisper
import torch
import logging
import subprocess
import os
import shutil
import re

# Model sizes map
MODEL_SIZES = {
    "tiny": "tiny (~75 MB)",
    "base": "base (~145 MB)",
    "small": "small (~461 MB)",
    "medium": "medium (~1.5 GB)",
    "large": "large (~3 GB)"
}
REVERSE_MODEL_MAP = {v: k for k, v in MODEL_SIZES.items()}

class TranscriberEngine:
    def __init__(self):
        self.model = None
        self.model_name = None
        self.device = "cpu"
        self.check_hardware()

    def check_hardware(self):
        self.has_nvidia_gpu = False
        try:
            subprocess.check_output("nvidia-smi", stderr=subprocess.STDOUT, shell=True)
            self.has_nvidia_gpu = True
        except: self.has_nvidia_gpu = False
        self.torch_cuda_available = torch.cuda.is_available()
        self.cuda_missing = self.has_nvidia_gpu and not self.torch_cuda_available
        self.mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()

    def recommend_model(self):
        """Auto-detects best model based on hardware"""
        try:
            if self.torch_cuda_available:
                # Get VRAM in GB
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                if vram_gb >= 8: return MODEL_SIZES["large"]
                if vram_gb >= 5: return MODEL_SIZES["medium"]
                if vram_gb >= 2: return MODEL_SIZES["small"]
                return MODEL_SIZES["base"]
            elif self.mps_available:
                # Mac M-series usually has shared RAM, default to small/medium
                return MODEL_SIZES["small"]
            else:
                # CPU mode - try to get system RAM
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(stat)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                ram_gb = stat.ullTotalPhys / (1024**3)
                
                # CPU is slow, so we don't recommend Large even if they have RAM
                if ram_gb >= 16: return MODEL_SIZES["small"]
                if ram_gb >= 8: return MODEL_SIZES["base"]
                return MODEL_SIZES["tiny"]
        except Exception as e:
            logging.error(f"Error auto-detecting hardware: {e}")
            return MODEL_SIZES["small"]

    def load_model(self, model_name_display, device_mode):
        """Loads the model if not already loaded or if name/device changed."""
        model_name = REVERSE_MODEL_MAP.get(model_name_display, "small")
        
        target_device = "cpu"
        if device_mode == "GPU (CUDA)": 
            target_device = "cuda"
        elif device_mode == "GPU (MPS)": 
            target_device = "mps"
        elif device_mode == "Auto": 
            if self.torch_cuda_available:
                target_device = "cuda"
            elif self.mps_available:
                target_device = "mps"
            else:
                target_device = "cpu"
        
        if self.model is None or self.model_name != model_name or self.device != target_device:
            logging.info(f"Loading model '{model_name}' on {target_device.upper()}...")
            self.model = None 
            torch.cuda.empty_cache()
            
            self.model = whisper.load_model(model_name, device=target_device)
            self.model_name = model_name
            self.device = target_device
            logging.info("Model loaded.")
        
        return target_device

    def transcribe_audio(self, audio_data, task="transcribe", fp16=True):
        if self.model is None: raise RuntimeError("Model not loaded")
        if audio_data.dtype != "float32": audio_data = audio_data.astype("float32")
        res = self.model.transcribe(audio_data, fp16=fp16, task=task)
        return res

    def transcribe_file(self, filepath, task="transcribe", verbose=False):
        if self.model is None: raise RuntimeError("Model not loaded")
        res = self.model.transcribe(filepath, verbose=verbose, task=task)
        return res

    # --- Management ---
    def get_cache_dir(self):
        """Returns the whisper cache directory."""
        return os.path.join(os.path.expanduser("~"), ".cache", "whisper")

    def get_downloaded_models(self):
        """Scans cache for downloaded models."""
        cache_dir = self.get_cache_dir()
        if not os.path.exists(cache_dir): return []
        
        models = []
        for f in os.listdir(cache_dir):
            path = os.path.join(cache_dir, f)
            if os.path.isfile(path):
                size_mb = os.path.getsize(path) / (1024 * 1024)
                models.append({"name": f, "size": f"{size_mb:.1f} MB", "path": path})
        return models

    def delete_model_file(self, path):
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
        except: return False
        return False

    def cleanup_text(self, text):
        """Removes common hallucinations."""
        # Remove repeated phrases like "Thank you." "Bye."
        bad_phrases = ["Thank you.", "Thanks for watching!", "Subscribe"]
        for phrase in bad_phrases:
            if text.strip() == phrase:
                return ""
        
        # Remove repetitive loops (e.g. "I am. I am. I am.")
        # Simple heuristic: if same word repeated 3+ times
        words = text.split()
        if len(words) > 4 and len(set(words)) < 2:
            return ""
            
        return text