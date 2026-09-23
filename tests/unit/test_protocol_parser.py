"""Unit tests for protocol parsing and validation (T018)."""
from src.extraction.protocol_parser import parse_link


def test_vless_valid():
    cfg = parse_link("vless://u@example.com:443?security=tls#n",
                     "ch", 10)
    assert cfg.is_valid and cfg.protocol == "vless"
    assert cfg.source_post_id == 10


def test_trojan_valid():
    cfg = parse_link("trojan://pw@example.com:443", "ch", 1)
    assert cfg.is_valid and cfg.protocol == "trojan"


def test_vmess_valid_base64():
    import base64
    payload = base64.b64encode(
        b'{"add":"example.com","port":"443"}').decode()
    cfg = parse_link(f"vmess://{payload}", "ch", 1)
    assert cfg.is_valid and cfg.protocol == "vmess"


def test_vmess_bad_base64_invalid():
    cfg = parse_link("vmess://!!!not-base64!!!", "ch", 1)
    assert cfg.is_valid is False


def test_unknown_scheme_invalid():
    cfg = parse_link("gopher://x@y:1", "ch", 1)
    assert cfg.is_valid is False
    assert cfg.protocol == "unknown"


def test_missing_host_invalid():
    cfg = parse_link("vless://", "ch", 1)
    assert cfg.is_valid is False
