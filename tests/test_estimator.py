from src.estimator import TimeEstimator, format_duration


def test_estimator_learns_from_observation():
    estimator = TimeEstimator()
    baseline = estimator.estimate(600, "large-v3", "cpu")
    estimator.observe(100, 50, "large-v3", "cpu")
    learned = estimator.estimate(600, "large-v3", "cpu")
    assert baseline.source == "baseline"
    assert learned.source == "learned"
    assert learned.seconds == 300


def test_duration_formatting():
    assert format_duration(5) == "5 s"
    assert format_duration(65) == "1 min 05 s"
    assert format_duration(3661) == "1 h 01 min"
