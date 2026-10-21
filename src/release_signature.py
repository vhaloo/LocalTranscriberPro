"""Independent Ed25519 publisher verification for update manifests."""
from __future__ import annotations

import base64
import json

PUBLIC_KEY = "5uWAidftLcjB2DUS+zE3d3K51c3Yr0nw4ViYi5faP54="


def verify_manifest(content, signature, version, filename, size, public_key=None):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if len(content) > 256 * 1024 or len(signature) > 200:
        raise ValueError("Oversized signed update manifest")
    try:
        key = base64.b64decode(public_key or PUBLIC_KEY, validate=True)
        Ed25519PublicKey.from_public_bytes(key).verify(base64.b64decode(signature.strip(), validate=True), content)
        payload = json.loads(content)
        if payload["version"] != version:
            raise ValueError("Signed update version mismatch")
        matches = [item for item in payload["assets"] if item["name"] == filename]
        if len(matches) != 1 or matches[0]["size"] != size:
            raise ValueError("Signed update size mismatch")
        import re
        checksum = matches[0]["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("Invalid signed checksum")
        return checksum
    except Exception as error:
        raise ValueError("Publisher signature verification failed") from error
