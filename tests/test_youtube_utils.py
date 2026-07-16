from pathlib import Path

from src.youtube_utils import bundled_ffmpeg, is_supported_url


def test_youtube_url_allowlist():
    assert is_supported_url("https://www.youtube.com/watch?v=abc")
    assert is_supported_url("https://youtu.be/abc")
    assert not is_supported_url("https://example.com/video")
    assert not is_supported_url("file:///private/audio.wav")


def test_ffmpeg_is_packaged_by_the_runtime_dependency():
    assert Path(bundled_ffmpeg()).is_file()
