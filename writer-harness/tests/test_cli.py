"""Tests for harness.cli — Click CLI commands."""
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from harness.cli import cli, create_workspace


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
