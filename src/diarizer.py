import logging
import os
import sys
import numpy as np

# Safe Imports
try:
    import torch
    import torchaudio
    from speechbrain.inference.speaker import EncoderClassifier
    from sklearn.cluster import AgglomerativeClustering
    HAS_DEPS = True
except ImportError as e:
    HAS_DEPS = False
    MISSING_ERR = str(e)

class Diarizer:
    def __init__(self):
        self.classifier = None
        self.enabled = HAS_DEPS
        self.logger = print # Default to print

    def log(self, msg):
        if self.logger: self.logger(f"[Diarizer] {msg}")

    def load_model(self):
        if not self.enabled: 
            self.log(f"Not enabled. Missing: {globals().get('MISSING_ERR', 'Unknown')}")
            return False
        if self.classifier: return True
        
        try:
            self.log("Loading Speaker Recognition Model (downloading if needed)...")
            save_path = os.path.join(os.path.expanduser("~"), ".cache", "speechbrain")
            
            # Force CPU to be safe
            self.classifier = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=save_path,
                run_opts={"device": "cpu"}
            )
            self.log("Model loaded.")
            return True
        except Exception as e:
            self.log(f"Model load failed: {e}")
            self.enabled = False
            return False

    def process(self, audio_path, segments, num_speakers=None, callback=None):
        """
        Assigns speaker labels to segments.
        Modifies 'segments' in-place and returns them.
        callback: function(str) to log messages to GUI.
        """
        if callback: self.logger = callback
        
        if not self.enabled: return segments
        if not self.load_model(): return segments
        
        self.log(f"Analyzing audio: {os.path.basename(audio_path)}")
        try:
            # 1. Load Audio
            try:
                signal, fs = torchaudio.load(audio_path, normalize=True)
            except Exception as e:
                self.log(f"Torchaudio load error: {e}. Trying soundfile...")
                import soundfile as sf
                sig_np, fs = sf.read(audio_path)
                signal = torch.from_numpy(sig_np).float()
                if len(signal.shape) == 1: signal = signal.unsqueeze(0)
                else: signal = signal.t()

            if signal.shape[0] > 1:
                signal = torch.mean(signal, dim=0, keepdim=True)
            
            # 2. Extract Embeddings
            embeddings = []
            valid_indices = []
            
            total_segs = len(segments)
            self.log(f"Extracting embeddings for {total_segs} segments...")
            
            for i, seg in enumerate(segments):
                start = seg['start']
                end = seg['end']
                s_samp = int(start * fs)
                e_samp = int(end * fs)
                
                if e_samp > signal.shape[1]: e_samp = signal.shape[1]
                if s_samp >= e_samp: continue
                
                sub = signal[:, s_samp:e_samp]
                
                if sub.shape[1] < 3000: continue 
                
                emb = self.classifier.encode_batch(sub)
                embeddings.append(emb.squeeze().numpy())
                valid_indices.append(i)
                
                if i > 0 and i % 50 == 0:
                    self.log(f"Processed {i}/{total_segs} segments...")
            
            if not embeddings: 
                self.log("No valid audio segments found for analysis.")
                return segments
            
            # 3. Cluster
            self.log("Clustering speakers...")
            X = np.array(embeddings)
            
            thresh = 0.5 
            n_clusters = None
            if num_speakers:
                n_clusters = int(num_speakers)
                thresh = None
            
            clusterer = AgglomerativeClustering(
                n_clusters=n_clusters,
                metric="cosine",
                linkage="average",
                distance_threshold=thresh
            )
            labels = clusterer.fit_predict(X)
            
            # 4. Apply Labels
            unique_speakers = set(labels)
            self.log(f"Found {len(unique_speakers)} unique speakers.")
            
            for idx, label in zip(valid_indices, labels):
                spk_label = f"Speaker {label + 1}"
                segments[idx]['speaker'] = spk_label
                segments[idx]['text'] = f"[{spk_label}] {segments[idx]['text']}"
                
            return segments
            
        except Exception as e:
            self.log(f"Critical Failure: {e}")
            import traceback
            traceback.print_exc()
            return segments