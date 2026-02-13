from pathlib import Path

from harness.config import settings
from harness.prompt_builder import build_revise_prompt
from harness.providers import get_provider
from harness.lint.rules import load_style_rules, load_banned_phrases
from harness.lint.style import lint_style
from harness.lint.continuity import lint_continuity
from harness.pipelines.draft import load_continuity_ledger


def revise_draft(
    draft_text: str,
    workspace_root: Path = settings.workspace_root,
) -> dict:
    """Revise a draft to fix violations."""
    state_path = workspace_root / "state.yaml"
    ledger = load_continuity_ledger(state_path)

    rules_path = workspace_root / "style_rules.yaml"
    rules = load_style_rules(rules_path)

    banned_path = workspace_root / "banned_phrases.yaml"
    banned = load_banned_phrases(banned_path)

    style_violations = lint_style(draft_text, banned, scene_location=ledger.location_current)
    continuity_violations = lint_continuity(draft_text, ledger)

    style_msgs = [v.message for v in style_violations]
    continuity_msgs = [v.message for v in continuity_violations]

    prompt = build_revise_prompt(draft_text, style_msgs, continuity_msgs, ledger, rules)

    settings.validate_provider()
    provider = get_provider(
        settings.provider,
        settings.anthropic_api_key or settings.openai_api_key,
        settings.model_name,
    )
    revised_text = provider.generate(prompt, max_tokens=settings.max_tokens)

    style_violations_after = lint_style(revised_text, banned, scene_location=ledger.location_current)
    continuity_violations_after = lint_continuity(revised_text, ledger)

    return {
        "revised_text": revised_text,
        "style_violations": style_violations_after,
        "continuity_violations": continuity_violations_after,
    }
