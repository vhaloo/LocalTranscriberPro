import logging
import os
import numpy as np

# Safe Imports
try:
    import torch
    import torchaudio
    from speechbrain.inference.speaker import EncoderClassifier
    from sklearn.cluster import AgglomerativeClustering
    HAS_DEPS = True
except ImportError as e:
    logging.warning(f"Diarization dependencies missing: {e}")
    HAS_DEPS = False

class Diarizer:
    def __init__(self):
        self.classifier = None
        self.enabled = HAS_DEPS

    def load_model(self):
        if not self.enabled: return False
        if self.classifier: return True
        
        try:
            logging.info("Loading Diarization Model (SpeechBrain)...")
            save_path = os.path.join(os.path.expanduser("~"), ".cache", "speechbrain")
            # Use a lightweight model
            self.classifier = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=save_path,
                run_opts={"device": "cpu"} # Keep it on CPU to avoid VRAM OOM with Whisper
            )
            return True
        except Exception as e:
            logging.error(f"Failed to load Diarizer: {e}")
            self.enabled = False
            return False

    def process(self, audio_path, segments, num_speakers=None):
        """
        Assigns speaker labels to segments.
        Modifies 'segments' in-place and returns them.
        """
        if not self.enabled: return segments
        if not self.load_model(): return segments
        
        try:
            # 1. Load Audio
            # normalize=True ensures float32 in [-1, 1]
            signal, fs = torchaudio.load(audio_path, normalize=True)
            
            # Mix to Mono if necessary
            if signal.shape[0] > 1:
                signal = torch.mean(signal, dim=0, keepdim=True)
            
            # 2. Extract Embeddings
            embeddings = []
            valid_indices = []
            
            for i, seg in enumerate(segments):
                start = seg['start']
                end = seg['end']
                s_samp = int(start * fs)
                e_samp = int(end * fs)
                
                # Check bounds
                if e_samp > signal.shape[1]: e_samp = signal.shape[1]
                if s_samp >= e_samp: continue
                
                sub = signal[:, s_samp:e_samp]
                
                # Minimum length check (~0.2s) to avoid errors
                # ECAPA-TDNN needs enough context
                if sub.shape[1] < 3200: continue 
                
                # Compute embedding
                # encode_batch expects (Batch, Time)
                # sub is (1, Time), which is correct
                emb = self.classifier.encode_batch(sub)
                embeddings.append(emb.squeeze().numpy())
                valid_indices.append(i)
            
            if not embeddings: return segments
            
            # 3. Cluster
            X = np.array(embeddings)
            
            # If we don't know num_speakers, use distance threshold
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
            for idx, label in zip(valid_indices, labels):
                spk_label = f"Speaker {label + 1}"
                segments[idx]['speaker'] = spk_label
                # Prepend to text for visibility
                segments[idx]['text'] = f"[{spk_label}] {segments[idx]['text']}"
                
            logging.info("Diarization complete.")
            return segments
            
        except Exception as e:
            logging.error(f"Diarization failed: {e}")
            return segments