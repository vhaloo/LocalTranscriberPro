"""Exercise real Tk update callbacks with isolated data and no actual installer."""
from __future__ import annotations

import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.update_ui as updates  # noqa: E402
from scripts.qa_workspace import WorkspaceApp  # noqa: E402
from src import __version__  # noqa: E402
from src.hardware import HardwareProfile  # noqa: E402
from src.history import HistoryStore  # noqa: E402
from src.settings import SettingsStore  # noqa: E402
from src.updater import UpdateInfo  # noqa: E402


def main():
    folder = ROOT / "artifacts" / ("gui-qa-" + __version__) / "updates"
    store = SettingsStore(folder / "settings.json")
    store.update({"check_updates": False, "output_folder": str(folder / "outputs")}, save=True)
    app = WorkspaceApp(hardware=HardwareProfile("Test", "", "", "CPU", 4, 32),
                       settings=store, history=HistoryStore(folder / "history.sqlite3"))
    errors, events, cases = [], [], []
    app.report_callback_exception = lambda *values: errors.append("".join(traceback.format_exception(*values)))
    original_close = app.on_close
    original_download, original_validate, original_launch = updates.download_update, updates.validate_installer_file, updates.launch_installer

    def pump_until(condition, timeout=10):
        deadline = time.monotonic() + timeout
        while not condition():
            if time.monotonic() >= deadline:
                raise TimeoutError("Update UI state did not settle")
            app.update()
            time.sleep(0.01)

    try:
        app.update()
        for error in ("", "No internet"):
            app._update_checked(None, True, error)
            assert not any(isinstance(window, updates.UpdateDialog) for window in app.winfo_children())
        cases.append("offline-and-current-startup-checks-have-no-popup")
        package = folder / "fixture.exe"
        package.write_bytes(b"local test fixture - never executable")
        def download(_info, _folder, progress, _cancel, *, verified_checksum):
            progress(0.5)
            verified_checksum(hashlib.sha256(package.read_bytes()).hexdigest())
            return package
        updates.download_update = download
        updates.validate_installer_file = lambda path, digest: events.append(
            "verified" if hashlib.sha256(path.read_bytes()).hexdigest() == digest else "bad")
        updates.launch_installer = lambda _path: events.append("handoff")
        app._automatic_updates_enabled = lambda: True
        app.on_close = lambda: events.append("close")
        app.busy = True
        info = UpdateInfo("9.0.0", "release", "setup", "checksum", "fixture.exe", package.stat().st_size)
        app._update_checked(info, True, "")
        pump_until(lambda: app._update_state == "ready")
        assert "9.0.0" in app.updates_button.cget("text") and events == []
        app._update_last_activity = time.monotonic() - 70
        app._update_idle_tick()
        assert events == []
        app.busy = False
        app.private_mode = True
        app.transcript_data = [{"text": "Private text", "start": 0, "end": 1}]
        app._update_idle_tick()
        assert events == []
        cases.append("available-badge-and-download-preserve-active-and-private-work")
        app.private_mode = False
        app.transcript_data = []
        app.open_workspace_settings()
        app.update()
        assert updates.install_blocked(app, automatic=True)
        app.settings_window.withdraw()
        app._update_last_activity = time.monotonic() - 70
        assert not updates.install_blocked(app, automatic=True)
        app.textbox._textbox.bind("<MouseWheel>", lambda _event: "break", add="+")
        app.textbox._textbox.event_generate("<MouseWheel>", delta=-120)
        app.update()
        assert updates.install_blocked(app, automatic=True), "Scrolling must defer installation"
        app._update_last_activity = time.monotonic() - 70
        app.event_generate("<Motion>", x=20, y=20)
        app.update()
        assert updates.install_blocked(app, automatic=True), "Pointer activity must defer installation"
        app._update_last_activity = time.monotonic() - 70
        app.bind("<KeyPress-F8>", lambda _event: "break")
        app.event_generate("<KeyPress-F8>")
        app.update()
        assert updates.install_blocked(app, automatic=True), "Handled keyboard shortcuts must defer installation"
        cases.append("scrolling-and-pointer-activity-reset-the-idle-period")
        cases.append("widget-and-keyboard-break-handlers-cannot-hide-activity")
        app._update_last_activity = time.monotonic() - 70
        app._update_idle_tick()
        pump_until(lambda: "close" in events)
        assert events == ["verified", "handoff", "close"]
        assert not errors, errors
        cases.append("hidden-settings-idle-signature-result-handoff-and-relaunch-flow")
        proof = {"success": True, "cases": cases, "events": events,
                 "transport": "local fixture; final file validator and installer replaced by recording stubs",
                 "callback_errors": errors}
        (folder / "proof.json").write_text(json.dumps(proof, indent=2), "utf-8")
        print(json.dumps(proof, indent=2))
    finally:
        updates.download_update, updates.validate_installer_file, updates.launch_installer = original_download, original_validate, original_launch
        app.on_close = original_close
        original_close()


if __name__ == "__main__":
    main()
