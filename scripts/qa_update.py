"""Validate the real update dialog/installer against a local built package.

This intentionally replaces only the network transport with local fixture files.
The production checksum validation, progress, acceptance, installer flags,
application mutex and relaunch are exercised. Installation happens only after
pressing Download & install in the displayed dialog.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.updater as updater  # noqa: E402
from src import __version__  # noqa: E402
from src.gui import TranscriberApp  # noqa: E402
from src.hardware import detect_hardware  # noqa: E402
from src.history import HistoryStore  # noqa: E402
from src.settings import SettingsStore  # noqa: E402
from src.startup import SingleInstanceLock  # noqa: E402
from src.update_ui import UpdateDialog  # noqa: E402
from src.updater import UpdateInfo  # noqa: E402
from src.utils import setup_logging  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("installer", type=Path)
    args = parser.parse_args()
    installer = args.installer.resolve()
    if installer.name != f"LocalTranscriberPro-{__version__}-Windows-x64-Setup.exe":
        raise ValueError("Expected the current-version installer")
    digest = hashlib.file_digest(installer.open("rb"), "sha256").hexdigest()
    base = f"https://github.com/vhaloo/LocalTranscriberPro/releases/download/v{__version__}/"
    info = UpdateInfo(__version__, base.replace("download/", "tag/").rstrip("/"),
                      base + installer.name, base + "SHA256SUMS.txt", installer.name, installer.stat().st_size)

    def fixture_transport(url):
        if url == info.checksum_url:
            return io.BytesIO(f"{digest}  {installer.name}\n".encode())
        if url == info.installer_url:
            return installer.open("rb")
        raise ValueError("Unexpected fixture URL")

    updater._open = fixture_transport
    folder = ROOT / "artifacts" / "update-qa"
    settings = SettingsStore(folder / "settings.json")
    settings.update({"ui_language": "fr", "ui_mode": "simple", "simple_quality": "fast", "model": "auto-fast",
                     "preset": "files", "check_updates": False, "window_geometry": "1320x990",
                     "output_folder": str(folder / "Transcriptions")}, save=True)
    lock = SingleInstanceLock()
    if not lock.acquire():
        raise RuntimeError("Close the current application before upgrade validation")
    try:
        setup_logging()
        app = TranscriberApp(hardware=detect_hardware(), settings=settings, history=HistoryStore(folder / "history.sqlite3"))
        app.title("Local Transcriber Pro — validation de mise à jour 3.0")
        app.after(3000, lambda: UpdateDialog(app, info))
        app.mainloop()
    finally:
        lock.release()


if __name__ == "__main__":
    main()
