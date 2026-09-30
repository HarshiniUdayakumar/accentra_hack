"""Top-level test runner for Step 5 ML verification.
Delegates to backend/scripts/test_ml_step5.py.
"""
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.test_ml_step5 import main

if __name__ == "__main__":
    main()
