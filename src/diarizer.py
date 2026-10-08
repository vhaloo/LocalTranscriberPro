import importlib.util
import logging
import os
import re

import numpy as np
from platformdirs import user_cache_dir

from src.jobs import JobCancelled, check_cancelled
from src.media import SAMPLE_RATE, iter_audio_chunks

# SpeechBrain inspects every loaded module on import. Importing it before
# Transformers can leave PyTorch's lazy distributed modules half-initialized.
# Keep optional speaker identification entirely lazy and separate from ASR.
HAS_DEPS = all(importlib.util.find_spec(name) is not None for name in ("torch", "torchaudio", "sklearn", "speechbrain"))


class Diarizer:
    def __init__(self):
        self.classifier = None
        self.enabled = HAS_DEPS
        self.logger = print
        self.target_fs = 16000  # ECAPA-TDNN expects 16kHz
        self.last_warning = ""

    def log(self, msg):
        if self.logger:
            self.logger(f"[Diarizer] {msg}")

    def load_model(self):
        global torch, T, AgglomerativeClustering, EncoderClassifier, LocalStrategy
        if not self.enabled:
            self.log(f"Not enabled. Missing: {globals().get('MISSING_ERR', 'Unknown')}")
            return False
        if self.classifier:
            return True

        try:
            import torch
            import torchaudio.transforms as T
            from sklearn.cluster import AgglomerativeClustering
            from speechbrain.inference.speaker import EncoderClassifier
            from speechbrain.utils.fetching import LocalStrategy

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
            logging.exception("Speaker identification could not initialize")
            self.log(f"Model load failed: {e}")
            self.enabled = False
            return False

    def process(self, audio_path, segments, num_speakers=None, callback=None, cancel_event=None):
        """
        Assigns speaker labels to segments.
        Returns segment copies with stable speaker metadata. Audio is decoded
        in bounded windows rather than accumulated for a long conference.
        """
        if callback:
            self.logger = callback
        self.last_warning = ""
        if not self.enabled:
            return segments
        if not self.load_model():
            return segments
        segments = [dict(item) for item in segments]

        self.log(f"Analyzing audio: {os.path.basename(audio_path)}")

        try:
            grouped = {}
            ordered = sorted(enumerate(segments), key=lambda entry: float(entry[1]["start"]))
            cursor = 0
            self.log(f"Extracting voice fingerprints from {len(segments)} segments...")
            for offset, audio in iter_audio_chunks(str(audio_path)):
                check_cancelled(cancel_event)
                limit = offset + len(audio) / SAMPLE_RATE
                while cursor < len(ordered) and float(ordered[cursor][1]["end"]) <= offset:
                    cursor += 1
                for index, segment in ordered[cursor:]:
                    start, end = float(segment["start"]), float(segment["end"])
                    if start >= limit:
                        break
                    left = max(0, int((start - offset) * SAMPLE_RATE))
                    right = min(len(audio), int((end - offset) * SAMPLE_RATE))
                    if right - left < SAMPLE_RATE:
                        continue
                    check_cancelled(cancel_event)
                    # Eight seconds are sufficient for a voice fingerprint.
                    sub = torch.from_numpy(audio[left:min(right, left + 8 * SAMPLE_RATE)].copy()).unsqueeze(0)
                    with torch.no_grad():
                        embedding = self.classifier.encode_batch(sub).squeeze().numpy()
                    grouped.setdefault(index, []).append(embedding)
            valid_indices = sorted(grouped)
            embeddings = [np.mean(grouped[index], axis=0) for index in valid_indices]

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

            if not num_speakers and len(set(labels)) > 20:
                # Very short/noisy segments can fragment into hundreds of
                # clusters. These are not evidence of hundreds of people.
                self.last_warning = "diarization_uncertain"
                self.log("Speaker grouping is unreliable; retaining text without inferred person labels.")
                for item in segments:
                    item.pop("speaker", None)
                    item["speaker_warning"] = self.last_warning
                return segments

            # 6. Apply Labels
            unique_speakers = set(labels)
            self.log(f"Detected {len(unique_speakers)} distinct speakers.")

            # Map back to original segments
            stable_labels = {}
            for idx, label in zip(valid_indices, labels, strict=True):
                stable_labels.setdefault(int(label), len(stable_labels) + 1)
                spk_label = f"Speaker {stable_labels[int(label)]}"
                segments[idx]["speaker"] = spk_label

                # Visual Tag in Text
                # Only prepend if not already there (idempotency)
                segments[idx]["text"] = re.sub(r"^\[Speaker \d+\]\s*", "", segments[idx]["text"])

            return segments

        except JobCancelled:
            raise
        except Exception as e:
            self.log(f"Critical Failure in Diarizer: {e}")
            import traceback

            traceback.print_exc()
            return segments
