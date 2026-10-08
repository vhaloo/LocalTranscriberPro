"""Exercise the real decoder API so incompatible dependency updates fail early."""
from io import BytesIO

import numpy as np
import pytest
import soundfile as sf
from faster_whisper.audio import decode_audio


@pytest.mark.parametrize("audio_format", ["WAV", "FLAC"])
def test_real_decoder_reads_and_resamples_stereo_audio(audio_format):
    rate = 32000
    time = np.arange(rate // 10) / rate
    stereo = np.column_stack((0.4 * np.sin(2 * np.pi * 220 * time),
                              0.4 * np.sin(2 * np.pi * 440 * time)))
    encoded = BytesIO()
    sf.write(encoded, stereo, rate, format=audio_format, subtype="PCM_16")
    encoded.seek(0)

    decoded = decode_audio(encoded, sampling_rate=16000)

    assert decoded.dtype == np.float32
    assert decoded.shape == (1600,)
    assert np.isfinite(decoded).all()
    assert np.max(np.abs(decoded)) > 0.1
