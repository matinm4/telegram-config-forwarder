"""Find config links inside post text (T023)."""
from __future__ import annotations

import re

_LINK_RE = re.compile(
    r"(?:vless|vmess|trojan|ssr?|hysteria2|hy2|tuic|wireguard)"
    r"://[^\s<>\"']+",
    re.IGNORECASE,
)


def find_links(text: str) -> list[str]:
    """Return all config-looking URIs in order of appearance."""
    if not text:
        return []
    return _LINK_RE.findall(text)
