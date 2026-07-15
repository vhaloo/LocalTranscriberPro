from src.youtube_utils import is_supported_url


def test_youtube_url_allowlist():
    assert is_supported_url("https://www.youtube.com/watch?v=abc")
    assert is_supported_url("https://youtu.be/abc")
    assert not is_supported_url("https://example.com/video")
    assert not is_supported_url("file:///private/audio.wav")
