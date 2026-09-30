"""Top-level test runner for Step 4 rules verification.
Delegates to backend/scripts/test_rules_step4.py.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from scripts.test_rules_step4 import main

if __name__ == "__main__":
    main()
