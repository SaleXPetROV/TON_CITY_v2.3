"""Shared conftest for backend tests.

Ensures the backend module directory is on sys.path so tests can `import promo_service`,
`import telegram_bot`, etc. without depending on a PYTHONPATH env override.
"""
import os
import sys

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
