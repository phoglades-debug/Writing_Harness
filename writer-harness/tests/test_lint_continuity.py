"""Tests for harness.lint.continuity — continuity checking."""
import pytest
from harness.models import ContinuityLedger
from harness.lint.continuity import (
    lint_location_change,
    lint_who_present,
    lint_timeline,
    lint_continuity,
)


def _ledger(**overrides):
    defaults = dict(
        location_current="Library",
        time_of_day="afternoon",
        date_or_day_count="Day 3",
        elapsed_time_since_last_scene="30 minutes",
        who_present=["Alice", "Bob"],
    )
    defaults.update(overrides)
    return ContinuityLedger(**defaults)


# ── lint_location_change ────────────────────────────────────────────
class TestLintLocationChange:
    def test_location_mentioned(self):
        ledger = _ledger(location_current="Library")
        text = "They sat in the Library, surrounded by books. " * 3
        assert lint_location_change(text, ledger) == []

    def test_location_not_mentioned(self):
        ledger = _ledger(location_current="Library")
        text = "He walked across the room and looked outside. " * 3
        vs = lint_location_change(text, ledger)
        assert len(vs) == 1
        assert "Library" in vs[0].message

    def test_short_text_skipped(self):
        ledger = _ledger(location_current="Library")
        text = "Short."  # len < 100
        assert lint_location_change(text, ledger) == []

    def test_case_insensitive(self):
        ledger = _ledger(location_current="Library")
        text = "They were in the library, reading. " * 3
        assert lint_location_change(text, ledger) == []


# ── lint_who_present ────────────────────────────────────────────────
class TestLintWhoPresent:
    def test_all_mentioned(self):
        ledger = _ledger(who_present=["Alice", "Bob"])
        text = "Alice poured coffee. Bob nodded."
        assert lint_who_present(text, ledger) == []

    def test_character_missing(self):
        ledger = _ledger(who_present=["Alice", "Bob"])
        text = "Alice poured coffee and sat down."
        vs = lint_who_present(text, ledger)
        assert len(vs) == 1
        assert "Bob" in vs[0].message

    def test_generic_roles_skipped(self):
        ledger = _ledger(who_present=["Alice", "aide"])
        text = "Alice spoke softly."
        vs = lint_who_present(text, ledger)
        # "aide" should be skipped
        assert vs == []

    def test_staff_skipped(self):
        ledger = _ledger(who_present=["staff", "assistant", "attendant"])
        text = "The room was quiet."
        assert lint_who_present(text, ledger) == []

    def test_case_insensitive(self):
        ledger = _ledger(who_present=["Phoenix"])
        text = "phoenix sat in the corner, silent."
        assert lint_who_present(text, ledger) == []


# ── lint_timeline ───────────────────────────────────────────────────
class TestLintTimeline:
    def test_no_time_refs(self):
        ledger = _ledger(elapsed_time_since_last_scene="30 minutes")
        text = "She waited. Nothing happened."
        assert lint_timeline(text, ledger) == []

    def test_reasonable_time_ref(self):
        ledger = _ledger(elapsed_time_since_last_scene="30 minutes")
        text = "It had been 20 minutes since they arrived."
        assert lint_timeline(text, ledger) == []

    def test_excessive_time_ref(self):
        ledger = _ledger(elapsed_time_since_last_scene="30 minutes")
        text = "It felt like 500 minutes had passed."
        vs = lint_timeline(text, ledger)
        assert len(vs) == 1
        assert "500" in vs[0].message

    def test_no_elapsed_numeric(self):
        ledger = _ledger(elapsed_time_since_last_scene="unknown")
        text = "It had been 100 hours."
        # no numeric in elapsed → no check
        assert lint_timeline(text, ledger) == []

    def test_boundary_within_3x(self):
        ledger = _ledger(elapsed_time_since_last_scene="10 minutes")
        text = "It had been 30 minutes."  # exactly 3x, not > 3x
        assert lint_timeline(text, ledger) == []

    def test_boundary_beyond_3x(self):
        ledger = _ledger(elapsed_time_since_last_scene="10 minutes")
        text = "It had been 31 minutes."  # > 3x
        vs = lint_timeline(text, ledger)
        assert len(vs) == 1


# ── lint_continuity (aggregator) ────────────────────────────────────
class TestLintContinuity:
    def test_all_clean(self):
        ledger = _ledger(location_current="Library", who_present=["Alice"])
        text = "Alice sat in the Library, reading a book. " * 3
        assert lint_continuity(text, ledger) == []

    def test_combines_all(self):
        ledger = _ledger(
            location_current="Library",
            who_present=["Alice", "Bob"],
            elapsed_time_since_last_scene="10 minutes",
        )
        # missing location, missing Bob, excessive time
        text = "She stood alone for 500 minutes in an empty room. " * 3
        vs = lint_continuity(text, ledger)
        categories = {v.message for v in vs}
        assert len(vs) >= 2  # at least location + missing character
