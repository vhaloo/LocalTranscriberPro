"""Release checks and verified Windows updates, without elevated privileges."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse

from src.jobs import check_cancelled

REPOSITORY = "vhaloo/LocalTranscriberPro"
RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
MAX_INSTALLER_BYTES = 12 * 1024**3
ALLOWED_DOWNLOAD_HOSTS = {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com",
                          "github-releases.githubusercontent.com"}


def version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value)
    if not match:
        raise ValueError("Updates require a stable semantic version")
    return tuple(int(part) for part in match.groups())


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    release_url: str
    installer_url: str
    checksum_url: str
    filename: str
    size: int


class SafeRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        parsed = urlparse(new_url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS:
            raise ValueError("The update redirected to an untrusted address")
        return super().redirect_request(request, fp, code, message, headers, new_url)


def _open(url: str):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS | {"api.github.com"}:
        raise ValueError("Untrusted update address")
    request = urllib.request.Request(url, headers={"User-Agent": "LocalTranscriberPro-Updater",
                                                  "Accept": "application/vnd.github+json"})
    return urllib.request.build_opener(SafeRedirects()).open(request, timeout=20)


def _release_asset_url(url: str, tag: str, filename: str) -> bool:
    expected = f"https://github.com/{REPOSITORY}/releases/download/{quote(tag, safe='')}/{quote(filename)}"
    return url == expected


def parse_release(payload: dict, current_version: str) -> UpdateInfo | None:
    if payload.get("draft") or payload.get("prerelease"):
        return None
    tag = str(payload.get("tag_name", ""))
    try:
        target = version_tuple(tag)
    except ValueError:
        return None
    if target <= version_tuple(current_version):
        return None
    version = ".".join(str(value) for value in target)
    filename = f"LocalTranscriberPro-{version}-Windows-x64-Setup.exe"
    assets = {asset.get("name"): asset for asset in payload.get("assets", []) if isinstance(asset, dict)}
    installer, checksum = assets.get(filename), assets.get("SHA256SUMS.txt")
    if installer is None or checksum is None:
        return None
    installer_url = str(installer.get("browser_download_url", ""))
    checksum_url = str(checksum.get("browser_download_url", ""))
    if not _release_asset_url(installer_url, tag, filename) or not _release_asset_url(checksum_url, tag, "SHA256SUMS.txt"):
        raise ValueError("Release assets are outside the official repository")
    size = int(installer.get("size", 0))
    if size <= 0 or size > MAX_INSTALLER_BYTES:
        raise ValueError("Invalid update package size")
    return UpdateInfo(version, f"https://github.com/{REPOSITORY}/releases/tag/{quote(tag, safe='')}",
                      installer_url, checksum_url, filename, size)


def check_for_update(current_version: str) -> UpdateInfo | None:
    try:
        with _open(RELEASE_API) as response:
            body = response.read(1024 * 1024 + 1)
        if len(body) > 1024 * 1024:
            raise ValueError("Release metadata is too large")
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("Invalid release metadata")
        return parse_release(payload, current_version)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def expected_checksum(content: str, filename: str) -> str:
    for line in content.splitlines():
        match = re.fullmatch(r"([a-fA-F0-9]{64})\s+\*?(.+)", line.strip())
        if match and match.group(2) == filename:
            return match.group(1).lower()
    raise ValueError("The release has no SHA-256 checksum for this installer")


def download_update(info: UpdateInfo, folder: Path, progress: Callable[[float], None] | None = None,
                    cancel_event: threading.Event | None = None) -> Path:
    if Path(info.filename).name != info.filename or not info.filename.endswith("-Windows-x64-Setup.exe"):
        raise ValueError("Invalid update filename")
    version_tuple(info.version)
    if not any(_release_asset_url(info.installer_url, tag, info.filename)
               and _release_asset_url(info.checksum_url, tag, "SHA256SUMS.txt")
               for tag in (info.version, "v" + info.version)):
        raise ValueError("Update assets are outside the official repository")
    if not 0 < info.size <= MAX_INSTALLER_BYTES:
        raise ValueError("Invalid update package size")
    with _open(info.checksum_url) as response:
        checksums = response.read(256 * 1024 + 1)
    if len(checksums) > 256 * 1024:
        raise ValueError("Checksum manifest is too large")
    expected = expected_checksum(checksums.decode("utf-8-sig"), info.filename)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / info.filename
    temporary = destination.with_suffix(".exe.part")
    digest = hashlib.sha256()
    downloaded = 0
    try:
        with _open(info.installer_url) as response, temporary.open("wb") as handle:
            while True:
                check_cancelled(cancel_event)
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > info.size or downloaded > MAX_INSTALLER_BYTES:
                    raise ValueError("Update exceeds the announced size")
                handle.write(chunk)
                digest.update(chunk)
                if progress:
                    progress(min(0.99, downloaded / info.size))
            handle.flush()
            os.fsync(handle.fileno())
        if downloaded != info.size or digest.hexdigest() != expected:
            raise ValueError("The downloaded update failed SHA-256 verification")
        temporary.replace(destination)
        if progress:
            progress(1.0)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def launch_installer(path: Path) -> None:
    if os.name != "nt" or not path.is_file() or path.suffix.lower() != ".exe":
        raise ValueError("Automatic installation requires a verified Windows installer")
    # Inno Setup waits for the old application's mutex, then launches the new
    # version. User data lives outside the installation directory.
    subprocess.Popen([str(path), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/AUTOUPDATE"],
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
