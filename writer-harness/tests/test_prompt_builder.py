"""Tests for harness.prompt_builder — prompt construction."""
import pytest
from harness.models import ContinuityLedger, StyleRules
from harness.prompt_builder import PromptBuilder, build_draft_prompt, build_revise_prompt


def _ledger():
    return ContinuityLedger(
        location_current="Library",
        time_of_day="afternoon",
        date_or_day_count="Day 3",
        elapsed_time_since_last_scene="30 minutes",
        who_present=["Alice", "Bob"],
        scene_goal="Confrontation",
        tone_profile="cold",
    )


def _rules():
    return StyleRules(
        hard_rules={"pov": ["No second person", "Stay in third person"]},
        soft_preferences={"style": ["Clean prose"]},
        output_targets={"length_words": [600, 1200]},
    )


# ── PromptBuilder ───────────────────────────────────────────────────
class TestPromptBuilder:
    def test_empty_build(self):
        pb = PromptBuilder()
        result = pb.build()
        assert result == ""

    def test_add_system(self):
        pb = PromptBuilder()
        pb.add_system("You are a writer.")
        result = pb.build()
        assert "SYSTEM" in result
        assert "You are a writer." in result

    def test_add_continuity_ledger(self):
        pb = PromptBuilder()
        pb.add_continuity_ledger(_ledger())
        result = pb.build()
        assert "CONTINUITY_LEDGER" in result
        assert "Library" in result
        assert "Alice" in result

    def test_add_style_rules(self):
        pb = PromptBuilder()
        pb.add_style_rules(_rules())
        result = pb.build()
        assert "HARD RULES" in result
        assert "No second person" in result
        assert "SOFT PREFERENCES" in result
        assert "OUTPUT TARGETS" in result

    def test_add_lore_snippets_empty(self):
        pb = PromptBuilder()
        pb.add_lore_snippets([])
        result = pb.build()
        assert "No lore retrieved" in result

    def test_add_lore_snippets(self):
        pb = PromptBuilder()
        pb.add_lore_snippets(["**Alice**\nShe is the protagonist."])
        result = pb.build()
        assert "Alice" in result
        assert "[1]" in result

    def test_add_user_seed(self):
        pb = PromptBuilder()
        pb.add_user_seed("She opened the door.")
        result = pb.build()
        assert "She opened the door." in result

    def test_section_ordering(self):
        pb = PromptBuilder()
        pb.add_task("Generate prose.")
        pb.add_system("You are a writer.")
        result = pb.build()
        # SYSTEM should appear before TASK
        assert result.index("SYSTEM") < result.index("TASK")

    def test_chaining(self):
        pb = PromptBuilder()
        result = pb.add_system("sys").add_user_seed("seed").add_task("task")
        assert result is pb  # returns self for chaining


# ── build_draft_prompt ──────────────────────────────────────────────
class TestBuildDraftPrompt:
    def test_contains_all_sections(self):
        prompt = build_draft_prompt(_ledger(), _rules(), "She entered the room.")
        assert "SYSTEM" in prompt
        assert "CONTINUITY_LEDGER" in prompt
        assert "STYLE_RULES" in prompt
        assert "SEED" in prompt
        assert "TASK" in prompt

    def test_contains_location(self):
        prompt = build_draft_prompt(_ledger(), _rules(), "She looked around.")
        assert "Library" in prompt

    def test_with_lore(self):
        prompt = build_draft_prompt(
            _ledger(), _rules(), "seed text",
            lore_snippets=["**Note**\nSome lore"],
        )
        assert "Some lore" in prompt

    def test_without_lore(self):
        prompt = build_draft_prompt(_ledger(), _rules(), "seed text")
        assert "No lore retrieved" in prompt

    def test_contains_anti_meta_rules(self):
        prompt = build_draft_prompt(_ledger(), _rules(), "seed")
        assert "ANTI-META" in prompt


# ── build_revise_prompt ─────────────────────────────────────────────
class TestBuildRevisePrompt:
    def test_contains_violations(self):
        prompt = build_revise_prompt(
            "draft text here",
            ["Banned: breath hitch"],
            ["Location missing"],
            _ledger(),
            _rules(),
        )
        assert "breath hitch" in prompt
        assert "Location missing" in prompt

    def test_no_violations(self):
        prompt = build_revise_prompt(
            "clean draft", [], [], _ledger(), _rules(),
        )
        assert "No violations found" in prompt

    def test_contains_draft_text(self):
        prompt = build_revise_prompt(
            "She looked out the window.",
            [], [], _ledger(), _rules(),
        )
        assert "She looked out the window." in prompt

    def test_system_mentions_revision(self):
        prompt = build_revise_prompt("draft", [], [], _ledger(), _rules())
        assert "revision assistant" in prompt

    def test_task_mentions_location(self):
        prompt = build_revise_prompt("draft", [], [], _ledger(), _rules())
        assert "Library" in prompt

    def test_task_mentions_anti_meta(self):
        prompt = build_revise_prompt("draft", [], [], _ledger(), _rules())
        assert "ANTI-META" in prompt

    def test_section_ordering(self):
        prompt = build_revise_prompt(
            "draft text",
            ["some violation"],
            [],
            _ledger(),
            _rules(),
        )
        # VIOLATIONS should appear before TASK
        assert prompt.index("VIOLATIONS") < prompt.index("TASK")
        # DRAFT_TEXT should appear before TASK
        assert prompt.index("DRAFT_TEXT") < prompt.index("TASK")
