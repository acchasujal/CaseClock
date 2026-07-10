# Root conftest.py — adds the repository root to sys.path so that
# `graph`, `backend`, `shared`, and `synthetic_data` packages are importable
# without installation.
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
