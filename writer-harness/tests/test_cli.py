"""Tests for harness.cli — Click CLI commands."""
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from harness.cli import cli, create_workspace
from harness.models import LintViolation


# ── create_workspace ────────────────────────────────────────────────
class TestCreateWorkspace:
    def test_creates_directories(self, tmp_path):
        ws = tmp_path / "workspace"
        create_workspace(ws)
        assert (ws / "lore").is_dir()
        assert (ws / "scenes").is_dir()
        assert (ws / "outputs").is_dir()

    def test_creates_state_yaml(self, tmp_path):
        ws = tmp_path / "workspace"
        create_workspace(ws)
        state_path = ws / "state.yaml"
        assert state_path.exists()
        with open(state_path) as f:
            data = yaml.safe_load(f)
        assert "location_current" in data
        assert "who_present" in data

    def test_creates_style_rules(self, tmp_path):
        ws = tmp_path / "workspace"
        create_workspace(ws)
        rules_path = ws / "style_rules.yaml"
        assert rules_path.exists()
        with open(rules_path) as f:
            data = yaml.safe_load(f)
        assert "hard_rules" in data
        assert "soft_preferences" in data

    def test_creates_banned_phrases(self, tmp_path):
        ws = tmp_path / "workspace"
        create_workspace(ws)
        banned_path = ws / "banned_phrases.yaml"
        assert banned_path.exists()
        with open(banned_path) as f:
            data = yaml.safe_load(f)
        assert "banned_regex" in data
        assert "warn_regex" in data

    def test_idempotent(self, tmp_path):
        ws = tmp_path / "workspace"
        create_workspace(ws)
        # modify state.yaml
        state_path = ws / "state.yaml"
        with open(state_path) as f:
            original = f.read()
        # call again — should not overwrite existing files
        create_workspace(ws)
        with open(state_path) as f:
            after = f.read()
        assert original == after


# ── CLI init command ────────────────────────────────────────────────
class TestCLIInit:
    @patch("harness.cli.settings")
    def test_init_command(self, mock_settings, tmp_path):
        ws = tmp_path / "workspace"
        mock_settings.workspace_root = ws
        runner = CliRunner()
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert (ws / "state.yaml").exists()


# ── CLI new-scene command ───────────────────────────────────────────
class TestCLINewScene:
    @patch("harness.cli.settings")
    def test_new_scene_creates_file(self, mock_settings, tmp_path):
        ws = tmp_path / "workspace"
        create_workspace(ws)
        mock_settings.workspace_root = ws
        runner = CliRunner()
        result = runner.invoke(cli, ["new-scene", "--title", "Test Scene"])
        assert result.exit_code == 0
        scenes = list((ws / "scenes").glob("*.md"))
        assert len(scenes) == 1
        content = scenes[0].read_text()
        assert "Test Scene" in content
        assert "Scene 0001" in content


# ── CLI lint command ────────────────────────────────────────────────
class TestCLILint:
    @patch("harness.cli.settings")
    def test_lint_clean_file(self, mock_settings, tmp_path):
        ws = tmp_path / "workspace"
        create_workspace(ws)
        mock_settings.workspace_root = ws

        text_file = tmp_path / "clean.txt"
        text_file.write_text("He sat in the chair at Novo-Ogaryovo. Phoenix watched. He waited.")

        runner = CliRunner()
        result = runner.invoke(cli, ["lint", str(text_file)])
        assert result.exit_code == 0

    @patch("harness.cli.settings")
    def test_lint_with_violations(self, mock_settings, tmp_path):
        ws = tmp_path / "workspace"
        create_workspace(ws)
        mock_settings.workspace_root = ws

        text_file = tmp_path / "bad.txt"
        text_file.write_text("Her breath hitched. The reader noticed.")

        runner = CliRunner()
        result = runner.invoke(cli, ["lint", str(text_file)])
        assert result.exit_code == 0
        assert "violation" in result.output.lower() or "ERROR" in result.output or "Banned" in result.output


# ── helpers ─────────────────────────────────────────────────────────
def _setup_workspace(tmp_path):
    """Create a workspace with all config files and a scene."""
    ws = tmp_path / "workspace"
    create_workspace(ws)
    (ws / "outputs").mkdir(exist_ok=True)

    scene_path = ws / "scenes" / "0001_scene.md"
    scene_path.write_text("# Scene 0001 — Test\n\nHe walked into Novo-Ogaryovo.")
    return ws, scene_path


# ── CLI draft command ───────────────────────────────────────────────
class TestCLIDraft:
    @patch("harness.cli.draft_scene")
    @patch("harness.cli.settings")
    def test_draft_clean(self, mock_settings, mock_draft_scene, tmp_path):
        ws, scene_path = _setup_workspace(tmp_path)
        mock_settings.workspace_root = ws

        mock_draft_scene.return_value = {
            "draft_text": "He sat in Novo-Ogaryovo. Phoenix waited.",
            "style_violations": [],
            "continuity_violations": [],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["draft", str(scene_path)])
        assert result.exit_code == 0
        assert "Draft" in result.output

        # Verify output files created
        assert (ws / "outputs" / "0001_scene_draft.md").exists()
        assert (ws / "outputs" / "0001_style_lint.md").exists()
        assert (ws / "outputs" / "0001_continuity_lint.md").exists()

        # Verify draft content
        draft_content = (ws / "outputs" / "0001_scene_draft.md").read_text()
        assert "He sat in Novo-Ogaryovo" in draft_content

        # Verify clean lint reports
        style_report = (ws / "outputs" / "0001_style_lint.md").read_text()
        assert "No style violations" in style_report
        continuity_report = (ws / "outputs" / "0001_continuity_lint.md").read_text()
        assert "No continuity violations" in continuity_report

    @patch("harness.cli.draft_scene")
    @patch("harness.cli.settings")
    def test_draft_with_violations(self, mock_settings, mock_draft_scene, tmp_path):
        ws, scene_path = _setup_workspace(tmp_path)
        mock_settings.workspace_root = ws

        mock_draft_scene.return_value = {
            "draft_text": "Her breath hitched.",
            "style_violations": [
                LintViolation(
                    category="style", severity="error",
                    message="Banned: breath hitch",
                    line_number=1, context="Her breath hitched.",
                ),
            ],
            "continuity_violations": [
                LintViolation(
                    category="continuity", severity="warning",
                    message="Character 'Phoenix' supposed present but not mentioned",
                    context="Check if character should still be in scene",
                ),
            ],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["draft", str(scene_path)])
        assert result.exit_code == 0
        assert "1 style" in result.output
        assert "1 continuity" in result.output
        assert "revise" in result.output.lower()

        # Verify violation reports have content
        style_report = (ws / "outputs" / "0001_style_lint.md").read_text()
        assert "breath hitch" in style_report
        continuity_report = (ws / "outputs" / "0001_continuity_lint.md").read_text()
        assert "Phoenix" in continuity_report

    @patch("harness.cli.draft_scene")
    @patch("harness.cli.settings")
    def test_draft_error_handling(self, mock_settings, mock_draft_scene, tmp_path):
        ws, scene_path = _setup_workspace(tmp_path)
        mock_settings.workspace_root = ws
        mock_draft_scene.side_effect = RuntimeError("API connection failed")

        runner = CliRunner()
        result = runner.invoke(cli, ["draft", str(scene_path)])
        assert result.exit_code == 1


# ── CLI revise command ──────────────────────────────────────────────
class TestCLIRevise:
    @patch("harness.cli.revise_draft")
    @patch("harness.cli.settings")
    def test_revise_clean(self, mock_settings, mock_revise, tmp_path):
        ws, _ = _setup_workspace(tmp_path)
        mock_settings.workspace_root = ws

        draft_path = ws / "outputs" / "0001_scene_draft.md"
        draft_path.write_text("He sat in the salon, waiting.")

        mock_revise.return_value = {
            "revised_text": "He sat in the salon. He waited.",
            "style_violations": [],
            "continuity_violations": [],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["revise", str(draft_path)])
        assert result.exit_code == 0
        assert "Revised" in result.output

        # Verify output files
        assert (ws / "outputs" / "0001_scene_out.md").exists()
        assert (ws / "outputs" / "0001_revise_lint.md").exists()

        revised = (ws / "outputs" / "0001_scene_out.md").read_text()
        assert "He sat in the salon" in revised

        report = (ws / "outputs" / "0001_revise_lint.md").read_text()
        assert "None." in report

    @patch("harness.cli.revise_draft")
    @patch("harness.cli.settings")
    def test_revise_with_remaining_violations(self, mock_settings, mock_revise, tmp_path):
        ws, _ = _setup_workspace(tmp_path)
        mock_settings.workspace_root = ws

        draft_path = ws / "outputs" / "0001_scene_draft.md"
        draft_path.write_text("Her breath hitched.")

        mock_revise.return_value = {
            "revised_text": "She paused. You could see the tension.",
            "style_violations": [
                LintViolation(
                    category="style", severity="error",
                    message="Second-person pronoun 'you' in narration",
                    line_number=1, context="You could see the tension.",
                ),
            ],
            "continuity_violations": [],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["revise", str(draft_path)])
        assert result.exit_code == 0
        assert "1 style" in result.output

        report = (ws / "outputs" / "0001_revise_lint.md").read_text()
        assert "you" in report.lower()

    @patch("harness.cli.revise_draft")
    @patch("harness.cli.settings")
    def test_revise_with_continuity_violations(self, mock_settings, mock_revise, tmp_path):
        ws, _ = _setup_workspace(tmp_path)
        mock_settings.workspace_root = ws

        draft_path = ws / "outputs" / "0001_scene_draft.md"
        draft_path.write_text("She stood alone.")

        mock_revise.return_value = {
            "revised_text": "She stood alone in the room.",
            "style_violations": [],
            "continuity_violations": [
                LintViolation(
                    category="continuity", severity="warning",
                    message="Character 'Phoenix' supposed present but not mentioned",
                    context="Check if character should still be in scene",
                ),
            ],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["revise", str(draft_path)])
        assert result.exit_code == 0
        assert "1 continuity" in result.output

        report = (ws / "outputs" / "0001_revise_lint.md").read_text()
        assert "Phoenix" in report

    @patch("harness.cli.revise_draft")
    @patch("harness.cli.settings")
    def test_revise_strict_fails_on_violations(self, mock_settings, mock_revise, tmp_path):
        ws, _ = _setup_workspace(tmp_path)
        mock_settings.workspace_root = ws

        draft_path = ws / "outputs" / "0001_scene_draft.md"
        draft_path.write_text("Draft text.")

        mock_revise.return_value = {
            "revised_text": "Revised but still bad.",
            "style_violations": [
                LintViolation(
                    category="style", severity="error",
                    message="Some violation",
                    line_number=1, context="bad text",
                ),
            ],
            "continuity_violations": [],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["revise", "--strict", str(draft_path)])
        assert result.exit_code == 1
        assert "Strict mode" in result.output

    @patch("harness.cli.revise_draft")
    @patch("harness.cli.settings")
    def test_revise_strict_passes_when_clean(self, mock_settings, mock_revise, tmp_path):
        ws, _ = _setup_workspace(tmp_path)
        mock_settings.workspace_root = ws

        draft_path = ws / "outputs" / "0001_scene_draft.md"
        draft_path.write_text("Draft text.")

        mock_revise.return_value = {
            "revised_text": "Clean revised text.",
            "style_violations": [],
            "continuity_violations": [],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["revise", "--strict", str(draft_path)])
        assert result.exit_code == 0

    @patch("harness.cli.revise_draft")
    @patch("harness.cli.settings")
    def test_revise_error_handling(self, mock_settings, mock_revise, tmp_path):
        ws, _ = _setup_workspace(tmp_path)
        mock_settings.workspace_root = ws

        draft_path = ws / "outputs" / "0001_scene_draft.md"
        draft_path.write_text("Draft text.")
        mock_revise.side_effect = RuntimeError("API failed")

        runner = CliRunner()
        result = runner.invoke(cli, ["revise", str(draft_path)])
        assert result.exit_code == 1


# ── CLI init error handling ─────────────────────────────────────────
class TestCLIInitError:
    @patch("harness.cli.create_workspace")
    @patch("harness.cli.settings")
    def test_init_error(self, mock_settings, mock_create, tmp_path):
        mock_settings.workspace_root = tmp_path / "ws"
        mock_create.side_effect = PermissionError("Cannot create directory")

        runner = CliRunner()
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 1


# ── CLI new-scene error handling ────────────────────────────────────
class TestCLINewSceneError:
    @patch("harness.cli.settings")
    def test_new_scene_no_workspace(self, mock_settings, tmp_path):
        # Point to nonexistent workspace — load_continuity_ledger will raise
        mock_settings.workspace_root = tmp_path / "nonexistent"

        runner = CliRunner()
        result = runner.invoke(cli, ["new-scene", "--title", "Test"])
        assert result.exit_code == 1


# ── main() entry point ─────────────────────────────────────────────
class TestMain:
    @patch("harness.cli.cli")
    def test_main_calls_cli(self, mock_cli):
        from harness.cli import main
        main()
        mock_cli.assert_called_once()
