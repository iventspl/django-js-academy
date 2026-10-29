# PII Redaction Pipeline — acceptance test pack

This pack defines the contract for the **PII Redaction Pipeline** project. It is intentionally failing until you implement `starter.py`.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Passing these tests does not mean the text is anonymous. Your submission still needs the threat model, false-positive analysis, residual-risk documentation and integration guidance from the project brief.
