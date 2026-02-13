import yaml
from pathlib import Path
from harness.models import StyleRules, BannedPhrases


def load_style_rules(path: Path) -> StyleRules:
    """Load style rules from YAML file."""
    if not path.exists():
        return StyleRules()

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    return StyleRules(
        hard_rules=data.get("hard_rules", {}),
        soft_preferences=data.get("soft_preferences", {}),
        output_targets=data.get("output_targets", None),
    )


def load_banned_phrases(path: Path) -> BannedPhrases:
    """Load banned phrases from YAML file."""
    if not path.exists():
        return BannedPhrases(banned_regex=[], warn_regex=[])

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    return BannedPhrases(
        banned_regex=data.get("banned_regex", []),
        warn_regex=data.get("warn_regex", []),
    )
