"""Unit tests for per-destination templates and limits (T033)."""
from src.filtering.cleaner import Cleaner
from src.formatting.message import build_message, get_template
from src.models import (Destination, ExtractedConfig, FilterRule, Location,
                        TestResult)


def _parts():
    cfg = ExtractedConfig(raw="vless://u@h:443#n", protocol="vless",
                          source_channel="c", source_post_id=1,
                          exact_hash="h", is_valid=True)
    loc = Location(country_code="DE", region=None, source="geoip",
                   display="آلمان")
    res = TestResult(status="success", latency_ms=124,
                     checked_at="t", error_class=None)
    dest = Destination(id="main", chat="@mydest", enabled=True,
                       sender="bot_api", quarantine=False)
    return cfg, loc, res, dest


def test_default_template_contents():
    body = build_message(*_parts())
    assert "vless://u@h:443#n" in body
    assert "آلمان" in body and "موفق" in body and "124" in body
    assert "@mydest" in body


def test_username_can_be_disabled():
    cfg, loc, res, dest = _parts()
    dest.append_username = False
    assert "@mydest" not in build_message(cfg, loc, res, dest)


def test_custom_template():
    cfg, loc, res, dest = _parts()
    body = build_message(cfg, loc, res, dest,
                         template="{config}@{location}")
    assert body == "vless://u@h:443#n@آلمان"


def test_long_message_keeps_config():
    cfg, loc, res, dest = _parts()
    cfg.raw = "vless://" + "x" * 4000 + "@h:443"
    body = build_message(cfg, loc, res, dest)
    assert len(body) <= 4096
    assert cfg.raw in body


def test_unknown_template_falls_back():
    assert get_template("nope") == get_template("default")


def test_destination_extra_rules():
    # رفتار T049: قوانین مستقل مقصد روی پیام نهایی اعمال می‌شود.
    cfg, loc, res, dest = _parts()
    dest.rules = [FilterRule(type="exact", pattern="تبلیغات",
                             scope="both", enabled=True)]
    body = build_message(cfg, loc, res, dest,
                         template="{config} تبلیغات")
    cleaned = Cleaner(dest.rules).clean(body, scope="text")
    assert "تبلیغات" not in cleaned
    assert cfg.raw in cleaned
