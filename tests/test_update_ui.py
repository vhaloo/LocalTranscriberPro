from types import SimpleNamespace

import pytest

from src.i18n import Translator
from src.update_ui import UpdatesMixin, install_blocked
from src.updater import UpdateInfo


class App(UpdatesMixin):
    def __init__(self):
        self.closing = self.busy = self.update_checking = self.private_mode = False
        self.recorder = SimpleNamespace(recording=False)
        self.transcript_data = []
        self.t = Translator("en")
        self.statuses = []
        self.settings = SimpleNamespace(get=lambda _key, default=None: default)
        self.winfo_children = lambda: []
        self._set_status = self.statuses.append
        self._ensure_update_state()
        self._update_last_activity = 0


@pytest.mark.parametrize("error,expected", [("", "current"), ("Network disconnected", "offline")])
@pytest.mark.parametrize("silent", [True, False])
def test_offline_and_up_to_date_never_open_an_error_or_dialog(error, expected, silent, monkeypatch):
    app = App()
    monkeypatch.setattr("src.update_ui.UpdateDialog", lambda *_: pytest.fail("No popup expected"))
    app._update_checked(None, silent, error)
    assert app._update_state == expected
    assert len(app.statuses) == (0 if silent else 1)
    assert "Network disconnected" not in " ".join(app.statuses)


def test_new_release_is_remembered_while_recording_without_a_dialog():
    app = App()
    app.recorder.recording = True
    info = UpdateInfo("9.0.0", "release", "setup", "checksum", "setup.exe", 9)
    app._update_checked(info, True, "")
    assert app._available_update == info and app._update_state == "available"
    assert app.statuses == []


@pytest.mark.parametrize("field", ["busy", "model_preloading", "private_mode", "_update_deferred"])
def test_automatic_install_defers_active_or_private_work(field):
    app = App()
    setattr(app, field, True)
    app.transcript_data = [{"text": "Private conversation"}]
    assert install_blocked(app, automatic=True, now=200)


@pytest.mark.parametrize("name", ["worker_thread", "speech_thread", "tool_threads", "preload_threads"])
def test_automatic_install_waits_for_every_active_worker(name):
    app = App()
    thread = SimpleNamespace(is_alive=lambda: True)
    setattr(app, name, [thread] if name.endswith("threads") else thread)
    assert install_blocked(app, automatic=True, now=200)


def test_idle_timer_resets_on_activity_and_private_empty_session_can_update():
    app = App()
    app.private_mode = True
    assert install_blocked(app, automatic=True, now=59)
    assert not install_blocked(app, automatic=True, now=61)
    app._update_last_activity = 50
    assert install_blocked(app, automatic=True, now=61)


def test_preflight_completion_rechecks_activity_before_closing(monkeypatch):
    app = App()
    app._automatic_updates_enabled = lambda: True
    app.busy = True
    app._update_state = "installing"
    monkeypatch.setattr("src.update_ui.launch_installer", lambda *_: pytest.fail("Must keep active app open"))
    app._apply_prepared_update(True)
    assert app._update_state == "ready"


@pytest.mark.parametrize("visible,expected", [(False, False), (True, True)])
def test_hidden_settings_do_not_prevent_idle_installation(visible, expected, monkeypatch):
    class Window:
        def winfo_exists(self):
            return True
        def winfo_viewable(self):
            return visible
    app = App()
    app.winfo_children = lambda: [Window()]
    monkeypatch.setattr("src.update_ui.ctk.CTkToplevel", Window)
    assert install_blocked(app, automatic=True, now=200) == expected


def test_uncommitted_private_editor_text_also_defers_installation():
    app = App()
    app.private_mode = True
    app._editor_text = lambda: "Unsaved confidential text"
    assert install_blocked(app, automatic=True, now=200)


def test_installation_handoff_preserves_text_and_settings_before_closing(monkeypatch, tmp_path):
    app = App()
    events = []
    app._automatic_updates_enabled = lambda: True
    app._commit_editor_changes = lambda: events.append("editor")
    app._save_backup = lambda: events.append("backup")
    app.persist_settings = lambda: events.append("settings")
    app.on_close = lambda: events.append("close")
    app._update_path = tmp_path / "setup.exe"
    monkeypatch.setattr("src.update_ui.launch_installer", lambda _: events.append("launch"))
    app._apply_prepared_update(True)
    assert events == ["editor", "backup", "settings", "launch", "close"]
