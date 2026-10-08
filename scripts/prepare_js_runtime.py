"""Validate the build-time Node runtime and preserve its redistribution license."""

from __future__ import annotations

import re
import shutil
import subprocess
import urllib.request
from pathlib import Path


def main() -> None:
    executable = shutil.which("node")
    if not executable:
        raise RuntimeError("Node >=22 is required to package online-video support")
    version = subprocess.check_output([executable, "--version"], text=True).strip()
    match = re.fullmatch(r"v(\d+)\.\d+\.\d+", version)
    if not match or int(match.group(1)) < 22:
        raise RuntimeError("Node >=22 is required to package online-video support")
    folder = Path(__file__).resolve().parents[1] / "artifacts" / "vendor" / "node"
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / "version.txt"
    license_file = folder / "LICENSE.txt"
    if not license_file.is_file() or not marker.is_file() or marker.read_text(encoding="utf-8").strip() != version:
        url = f"https://raw.githubusercontent.com/nodejs/node/{version}/LICENSE"
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read(1024 * 1024 + 1)
        if len(content) > 1024 * 1024 or b"Node.js" not in content or b"Permission" not in content:
            raise ValueError("Invalid Node redistribution license")
        license_file.write_bytes(content)
        marker.write_text(version + "\n", encoding="utf-8")
    print(f"Packaging Node {version} and its license")


if __name__ == "__main__":
    main()
