"""Parse and validate a config link (T024, FR-006 v1 list)."""
from __future__ import annotations

import base64
import json
from urllib.parse import urlsplit

from src.models import ExtractedConfig

V1_PROTOCOLS = {"vless", "vmess", "trojan", "ss", "ssr",
                "hysteria2", "hy2", "tuic", "wireguard"}


def _valid_vmess(netloc: str) -> bool:
    try:
        payload = json.loads(base64.b64decode(netloc + "==="))
    except Exception:
        return False
    return isinstance(payload, dict) and "add" in payload


def parse_link(raw: str, channel: str, post_id: int) -> ExtractedConfig:
    scheme = raw.split("://", 1)[0].lower() if "://" in raw else ""
    if scheme not in V1_PROTOCOLS:
        return ExtractedConfig(raw=raw, protocol="unknown",
                               source_channel=channel,
                               source_post_id=post_id, is_valid=False)
    try:
        parts = urlsplit(raw)
    except ValueError:
        return ExtractedConfig(raw=raw, protocol=scheme,
                               source_channel=channel,
                               source_post_id=post_id, is_valid=False)
    valid = bool(parts.hostname)
    if valid and scheme == "vmess":
        valid = _valid_vmess(parts.netloc)
    return ExtractedConfig(raw=raw, protocol=scheme,
                           source_channel=channel,
                           source_post_id=post_id, is_valid=valid)
