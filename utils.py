"""Utility helpers used across the application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Union
import hashlib
from io import BytesIO

PRESET_DIR = Path(".streamlit/score_presets")
PRESET_DIR.mkdir(parents=True, exist_ok=True)


def save_preset(name: str, weights: Dict[str, float]) -> None:
    """Save ``weights`` dictionary to ``name.json`` inside ``PRESET_DIR``."""
    path = PRESET_DIR / f"{name}.json"
    path.write_text(json.dumps(weights), encoding="utf-8")


def load_preset(name: str) -> Dict[str, float]:
    """Load a preset by ``name``."""
    path = PRESET_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def hash_file(file_obj: Union[BytesIO, "UploadedFile", bytes]) -> str:
    """Return a SHA256 hash for the given file-like object or bytes."""
    if isinstance(file_obj, bytes):
        data = file_obj
    elif hasattr(file_obj, "getvalue"):
        data = file_obj.getvalue()
    else:
        pos = file_obj.tell()
        file_obj.seek(0)
        data = file_obj.read()
        file_obj.seek(pos)
    return hashlib.sha256(data).hexdigest()
