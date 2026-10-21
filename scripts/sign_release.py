"""Sign final, already verified release assets; private key stays outside Git.

Usage: python scripts/sign_release.py ASSET_FOLDER --key PRIVATE_KEY_PATH
The raw Ed25519 private key is never printed or bundled. Distribute only the
manifest and signature. Initial key provisioning is a separate maintainer step.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path


def sign(folder, key_path, version):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    assets = []
    for path in sorted(folder.iterdir()):
        if not path.name.endswith((".exe", ".dmg", ".AppImage", ".tar.gz")):
            continue
        with path.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        assets.append({"name": path.name, "size": path.stat().st_size, "sha256": checksum})
    if not assets:
        raise ValueError("No verified release assets to sign")
    content = json.dumps({"version": version, "assets": assets}, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    signature = Ed25519PrivateKey.from_private_bytes(key_path.read_bytes()).sign(content)
    (folder / "release-manifest.json").write_bytes(content)
    (folder / "release-manifest.sig").write_bytes(base64.b64encode(signature) + b"\n")
    (folder / "SHA256SUMS.txt").write_text("".join(f"{item['sha256']}  {item['name']}\n" for item in assets), "utf-8")
    return len(assets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--version", default="3.3.0")
    args = parser.parse_args()
    print(f"Signed {sign(args.folder, args.key, args.version)} assets.")
