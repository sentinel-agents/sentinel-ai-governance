from __future__ import annotations

import json
import logging
from typing import Any

import requests

PINATA_UPLOAD_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
LOGGER = logging.getLogger(__name__)


def upload_json(canonical_json_bytes: bytes, token: str) -> str:
    """Upload canonical governance JSON to Pinata and return CID."""
    if not token:
        return ""

    try:
        canonical_obj: Any = json.loads(canonical_json_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        LOGGER.warning("Failed to decode canonical payload for Pinata: %s", exc)
        return ""

    payload = {
        "pinataOptions": {"cidVersion": 1},
        "pinataContent": canonical_obj,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            PINATA_UPLOAD_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("Pinata upload failed: %s", exc)
        return ""

    try:
        pinata_json = response.json()
    except ValueError as exc:
        LOGGER.warning("Invalid JSON from Pinata: %s", exc)
        return ""

    cid = pinata_json.get("IpfsHash")
    if not isinstance(cid, str):
        return ""

    return cid.strip()
