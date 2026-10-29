import pandas as pd
from sklearn.pipeline import Pipeline

from starter import build_pipeline, choose_threshold


def test_pipeline_handles_missing_and_categorical_values():
    frame = pd.DataFrame(
        {
            "age": [20, None, 40, 50, 33, 61],
            "income": [30.0, 50.0, None, 90.0, 44.0, 120.0],
            "plan": ["basic", "pro", "basic", None, "pro", "basic"],
        }
    )
    target = [0, 0, 1, 1, 0, 1]
    model = build_pipeline(["age", "income"], ["plan"])
    assert isinstance(model, Pipeline)
    model.fit(frame, target)
    predictions = model.predict(frame)
    assert len(predictions) == len(frame)


def test_pipeline_exposes_probabilities():
    frame = pd.DataFrame({"age": [20, 30, 40, 50], "plan": ["a", "b", "a", "b"]})
    model = build_pipeline(["age"], ["plan"])
    model.fit(frame, [0, 0, 1, 1])
    probabilities = model.predict_proba(frame)
    assert probabilities.shape == (4, 2)


def test_threshold_minimizes_cost():
    y_true = [0, 0, 1, 1]
    scores = [0.1, 0.4, 0.6, 0.9]
    threshold = choose_threshold(y_true, scores, cost_false_positive=1, cost_false_negative=5)
    assert 0.4 < threshold <= 0.6
