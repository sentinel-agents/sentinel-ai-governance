from __future__ import annotations

import logging

import requests

WEB3_STORAGE_UPLOAD_URL = "https://api.web3.storage/upload"
LOGGER = logging.getLogger(__name__)


def upload_json(canonical_json_bytes: bytes, token: str) -> str:
    """Upload canonical governance JSON to web3.storage and return CID."""
    if not token:
        return ""

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            WEB3_STORAGE_UPLOAD_URL,
            headers=headers,
            data=canonical_json_bytes,
            timeout=30,
        )
        response.raise_for_status()
        if response.status_code != 200:
            LOGGER.warning(
                "web3.storage unexpected status %s: %s",
                response.status_code,
                response.text,
            )
            return ""
    except requests.RequestException as exc:
        LOGGER.warning("web3.storage upload failed: %s", exc)
        return ""

    try:
        payload = response.json()
    except ValueError as exc:
        LOGGER.warning("Invalid JSON from web3.storage: %s", exc)
        return ""

    cid = (
        payload.get("cid")
        or payload.get("value", {}).get("cid")
        or payload.get("value", {}).get("root", {}).get("cid")
        or payload.get("value", {}).get("root", {}).get("/")
    )

    if not isinstance(cid, str):
        return ""

    return cid.strip()
