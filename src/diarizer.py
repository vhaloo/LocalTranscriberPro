import os

import numpy as np
from platformdirs import user_cache_dir

# Safe Imports
try:
    import torch
    import torchaudio.transforms as T
    from sklearn.cluster import AgglomerativeClustering
    from speechbrain.inference.speaker import EncoderClassifier
    from speechbrain.utils.fetching import LocalStrategy

    HAS_DEPS = True
except ImportError as e:
    HAS_DEPS = False
    MISSING_ERR = str(e)


class Diarizer:
    def __init__(self):
        self.classifier = None
        self.enabled = HAS_DEPS
        self.logger = print
        self.target_fs = 16000  # ECAPA-TDNN expects 16kHz

    def log(self, msg):
        if self.logger:
            self.logger(f"[Diarizer] {msg}")

    def load_model(self):
        if not self.enabled:
            self.log(f"Not enabled. Missing: {globals().get('MISSING_ERR', 'Unknown')}")
            return False
        if self.classifier:
            return True

        try:
            self.log("Loading Speaker Recognition Model (SpeechBrain)...")
            save_path = os.path.join(user_cache_dir("LocalTranscriberPro", "Vhaloo"), "speechbrain")

            # Force CPU to be safe and avoid VRAM conflicts
            self.classifier = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=save_path,
                run_opts={"device": "cpu"},
                local_strategy=LocalStrategy.COPY,
            )
            self.log("Model loaded successfully.")
            return True
        except Exception as e:
            self.log(f"Model load failed: {e}")
            self.enabled = False
            return False

    def process(self, audio_path, segments, num_speakers=None, callback=None):
        """
        Assigns speaker labels to segments.
        Modifies 'segments' in-place and returns them.
        """
        if callback:
            self.logger = callback
        if not self.enabled:
            return segments
        if not self.load_model():
            return segments

        self.log(f"Analyzing audio: {os.path.basename(audio_path)}")

        try:
            # 1. Decode through PyAV (bundled by faster-whisper), so the
            # diarizer accepts the same audio and video files as transcription.
            try:
                from faster_whisper.audio import decode_audio

                decoded = decode_audio(audio_path, sampling_rate=self.target_fs)
                signal = torch.from_numpy(decoded).float().unsqueeze(0)
                fs = self.target_fs
            except Exception as e:
                self.log(f"Universal audio decode failed ({e}). Trying WAV/FLAC fallback...")
                import soundfile as sf

                sig_np, fs = sf.read(audio_path)
                signal = torch.from_numpy(sig_np).float()
                if len(signal.shape) == 1:
                    signal = signal.unsqueeze(0)
                else:
                    signal = signal.t()

            # 2. Mix to Mono
            if signal.shape[0] > 1:
                signal = torch.mean(signal, dim=0, keepdim=True)

            # 3. Resample to 16kHz (CRITICAL for Model Accuracy)
            if fs != self.target_fs:
                self.log(f"Resampling from {fs}Hz to {self.target_fs}Hz...")
                resampler = T.Resample(fs, self.target_fs)
                signal = resampler(signal)
                fs = self.target_fs

            # 4. Extract Embeddings per Segment
            embeddings = []
            valid_indices = []

            total_segs = len(segments)
            self.log(f"Extracting voice fingerprints from {total_segs} segments...")

            for i, seg in enumerate(segments):
                start = seg["start"]
                end = seg["end"]

                # Convert time (seconds) to samples
                s_samp = int(start * fs)
                e_samp = int(end * fs)

                # Boundary Checks
                if e_samp > signal.shape[1]:
                    e_samp = signal.shape[1]
                if s_samp >= e_samp:
                    continue

                # Extract Segment Audio
                sub = signal[:, s_samp:e_samp]

                # Check Duration
                # Model needs at least ~0.5s (8000 samples) for reliable detection.
                # If too short, we skip assigning a speaker (or assign unknown later).
                if sub.shape[1] < 4000:  # Allow down to 0.25s but might be noisy
                    continue

                # Get Embedding
                # encode_batch returns (batch, 1, 192) -> squeeze to (192)
                with torch.no_grad():
                    emb = self.classifier.encode_batch(sub)

                embeddings.append(emb.squeeze().numpy())
                valid_indices.append(i)

                if i > 0 and i % 20 == 0:
                    self.log(f"Processed {i}/{total_segs} segments...")

            if not embeddings:
                self.log("No valid audio segments found (too short or silent).")
                return segments

            # 5. Clustering (Speaker Identification)
            self.log(f"Grouping {len(embeddings)} segments into speakers...")
            X = np.array(embeddings)

            if len(embeddings) == 1:
                labels = np.array([0])
            else:
                # Parameters
                thresh = 0.5  # Cosine distance threshold (lower = stricter)
                n_clusters = None
                if num_speakers:
                    n_clusters = max(1, min(int(num_speakers), len(embeddings)))
                    thresh = None

                # Agglomerative clustering works without knowing K in advance.
                clusterer = AgglomerativeClustering(
                    n_clusters=n_clusters, metric="cosine", linkage="average", distance_threshold=thresh
                )
                labels = clusterer.fit_predict(X)

            # 6. Apply Labels
            unique_speakers = set(labels)
            self.log(f"Detected {len(unique_speakers)} distinct speakers.")

            # Map back to original segments
            for idx, label in zip(valid_indices, labels, strict=True):
                spk_label = f"Speaker {label + 1}"
                segments[idx]["speaker"] = spk_label

                # Visual Tag in Text
                # Only prepend if not already there (idempotency)
                original_text = segments[idx]["text"]
                if not original_text.startswith("[Speaker"):
                    segments[idx]["text"] = f"[{spk_label}] {original_text}"

            return segments

        except Exception as e:
            self.log(f"Critical Failure in Diarizer: {e}")
            import traceback

            traceback.print_exc()
            return segments
