"""Unit tests for GeoIP location with fallback (T037, FR-011/012)."""
from src.location.geoip import GeoIpLocator
from src.models import ExtractedConfig


class FakeReader:
    def __init__(self, mapping):
        self._mapping = mapping

    def country(self, host):
        if host not in self._mapping:
            raise LookupError(host)
        code = self._mapping[host]

        class C:
            iso_code = code

        class R:
            country = C()

        return R()


def _cfg(raw="vless://u@example.com:443#n"):
    return ExtractedConfig(raw=raw, protocol="vless", source_channel="c",
                           source_post_id=1, exact_hash="h", is_valid=True)


def test_known_host_resolves():
    loc = GeoIpLocator(reader=FakeReader({"example.com": "DE"}),
                       fallback_display="Unknown")
    out = loc.locate(_cfg())
    assert out.country_code == "DE" and out.source == "geoip"


def test_unknown_host_falls_back():
    loc = GeoIpLocator(reader=FakeReader({}),
                       fallback_display="Unknown")
    out = loc.locate(_cfg())
    assert out.display == "Unknown" and out.source == "fallback"


def test_missing_reader_falls_back():
    loc = GeoIpLocator(reader=None, fallback_display="نامشخص")
    out = loc.locate(_cfg())
    assert out.display == "نامشخص"


def test_unparsable_link_falls_back():
    loc = GeoIpLocator(reader=FakeReader({"example.com": "DE"}),
                       fallback_display="Unknown")
    out = loc.locate(_cfg(raw="not a link"))
    assert out.source == "fallback"
