"""Optional two-source SepFormer inference, bounded and entirely local.

Channels are temporary separation hypotheses, not persistent person identities.
The model was trained on English WHAMR; other languages are experimental.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from platformdirs import user_cache_dir

from src.jobs import check_cancelled
from src.local_assets import prepare_assets

REPOSITORY = "speechbrain/sepformer-whamr16k"
REVISION = "21a5b500c6f52fddc387c5d9e5fb13ffd6f039c5"
FILES = {
    "encoder.ckpt": {"size": 17272, "hash": "31d23d395a408b887b8f6ac01e477f00bcba27f95785426359fb52d52f1dc6ed", "algorithm": "sha256"},
    "decoder.ckpt": {"size": 17272, "hash": "2d959cb46de5b15f008bf5476cf7c19bc680b310c7e10883e3eddfdbde533cb8", "algorithm": "sha256"},
    "masknet.ckpt": {"size": 113112646, "hash": "e5fb8c690668e5d1bbbc9a8256974577093a09cd08e845e9f30024fdd33472ce", "algorithm": "sha256"},
}


class OverlapSeparator:
    def __init__(self, cache=None):
        self.cache = Path(cache) if cache else Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "separation/sepformer-whamr16k"
        self.encoder = self.decoder = self.masknet = None

    def load(self, allow_download=True, cancel_event=None):
        if self.encoder is not None:
            return
        prepare_assets(self.cache, REPOSITORY, REVISION, FILES, allow_download, cancel_event)
        import torch
        from speechbrain.lobes.models.dual_path import Decoder, Dual_Path_Model, Encoder, SBTransformerBlock

        torch.set_num_threads(min(torch.get_num_threads(), 8))
        def transformer():
            return SBTransformerBlock(num_layers=8, d_model=256, nhead=8, d_ffn=1024,
                                      dropout=0, use_positional_encoding=True, norm_before=True)
        encoder = Encoder(kernel_size=16, out_channels=256)
        decoder = Decoder(in_channels=256, out_channels=1, kernel_size=16, stride=8, bias=False)
        masknet = Dual_Path_Model(num_spks=2, in_channels=256, out_channels=256, num_layers=2, K=250,
            intra_model=transformer(), inter_model=transformer(), norm="ln",
            linear_layer_after_inter_intra=False, skip_around_intra=True)
        for name, model in (("encoder", encoder), ("decoder", decoder), ("masknet", masknet)):
            check_cancelled(cancel_event)
            model.load_state_dict(torch.load(self.cache / (name + ".ckpt"), map_location="cpu", weights_only=True))
            model.eval()
        self.encoder, self.decoder, self.masknet = encoder, decoder, masknet

    def separate(self, audio, cancel_event=None):
        import torch

        check_cancelled(cancel_event)
        if self.encoder is None:
            raise RuntimeError("Separation engine is not loaded")
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        if len(audio) > 6 * 16000:
            raise ValueError("Separation windows must not exceed six seconds")
        if len(audio) < 32:
            return [audio.copy()]
        with torch.inference_mode():
            features = self.encoder(torch.from_numpy(audio.copy()).unsqueeze(0))
            masks = self.masknet(features)
            outputs = []
            for index in range(2):
                samples = self.decoder(features * masks[index]).squeeze(0).numpy()
                samples = np.pad(samples[:len(audio)], (0, max(0, len(audio) - len(samples))))
                outputs.append(samples.astype(np.float32))
        check_cancelled(cancel_event)
        return outputs
