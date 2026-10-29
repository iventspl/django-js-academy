# Safe Text-to-SQL Analyst — acceptance test pack

This pack defines the contract for the **Safe Text-to-SQL Analyst** project. It is intentionally failing until you implement `starter.py`.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

The validator is one layer of defence. Your submission still needs a read-only database role, a refusal policy, an LLM/template baseline, adversarial tests and the threat model from the project brief.
