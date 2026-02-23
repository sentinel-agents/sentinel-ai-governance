from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

KEY_PATH = Path('.sentinel_ed25519_keypair.json')


def _encode_b64(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def _decode_b64(data_b64: str) -> bytes:
    return base64.b64decode(data_b64.encode('ascii'))


def load_or_create_keypair(key_path: Path | str = KEY_PATH) -> Tuple[bytes, bytes]:
    key_path = Path(key_path)
    if key_path.exists():
        document = json.loads(key_path.read_text())
        private_b64 = document['private_key']
        public_b64 = document['public_key']
        return _decode_b64(private_b64), _decode_b64(public_b64)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )
    public_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

    key_path.write_text(
        json.dumps(
            {
                'private_key': _encode_b64(private_bytes),
                'public_key': _encode_b64(public_bytes),
            },
            indent=2,
        )
    )

    return private_bytes, public_bytes


def sign_hash(private_key_bytes: bytes, sha256_post_hex: str) -> str:
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    message = sha256_post_hex.encode('utf-8')
    signature = private_key.sign(message)
    return _encode_b64(signature)


def public_key_b64(public_key_bytes: bytes) -> str:
    return _encode_b64(public_key_bytes)


def verify_signature(public_key_bytes: bytes, sha256_post_hex: str, signature_b64: str) -> bool:
    public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    message = sha256_post_hex.encode('utf-8')
    signature = _decode_b64(signature_b64)
    try:
        public_key.verify(signature, message)
        return True
    except Exception:  # noqa: BLE001
        return False
