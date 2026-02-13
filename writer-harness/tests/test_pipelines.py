"""Tests for harness.pipelines.draft and harness.pipelines.revise."""
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from pydantic import ValidationError
from harness.pipelines.draft import load_continuity_ledger, extract_seed_text


# ── load_continuity_ledger ──────────────────────────────────────────
class TestLoadContinuityLedger:
    def test_missing_file_raises(self, tmp_path):
        # The fallback passes only location_current and who_present,
        # but ContinuityLedger requires time_of_day, date_or_day_count,
        # and elapsed_time_since_last_scene — so this raises ValidationError.
        with pytest.raises(ValidationError):
            load_continuity_ledger(tmp_path / "missing.yaml")

    def test_valid_file(self, tmp_path):
        data = {
            "location_current": "Salon",
            "time_of_day": "evening",
            "date_or_day_count": "Day 5",
            "elapsed_time_since_last_scene": "1 hour",
            "who_present": ["He", "Phoenix"],
        }
        state_path = tmp_path / "state.yaml"
        with open(state_path, "w") as f:
            yaml.dump(data, f)
        ledger = load_continuity_ledger(state_path)
        assert ledger.location_current == "Salon"
        assert "Phoenix" in ledger.who_present

    def test_empty_file_raises(self, tmp_path):
        # Empty YAML yields None → {} → missing required fields
        state_path = tmp_path / "state.yaml"
        state_path.write_text("")
        with pytest.raises(ValidationError):
            load_continuity_ledger(state_path)


# ── extract_seed_text ───────────────────────────────────────────────
class TestExtractSeedText:
    def test_with_scene_header(self):
        content = "<!-- state info -->\n\n# Scene 0001 — Test\n\nShe opened the door."
        seed = extract_seed_text(content)
        assert seed == "She opened the door."

    def test_without_scene_header(self):
        content = "Just plain text here."
        seed = extract_seed_text(content)
        assert seed == "Just plain text here."

    def test_multiline_seed(self):
        content = "# Scene 0002 — Title\n\nLine one.\nLine two.\nLine three."
        seed = extract_seed_text(content)
        assert "Line one." in seed
        assert "Line three." in seed

    def test_empty_seed(self):
        content = "# Scene 0001 — Title\n"
        seed = extract_seed_text(content)
        assert seed == ""


# ── draft_scene (integration with mocks) ────────────────────────────
class TestDraftScene:
    def _setup_workspace(self, tmp_path):
        """Create a minimal workspace for draft testing."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "lore").mkdir()
        (workspace / "scenes").mkdir()
        (workspace / "outputs").mkdir()

        state = {
            "location_current": "Library",
            "time_of_day": "afternoon",
            "date_or_day_count": "Day 1",
            "elapsed_time_since_last_scene": "10 minutes",
            "who_present": ["Alice"],
        }
        with open(workspace / "state.yaml", "w") as f:
            yaml.dump(state, f)

        rules = {"hard_rules": {}, "soft_preferences": {}}
        with open(workspace / "style_rules.yaml", "w") as f:
            yaml.dump(rules, f)

        banned = {"banned_regex": [], "warn_regex": []}
        with open(workspace / "banned_phrases.yaml", "w") as f:
            yaml.dump(banned, f)

        scene_path = workspace / "scenes" / "0001_scene.md"
        scene_path.write_text("# Scene 0001 — Test\n\nAlice entered the Library.")

        return workspace, scene_path

    @patch("harness.pipelines.draft.get_provider")
    @patch("harness.pipelines.draft.settings")
    def test_draft_scene_returns_result(self, mock_settings, mock_get_provider, tmp_path):
        workspace, scene_path = self._setup_workspace(tmp_path)

        mock_settings.workspace_root = workspace
        mock_settings.max_tokens = 1000
        mock_settings.provider = "anthropic"
        mock_settings.anthropic_api_key = "test"
        mock_settings.openai_api_key = ""
        mock_settings.model_name = "claude-3"

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "Alice sat in the Library and opened a book."
        mock_get_provider.return_value = mock_provider

        from harness.pipelines.draft import draft_scene
        result = draft_scene(scene_path, workspace_root=workspace, use_lore=False)

        assert "draft_text" in result
        assert "style_violations" in result
        assert "continuity_violations" in result
        assert result["draft_text"] == "Alice sat in the Library and opened a book."


# ── revise_draft (integration with mocks) ───────────────────────────
class TestReviseDraft:
    def _setup_workspace(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        state = {
            "location_current": "Library",
            "time_of_day": "afternoon",
            "date_or_day_count": "Day 1",
            "elapsed_time_since_last_scene": "10 minutes",
            "who_present": ["Alice"],
        }
        with open(workspace / "state.yaml", "w") as f:
            yaml.dump(state, f)

        rules = {"hard_rules": {}, "soft_preferences": {}}
        with open(workspace / "style_rules.yaml", "w") as f:
            yaml.dump(rules, f)

        banned = {"banned_regex": [], "warn_regex": []}
        with open(workspace / "banned_phrases.yaml", "w") as f:
            yaml.dump(banned, f)

        return workspace

    @patch("harness.pipelines.revise.get_provider")
    @patch("harness.pipelines.revise.settings")
    def test_revise_returns_result(self, mock_settings, mock_get_provider, tmp_path):
        workspace = self._setup_workspace(tmp_path)

        mock_settings.workspace_root = workspace
        mock_settings.max_tokens = 1000
        mock_settings.provider = "anthropic"
        mock_settings.anthropic_api_key = "test"
        mock_settings.openai_api_key = ""
        mock_settings.model_name = "claude-3"

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "Alice sat in the Library reading quietly."
        mock_get_provider.return_value = mock_provider

        from harness.pipelines.revise import revise_draft
        result = revise_draft(
            "Alice sat in the Library. Her breath hitched.",
            workspace_root=workspace,
        )

        assert "revised_text" in result
        assert "style_violations" in result
        assert "continuity_violations" in result
