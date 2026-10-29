import pandas as pd

from starter import audit_data, classification_metrics, temporal_split


def _frame():
    return pd.DataFrame(
        {
            "month": ["2026-01", "2026-02", "2026-03", "2026-04", "2026-04"],
            "customer_id": ["a", "b", "c", "d", "d"],
            "spend": [10.0, None, 30.0, 40.0, 40.0],
            "churned": [0, 0, 1, 1, 1],
        }
    )


def test_temporal_split_has_no_future_leakage():
    train, valid = temporal_split(_frame(), "month", "2026-03")
    assert train["month"].max() < "2026-03"
    assert valid["month"].min() >= "2026-03"
    assert len(train) + len(valid) == len(_frame())


def test_audit_reports_rate_missing_and_duplicates():
    report = audit_data(_frame(), "churned")
    assert report["rows"] == 5
    assert report["target_rate"] == 0.6
    assert report["duplicate_rows"] == 1
    assert report["missing"]["spend"] == 0.2


def test_audit_exposes_leakage_risk_list():
    report = audit_data(_frame(), "churned")
    assert isinstance(report["leakage_risks"], list)
    assert report["leakage_risks"]


def test_classification_metrics_on_known_predictions():
    result = classification_metrics([1, 0, 1, 0], [1, 1, 0, 0])
    assert result["accuracy"] == 0.5
    assert result["precision"] == 0.5
    assert result["recall"] == 0.5
    assert result["f1"] == 0.5
