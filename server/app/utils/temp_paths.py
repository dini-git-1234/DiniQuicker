from __future__ import annotations

import os
from pathlib import Path


def get_temp_root() -> Path:
    """
    Single writable workspace for all generated artifacts (screenshots, downloads, debug files, etc).

    Override with QUICKERAI_TEMP_ROOT (absolute or relative).
    """
    raw = (os.environ.get("QUICKERAI_TEMP_ROOT") or "temp").strip()
    root = Path(raw)
    root.mkdir(parents=True, exist_ok=True)
    return root


def temp_dir(*parts: str | Path, ensure: bool = True) -> Path:
    """Build a path under TEMP root and optionally mkdir it."""
    p = get_temp_root()
    for part in parts:
        p = p / part
    if ensure:
        p.mkdir(parents=True, exist_ok=True)
    return p

