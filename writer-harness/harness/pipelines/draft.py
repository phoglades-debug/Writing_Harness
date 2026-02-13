from pathlib import Path
import yaml

import harness.config as _cfg
from harness.models import ContinuityLedger
from harness.prompt_builder import build_draft_prompt
from harness.providers import get_provider
from harness.lore.retrieve import retrieve_lore, extract_keywords
from harness.lint.rules import load_style_rules, load_banned_phrases
from harness.lint.style import lint_style
from harness.lint.continuity import lint_continuity


def load_continuity_ledger(state_path: Path) -> ContinuityLedger:
    """Load ledger from YAML."""
    if not state_path.exists():
        return ContinuityLedger(
            location_current="Unknown",
            time_of_day="unknown",
            date_or_day_count="unknown",
            elapsed_time_since_last_scene="unknown",
            who_present=[],
        )

    with open(state_path, "r") as f:
        data = yaml.safe_load(f) or {}

    if not data:
        return ContinuityLedger(
            location_current="Unknown",
            time_of_day="unknown",
            date_or_day_count="unknown",
            elapsed_time_since_last_scene="unknown",
            who_present=[],
        )

    return ContinuityLedger(**data)


def extract_seed_text(scene_content: str) -> str:
    """Extract seed text from scene file."""
    lines = scene_content.split('\n')
    seed_start = 0

    for i, line in enumerate(lines):
        if line.startswith('# Scene '):
            seed_start = i + 1
            break

    return '\n'.join(lines[seed_start:]).strip()


def draft_scene(
    scene_path: Path,
    workspace_root: Path = _cfg.settings.workspace_root,
    lore_k: int = 8,
    use_lore: bool = True,
) -> dict:
    """Generate a draft of a scene."""
    with open(scene_path, "r") as f:
        scene_content = f.read()

    seed_text = extract_seed_text(scene_content)

    state_path = workspace_root / "state.yaml"
    ledger = load_continuity_ledger(state_path)

    rules_path = workspace_root / "style_rules.yaml"
    rules = load_style_rules(rules_path)

    banned_path = workspace_root / "banned_phrases.yaml"
    banned = load_banned_phrases(banned_path)

    lore_snippets = []
    if use_lore:
        keywords = extract_keywords(seed_text + " " + ledger.location_current)
        lore_dir = workspace_root / "lore"
        lore_snippets = retrieve_lore(keywords, lore_dir, top_k=lore_k)

    prompt = build_draft_prompt(ledger, rules, seed_text, lore_snippets)

    _cfg.settings.validate_provider()
    provider = get_provider(
        _cfg.settings.provider,
        _cfg.settings.anthropic_api_key or _cfg.settings.openai_api_key,
        _cfg.settings.model_name,
    )
    draft_text = provider.generate(prompt, max_tokens=_cfg.settings.max_tokens)

    style_violations = lint_style(draft_text, banned, scene_location=ledger.location_current)
    continuity_violations = lint_continuity(draft_text, ledger)

    return {
        "draft_text": draft_text,
        "style_violations": style_violations,
        "continuity_violations": continuity_violations,
    }
