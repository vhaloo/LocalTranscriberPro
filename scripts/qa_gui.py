"""Open the real desktop interface with isolated QA settings and history."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gui import TranscriberApp  # noqa: E402
from src.hardware import detect_hardware  # noqa: E402
from src.history import HistoryStore  # noqa: E402
from src.settings import SettingsStore  # noqa: E402
from src.utils import setup_logging  # noqa: E402

if __name__ == "__main__":
    setup_logging()
    folder = ROOT / "artifacts" / "gui-qa"
    settings = SettingsStore(folder / "settings.json")
    settings.update({"ui_language": "fr", "ui_mode": "simple", "preset": "files", "model": "auto-best",
                     "device": "auto", "spoken_language": "auto", "check_updates": False,
                     "window_geometry": "1320x990", "output_folder": str(folder / "Transcriptions")}, save=True)
    app = TranscriberApp(hardware=detect_hardware(), settings=settings,
                         history=HistoryStore(folder / "history.sqlite3"))
    app.mainloop()
