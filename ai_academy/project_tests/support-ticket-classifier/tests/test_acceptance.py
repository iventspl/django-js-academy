from starter import predict_with_confidence, route_low_confidence, train_baseline

TEXTS = [
    "Please refund the duplicate charge",
    "I was charged twice this month",
    "The app crashes when I upload a file",
    "The dashboard shows a blank screen",
    "I cannot log into my account",
    "Reset my password link is broken",
]
LABELS = ["billing", "billing", "bug", "bug", "account", "account"]


def test_baseline_predicts_known_labels():
    model = train_baseline(TEXTS, LABELS)
    predictions = predict_with_confidence(model, TEXTS)
    assert len(predictions) == len(TEXTS)
    assert all(label in {"billing", "bug", "account"} for label, _ in predictions)


def test_confidence_is_a_probability():
    model = train_baseline(TEXTS, LABELS)
    predictions = predict_with_confidence(model, ["refund my charge"])
    assert len(predictions) == 1
    assert 0.0 <= predictions[0][1] <= 1.0


def test_low_confidence_routes_to_human():
    predictions = [("bug", 0.91), ("billing", 0.42), ("account", 0.60)]
    assert route_low_confidence(predictions, threshold=0.6) == ["bug", "human", "account"]


def test_threshold_is_inclusive():
    assert route_low_confidence([("bug", 0.6)], threshold=0.6) == ["bug"]
