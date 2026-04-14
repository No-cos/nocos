# tests/conftest.py
# Root conftest — adds the backend package root to sys.path so all test
# files can import backend modules without a pip install.

import sys
import os

# Insert backend/ at the front of sys.path so "from services.xxx import yyy"
# works when pytest is run from either backend/ or the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
