"""Vercel Python Function entry point. Never starts a listening server on import."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Handler

class handler(Handler):
    pass
