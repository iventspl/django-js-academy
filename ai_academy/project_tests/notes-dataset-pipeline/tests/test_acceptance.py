import json

from starter import clean_records, load_records, split_records, summarize


def _write(tmp_path, records):
    path = tmp_path / "notes.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return str(path)


def test_load_reads_multiple_json_files(tmp_path):
    first = _write(tmp_path, [{"text": " Reset password ", "label": "account"}])
    second = tmp_path / "more.json"
    second.write_text(json.dumps([{"text": "Charged twice", "label": "billing"}]), encoding="utf-8")
    records = load_records([first, str(second)])
    assert len(records) == 2
    assert records[1]["label"] == "billing"


def test_clean_normalises_and_deduplicates():
    raw = [
        {"text": "  Reset   Password ", "label": " Account "},
        {"text": "reset password", "label": "account"},
        {"text": "", "label": "other"},
        {"text": "Charged twice", "label": None},
    ]
    cleaned = clean_records(raw)
    assert cleaned == [
        {"text": "reset password", "label": "account"},
        {"text": "charged twice", "label": "unlabelled"},
    ]
    assert raw[0]["text"].strip() == "Reset Password"


def test_split_is_deterministic_and_disjoint():
    records = [{"text": f"note {i}", "label": "a" if i % 2 else "b"} for i in range(20)]
    train_one, valid_one = split_records(records, test_size=0.25, seed=7)
    train_two, valid_two = split_records(records, test_size=0.25, seed=7)
    assert [r["text"] for r in train_one] == [r["text"] for r in train_two]
    assert [r["text"] for r in valid_one] == [r["text"] for r in valid_two]
    assert not ({r["text"] for r in train_one} & {r["text"] for r in valid_one})
    assert len(valid_one) == 5


def test_summary_reports_labels_and_missingness():
    report = summarize(
        [
            {"text": "a", "label": "account"},
            {"text": "b", "label": "account"},
            {"text": "", "label": "bug"},
        ]
    )
    assert report["rows"] == 3
    assert report["label_counts"]["account"] == 2
    assert report["missing_text"] == 1
    assert report["unique_texts"] == 2
