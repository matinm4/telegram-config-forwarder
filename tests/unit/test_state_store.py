"""Unit tests for atomic state storage (T008)."""
from src.persistence.state_store import StateStore
from src.models import RunRecord


def test_defaults_on_missing_file(tmp_path):
    store = StateStore(str(tmp_path / "state.json"))
    store.load()
    assert store.get_last_id("nope") == 0
    assert store.is_published("abc") is False


def test_last_id_roundtrip(tmp_path):
    p = str(tmp_path / "state.json")
    s1 = StateStore(p)
    s1.load()
    s1.set_last_id("src1", 101)
    s1.save()
    s2 = StateStore(p)
    s2.load()
    assert s2.get_last_id("src1") == 101


def test_published_hashes(tmp_path):
    p = str(tmp_path / "state.json")
    s1 = StateStore(p)
    s1.load()
    s1.mark_published("h1")
    s1.mark_published("h1")  # duplicate add is idempotent
    assert s1.is_published("h1") is True
    s1.save()
    s2 = StateStore(p)
    s2.load()
    assert s2.is_published("h1") is True
    assert s2.is_published("h2") is False


def test_cursor_and_runs(tmp_path):
    p = str(tmp_path / "state.json")
    s = StateStore(p)
    s.load()
    assert s.advance_cursor(2) == 2
    s.append_run(RunRecord(started_at="2026-09-23T00:00:00",
                           finished_at="2026-09-23T00:01:00", sent=3))
    s.save()
    s2 = StateStore(p)
    s2.load()
    assert s2.state.distribution_cursor == 2
    assert len(s2.state.runs) == 1
