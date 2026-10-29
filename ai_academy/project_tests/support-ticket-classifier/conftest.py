import sys
from pathlib import Path

# Make `starter.py` importable when pytest is run from the pack root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
