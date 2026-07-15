from src.utils import create_srt_content, create_vtt_content, format_timestamp

SEGMENTS = [{"start": 1.25, "end": 2.5, "text": "Hello"}]


def test_timestamp_formats_srt_and_vtt():
    assert format_timestamp(3661.234) == "01:01:01,234"
    assert "00:00:01,250 --> 00:00:02,500" in create_srt_content(SEGMENTS)
    assert "00:00:01.250 --> 00:00:02.500" in create_vtt_content(SEGMENTS)
