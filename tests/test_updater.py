import hashlib
import io

import pytest

from src.jobs import JobCancelled
from src.updater import (
    RELEASE_API,
    SafeRedirects,
    check_for_update,
    download_update,
    expected_checksum,
    launch_installer,
    parse_release,
    version_tuple,
)


def release(version="3.1.0"):
    filename = f"LocalTranscriberPro-{version}-Windows-x64-Setup.exe"
    base = f"https://github.com/vhaloo/LocalTranscriberPro/releases/download/v{version}/"
    return {"tag_name": f"v{version}", "draft": False, "prerelease": False, "assets": [
        {"name": filename, "browser_download_url": base + filename, "size": 9},
        {"name": "SHA256SUMS.txt", "browser_download_url": base + "SHA256SUMS.txt", "size": 200},
    ]}


@pytest.mark.parametrize("target,offered", [("2.2.0", False), ("3.0.0", False), ("3.0.1", True), ("3.1.0", True), ("10.0.0", True)])
def test_updates_never_downgrade_and_compare_numeric_versions(target, offered):
    assert (parse_release(release(target), "3.0.0") is not None) == offered


@pytest.mark.parametrize("field", ["draft", "prerelease"])
def test_unstable_releases_are_not_offered(field):
    payload = release()
    payload[field] = True
    assert parse_release(payload, "3.0.0") is None


@pytest.mark.parametrize("version", ["3.1.0-rc1", "3.1", "3.1.0/../../bad", "03.1.0", "3.1.0+local"])
def test_malformed_or_prerelease_versions_are_rejected(version):
    with pytest.raises(ValueError):
        version_tuple(version)


def test_missing_checksum_manifest_prevents_installation():
    payload = release()
    payload["assets"].pop()
    assert parse_release(payload, "3.0.0") is None


def test_foreign_download_url_is_rejected():
    payload = release()
    payload["assets"][0]["browser_download_url"] = "https://github.com/attacker/repo/setup.exe"
    with pytest.raises(ValueError, match="official repository"):
        parse_release(payload, "3.0.0")


@pytest.mark.parametrize("size", [0, -1, 13 * 1024**3])
def test_invalid_announced_download_size_is_rejected(size):
    payload = release()
    payload["assets"][0]["size"] = size
    with pytest.raises(ValueError, match="size"):
        parse_release(payload, "3.0.0")


def test_download_verifies_the_actual_bytes_before_publishing_package(tmp_path, monkeypatch):
    binary = b"installer"
    info = parse_release(release(), "3.0.0")
    manifest = f"{hashlib.sha256(binary).hexdigest()}  {info.filename}\n".encode()
    monkeypatch.setattr("src.updater._open", lambda url: io.BytesIO(manifest if url == info.checksum_url else binary))
    progress = []
    path = download_update(info, tmp_path, progress.append)
    assert path.read_bytes() == binary
    assert progress[-1] == 1
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.parametrize("body", [b"corrupted", b"truncated", b"installer-with-extra-payload"])
def test_corrupt_or_oversized_download_never_becomes_an_installer(tmp_path, monkeypatch, body):
    info = parse_release(release(), "3.0.0")
    manifest = f"{hashlib.sha256(b'installer').hexdigest()}  {info.filename}\n".encode()
    monkeypatch.setattr("src.updater._open", lambda url: io.BytesIO(manifest if url == info.checksum_url else body))
    with pytest.raises(ValueError):
        download_update(info, tmp_path)
    assert not list(tmp_path.glob("*.exe"))
    assert not list(tmp_path.glob("*.part"))


def test_cancellation_removes_incomplete_download(tmp_path, monkeypatch):
    import threading

    info = parse_release(release(), "3.0.0")
    manifest = f"{hashlib.sha256(b'installer').hexdigest()} *{info.filename}\n".encode()
    monkeypatch.setattr("src.updater._open", lambda url: io.BytesIO(manifest if url == info.checksum_url else b"installer"))
    event = threading.Event()
    event.set()
    with pytest.raises(JobCancelled):
        download_update(info, tmp_path, cancel_event=event)
    assert not list(tmp_path.iterdir())


def test_checksum_requires_exact_filename():
    with pytest.raises(ValueError):
        expected_checksum("a" * 64 + "  another-installer.exe", "setup.exe")


def test_check_only_contacts_the_public_release_api(monkeypatch):
    import json

    requested = []

    def open_url(url):
        requested.append(url)
        return io.BytesIO(json.dumps(release()).encode())

    monkeypatch.setattr("src.updater._open", open_url)
    assert check_for_update("3.0.0").version == "3.1.0"
    assert requested == [RELEASE_API]


def test_redirect_to_insecure_or_foreign_host_is_blocked():
    handler = SafeRedirects()
    for url in ("http://github.com/file", "https://evil.example/file", "https://localhost/file"):
        with pytest.raises(ValueError):
            handler.redirect_request(None, None, 302, "Found", {}, url)


def test_windows_installation_is_per_user_and_requests_relaunch(tmp_path, monkeypatch):
    import src.updater as updater

    package = tmp_path / "setup.exe"
    package.write_bytes(b"verified")
    calls = []
    monkeypatch.setattr(updater.subprocess, "Popen", lambda args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(updater.os, "getpid", lambda: 12345)
    if updater.os.name != "nt":
        pytest.skip("Windows process creation flags are platform-specific")
    launch_installer(package)
    assert "/AUTOUPDATE" in calls[0][0]
    assert "/NORESTART" in calls[0][0]
    assert "/WAITPID=12345" in calls[0][0]
    assert not any("runas" in arg.lower() for arg in calls[0][0])


def test_forged_update_object_is_rejected_before_network_access(tmp_path, monkeypatch):
    from dataclasses import replace
    info = parse_release(release(), "3.0.0")
    monkeypatch.setattr("src.updater._open", lambda *_args: pytest.fail("Must reject before download"))
    with pytest.raises(ValueError):
        download_update(replace(info, installer_url="https://evil.example/setup.exe"), tmp_path)
