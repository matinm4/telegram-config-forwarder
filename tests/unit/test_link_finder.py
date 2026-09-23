"""Unit tests for config link finding (T017)."""
from src.extraction.link_finder import find_links

SAMPLE = ("here vless://u@example.com:443?x=1#n and "
          "trojan://p@example.com:443 plus not-a-link")


def test_finds_all_links():
    links = find_links(SAMPLE)
    assert len(links) == 2
    assert links[0].startswith("vless://")
    assert links[1].startswith("trojan://")


def test_ignores_plain_text():
    assert find_links("just some text 123") == []


def test_multiple_protocols():
    text = "ss://a@h:1 vmess://e30= tuic://t@h:443"
    assert len(find_links(text)) == 3


def test_empty():
    assert find_links("") == []
