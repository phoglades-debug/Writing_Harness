"""Tests for harness.lint.rules — YAML config loading."""
import pytest
import yaml
from pathlib import Path
from harness.lint.rules import load_style_rules, load_banned_phrases


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


class TestLoadStyleRules:
    def test_missing_file_returns_defaults(self, tmp_dir):
        rules = load_style_rules(tmp_dir / "nonexistent.yaml")
        assert rules.hard_rules == {}
        assert rules.soft_preferences == {}
        assert rules.output_targets is None

    def test_empty_file(self, tmp_dir):
        path = tmp_dir / "style.yaml"
        path.write_text("")
        rules = load_style_rules(path)
        assert rules.hard_rules == {}

    def test_valid_file(self, tmp_dir):
        data = {
            "hard_rules": {"pov": ["No second person"]},
            "soft_preferences": {"style": ["Clean prose"]},
            "output_targets": {"length_words": [600, 1200]},
        }
        path = tmp_dir / "style.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)
        rules = load_style_rules(path)
        assert "pov" in rules.hard_rules
        assert rules.output_targets["length_words"] == [600, 1200]


class TestLoadBannedPhrases:
    def test_missing_file_returns_empty(self, tmp_dir):
        bp = load_banned_phrases(tmp_dir / "nonexistent.yaml")
        assert bp.banned_regex == []
        assert bp.warn_regex == []

    def test_empty_file(self, tmp_dir):
        path = tmp_dir / "banned.yaml"
        path.write_text("")
        bp = load_banned_phrases(path)
        assert bp.banned_regex == []

    def test_valid_file(self, tmp_dir):
        data = {
            "banned_regex": [r"(?i)breath\s+hitch", r"(?i)silence\s+pools"],
            "warn_regex": [r"(?i)cufflinks"],
        }
        path = tmp_dir / "banned.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)
        bp = load_banned_phrases(path)
        assert len(bp.banned_regex) == 2
        assert len(bp.warn_regex) == 1
