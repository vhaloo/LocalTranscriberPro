import pytest

from src.meter import amplitude_to_db


def test_amplitude_to_db_uses_safe_display_range():
    assert amplitude_to_db(1.0) == pytest.approx(0.0)
    assert amplitude_to_db(0.1) == pytest.approx(-20.0)
    assert amplitude_to_db(0.0) == pytest.approx(-60.0)
    assert amplitude_to_db(99.0) == pytest.approx(0.0)
