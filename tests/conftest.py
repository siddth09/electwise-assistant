# conftest.py — shared pytest configuration
import os
import sys

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required environment variables before any imports
os.environ.setdefault("GEMINI_API_KEY", "test-api-key-dummy")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("FLASK_ENV", "testing")
