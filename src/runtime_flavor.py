"""CPU package choice persists through the official updater."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def cpu_only():
    try:
        return json.loads((Path(getattr(sys, "_MEIPASS", Path(__file__).parents[1])) / "runtime-flavor.json").read_text("utf-8")).get("cpu_only") is True
    except (OSError, ValueError, TypeError):
        return False
