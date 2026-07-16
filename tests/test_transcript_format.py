from src.transcript_format import TranscriptFormat, format_transcript

SEGMENTS = [
    {"start": 1.0, "end": 3.5, "speaker": "Speaker 1", "text": "Hello there."},
    {"start": 4.0, "end": 7.0, "speaker": "Speaker 1", "text": "This stays together."},
    {"start": 8.0, "end": 9.0, "speaker": "Speaker 2", "text": "New voice."},
]


def test_lines_can_show_start_time_and_duration():
    text = format_transcript(
        SEGMENTS,
        TranscriptFormat(mode="lines", show_timestamps=True, show_duration=True),
    )
    assert "[00:00:01 • 2.5 s] [Speaker 1] Hello there." in text
    assert text.count("\n") == 2


def test_blocks_join_nearby_phrases_and_can_hide_timing():
    text = format_transcript(
        SEGMENTS,
        TranscriptFormat(mode="blocks", show_timestamps=False, show_duration=False),
    )
    assert text.startswith("[Speaker 1] Hello there. This stays together.")
    assert "\n\n[Speaker 2] New voice." in text
    assert "00:00" not in text
