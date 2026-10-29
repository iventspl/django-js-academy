# Notes-to-Dataset Pipeline — acceptance test pack

This pack defines the contract for the **Notes-to-Dataset Pipeline** project. It is intentionally failing until you implement `starter.py`. Do not edit the tests to make them pass; change the implementation.

## Run

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

## Files

- `starter.py` — the interfaces you implement.
- `tests/test_acceptance.py` — the contract.
- `requirements.txt`, `pytest.ini`, `conftest.py`.
- `README.md` — this file.

## Rule of the exercise

The tests are a floor, not the whole project. Your submission still needs the README, the cleaned dataset, the split files, the summary JSON and the failure analysis described in the project brief on AI Academy.
