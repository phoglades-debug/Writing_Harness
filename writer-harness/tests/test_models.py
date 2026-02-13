"""Tests for harness.models — Pydantic data models."""
import pytest
from harness.models import ContinuityLedger, StyleRules, BannedPhrases, LintViolation


class TestContinuityLedger:
    def test_minimal_construction(self):
        ledger = ContinuityLedger(
            location_current="Library",
            time_of_day="morning",
            date_or_day_count="Day 1",
            elapsed_time_since_last_scene="10 minutes",
        )
        assert ledger.location_current == "Library"
        assert ledger.who_present == []
        assert ledger.location_previous is None
        assert ledger.devices_and_objects_in_scene == []

    def test_full_construction(self):
        ledger = ContinuityLedger(
            location_current="Salon",
            location_previous="Hallway",
            time_of_day="afternoon",
            date_or_day_count="Day 5",
            elapsed_time_since_last_scene="30 minutes",
            who_present=["Alice", "Bob"],
            transport_last_leg={"vehicle": "car", "from": "A", "to": "B"},
            relationship_elapsed_time="2 weeks",
            relationship_last_contact="yesterday",
            relationship_status_note="tense",
            physical_constraints={"injuries": [], "restraints": []},
            devices_and_objects_in_scene=["phone", "glass"],
            scene_goal="Confrontation",
            tone_profile="cold, restrained",
        )
        assert ledger.who_present == ["Alice", "Bob"]
        assert ledger.transport_last_leg["vehicle"] == "car"
        assert ledger.scene_goal == "Confrontation"

    def test_defaults(self):
        ledger = ContinuityLedger(
            location_current="X",
            time_of_day="night",
            date_or_day_count="Day 1",
            elapsed_time_since_last_scene="0",
        )
        assert ledger.scene_goal == ""
        assert ledger.tone_profile == ""
        assert ledger.physical_constraints is None

    def test_serialization_roundtrip(self):
        ledger = ContinuityLedger(
            location_current="Office",
            time_of_day="evening",
            date_or_day_count="Day 3",
            elapsed_time_since_last_scene="1 hour",
            who_present=["He", "Phoenix"],
        )
        data = ledger.model_dump()
        restored = ContinuityLedger(**data)
        assert restored.location_current == ledger.location_current
        assert restored.who_present == ledger.who_present


class TestStyleRules:
    def test_empty(self):
        rules = StyleRules()
        assert rules.hard_rules == {}
        assert rules.soft_preferences == {}
        assert rules.output_targets is None

    def test_with_data(self):
        rules = StyleRules(
            hard_rules={"pov": ["No second person"]},
            soft_preferences={"style": ["Clean sentences"]},
            output_targets={"length_words": [600, 1200]},
        )
        assert "pov" in rules.hard_rules
        assert rules.output_targets["length_words"] == [600, 1200]


class TestBannedPhrases:
    def test_empty(self):
        bp = BannedPhrases()
        assert bp.banned_regex == []
        assert bp.warn_regex == []

    def test_with_patterns(self):
        bp = BannedPhrases(
            banned_regex=[r"(?i)breath\s+hitch"],
            warn_regex=[r"(?i)cufflinks"],
        )
        assert len(bp.banned_regex) == 1
        assert len(bp.warn_regex) == 1


class TestLintViolation:
    def test_minimal(self):
        v = LintViolation(category="style", severity="error", message="Bad")
        assert v.line_number is None
        assert v.context == ""

    def test_full(self):
        v = LintViolation(
            category="continuity",
            severity="warning",
            message="Character missing",
            line_number=42,
            context="some text here",
        )
        assert v.category == "continuity"
        assert v.line_number == 42
