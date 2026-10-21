"""Password-protected transcript snapshots; no private keys in preferences.

AES-GCM authenticates content and its format header. Scrypt parameters are
fixed by this version to bound work on untrusted input. Audio is not included.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

MAGIC = b"LTP-PRIVATE-1\n"
MAX_BYTES = 32 * 1024 * 1024


def _key(password, salt):
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    if len(password) < 10 or len(password) > 1024:
        raise ValueError("Use a password of 10–1024 characters; it cannot be recovered")
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(password.encode("utf-8"))


def encrypt_segments(segments, password):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    plaintext = json.dumps(segments, ensure_ascii=False).encode("utf-8")
    if len(plaintext) > MAX_BYTES:
        raise ValueError("Private session exceeds 32 MB")
    salt, nonce = os.urandom(16), os.urandom(12)
    header = MAGIC + salt + nonce
    return header + AESGCM(_key(password, salt)).encrypt(nonce, plaintext, header)


def decrypt_segments(content, password):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not content.startswith(MAGIC) or not len(MAGIC) + 44 <= len(content) <= MAX_BYTES + 200:
        raise ValueError("Invalid or oversized private session")
    start = len(MAGIC)
    salt, nonce = content[start:start + 16], content[start + 16:start + 28]
    header = content[:start + 28]
    value = json.loads(AESGCM(_key(password, salt)).decrypt(nonce, content[start + 28:], header))
    if not isinstance(value, list):
        raise ValueError("Invalid private session contents")
    from src.segments import validate_segments
    return validate_segments(value)


def save_private(path: Path, segments, password):
    content = encrypt_segments(segments, password)
    path.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".ltp-private-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
