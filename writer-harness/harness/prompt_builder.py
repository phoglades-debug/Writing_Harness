from typing import Optional, List
from harness.models import ContinuityLedger, StyleRules


class PromptBuilder:
    """Assembles prompts with clearly delineated sections."""

    def __init__(self):
        self.sections = {}

    def add_system(self, text: str) -> "PromptBuilder":
        """Add system context."""
        self.sections["SYSTEM"] = text
        return self

    def add_continuity_ledger(self, ledger: ContinuityLedger) -> "PromptBuilder":
        """Add current story state as JSON."""
        ledger_json = ledger.model_dump_json(indent=2)
        self.sections["CONTINUITY_LEDGER"] = f"```json\n{ledger_json}\n```"
        return self

    def add_style_rules(self, rules: StyleRules) -> "PromptBuilder":
        """Add hard rules and soft preferences."""
        text = ""

        text += "## HARD RULES (MUST ENFORCE):\n\n"
        for category, rules_list in rules.hard_rules.items():
            text += f"### {category}\n"
            if isinstance(rules_list, list):
                for rule in rules_list:
                    text += f"- {rule}\n"
            else:
                text += f"- {rules_list}\n"
            text += "\n"

        text += "## SOFT PREFERENCES (GUIDANCE):\n\n"
        for category, prefs_list in rules.soft_preferences.items():
            text += f"### {category}\n"
            if isinstance(prefs_list, list):
                for pref in prefs_list:
                    text += f"- {pref}\n"
            else:
                text += f"- {prefs_list}\n"
            text += "\n"

        if hasattr(rules, 'output_targets'):
            text += "## OUTPUT TARGETS:\n"
            targets = rules.output_targets
            if isinstance(targets, dict):
                if 'length_words' in targets:
                    length = targets['length_words']
                    if isinstance(length, list):
                        text += f"- Target length: {length[0]}–{length[1]} words\n"

        self.sections["STYLE_RULES"] = text
        return self

    def add_lore_snippets(self, snippets: List[str]) -> "PromptBuilder":
        """Add retrieved lore context."""
        if not snippets:
            self.sections["LORE"] = "(No lore retrieved or disabled)"
        else:
            text = "## RELEVANT STORY NOTES:\n\n"
            for i, snippet in enumerate(snippets, 1):
                text += f"[{i}]\n{snippet}\n\n"
            self.sections["LORE"] = text
        return self

    def add_user_seed(self, seed_text: str) -> "PromptBuilder":
        """Add user's scene seed."""
        self.sections["SEED"] = seed_text
        return self

    def add_task(self, task_text: str) -> "PromptBuilder":
        """Add the generation task."""
        self.sections["TASK"] = task_text
        return self

    def build(self) -> str:
        """Assemble final prompt."""
        prompt = ""
        order = [
            "SYSTEM",
            "CONTINUITY_LEDGER",
            "STYLE_RULES",
            "VIOLATIONS",
            "DRAFT_TEXT",
            "LORE",
            "SEED",
            "TASK",
        ]

        for key in order:
            if key in self.sections:
                prompt += f"\n## {key}\n\n{self.sections[key]}\n"

        return prompt


def build_draft_prompt(
    ledger: ContinuityLedger,
    rules: StyleRules,
    seed_text: str,
    lore_snippets: Optional[List[str]] = None,
) -> str:
    """Build a prompt for the draft pass."""
    builder = PromptBuilder()
    builder.add_system(
        """You are a writing assistant for controlled, high-tension prose.

Your role is to continue a scene while strictly respecting:
1. The Continuity Ledger (location, time, characters, logistics)
2. Hard Rules (POV, no editorializing, no object anthropomorphism, scene containment, etc.)
3. The tone profile and scene goal

CRITICAL CONSTRAINTS:
- Output prose only. No meta-commentary, no disclaimers.
- Do not violate the Continuity Ledger. It is truth.
- No second-person address. Use third-person or first-person only.
- Do not break the fourth wall. No reference to "the reader", "the story", "tension", or narrative mechanics.
- Do not explain or moralize the dynamic. Show behavior.
- Stay inside character POV and observable action only. No summary, no diagnosis, no character typing.
- Inanimate objects do not emote, symbolize, or act.
- Dialogue is sparse. No monologues.
- Avoid clichés: breath hitches, heart races, trembling, etc.

SCENE CONTAINMENT (CRITICAL):
- Do NOT change location unless explicitly instructed in the seed or justified by dialogue.
- Do NOT introduce backstory events mid-scene unless directly relevant to current dialogue.
- Do NOT insert historical exposition. Stay in the present moment of the scene.
- Do NOT reference past events unless characters are actively discussing them now.
- If backstory is necessary, it must emerge through dialogue, not narration.

STYLE:
- Clean sentences. Minimal adjectives.
- Prefer micro-actions: pauses, gaze timing, stillness, proximity.
- If luxury appears, render it via precision and logistics, not spectacle.
- When in doubt, stay in-scene. Show behavior. Let implication stand.

ANTI-META RULE: Never step outside the scene to explain, summarize, or name emotional/relational states.
Every sentence must be observable action or dialogue. No author voice."""
    )

    builder.add_continuity_ledger(ledger)
    builder.add_style_rules(rules)
    builder.add_lore_snippets(lore_snippets or [])
    builder.add_user_seed(seed_text)
    builder.add_task(
        f"""Generate the next 600–1200 words of this scene.

SCENE LOCATION (MUST NOT CHANGE): {ledger.location_current}

CRITICAL ANTI-META RULES:
- No "the reader", "the story", "tension escalates", "the mood", "this reveals", etc.
- No character summary or typing ("she was the type to...").
- No explaining what behavior means. Show it.
- Every line must be action, dialogue, or pure observation inside POV.
- NO BACKSTORY EXPOSITION. Stay in the present moment.
- NO LOCATION CHANGES unless explicitly prompted.
- If past events matter, show their impact on current behavior (in dialogue, not narration).

REQUIREMENTS:
- Prose only. No commentary or explanation.
- Obey all Hard Rules strictly, especially scene_containment.
- Respect Continuity Ledger absolutely.
- Maintain tone and scene goal.
- Continue seamlessly from the seed.
- Focus on: behavior, timing, control, micro-actions, what is observable.
- Do not introduce new locations, major plot twists, or characters without justification.
- Keep the scene TIGHT. Every beat advances the current moment, not context.

Output clean prose. Nothing else."""
    )
    return builder.build()


def build_revise_prompt(
    draft_text: str,
    style_violations: List[str],
    continuity_violations: List[str],
    ledger: ContinuityLedger,
    rules: StyleRules,
) -> str:
    """Build a prompt for the revise pass."""
    builder = PromptBuilder()
    builder.add_system(
        """You are a revision assistant. Your job is to rewrite prose to fix violations while preserving scene intent.

CRITICAL:
- Fix all listed violations.
- Preserve the plot, characters, and voice.
- Do NOT introduce new scenes, characters, or plot changes.
- Do NOT change location or timeline unless absolutely necessary.
- Do NOT step outside the scene to explain, comment, or summarize.
- Do NOT insert backstory or historical exposition.
- Output prose only."""
    )
    builder.add_continuity_ledger(ledger)
    builder.add_style_rules(rules)

    violations_text = "## VIOLATIONS TO FIX:\n\n"

    if style_violations:
        violations_text += "### STYLE VIOLATIONS:\n"
        for v in style_violations:
            violations_text += f"- {v}\n"
        violations_text += "\n"

    if continuity_violations:
        violations_text += "### CONTINUITY VIOLATIONS:\n"
        for v in continuity_violations:
            violations_text += f"- {v}\n"
        violations_text += "\n"

    if not style_violations and not continuity_violations:
        violations_text += "No violations found. Light revision for polish.\n"

    builder.sections["VIOLATIONS"] = violations_text
    builder.sections["DRAFT_TEXT"] = f"```\n{draft_text}\n```"

    builder.add_task(
        f"""Rewrite the draft above to fix all violations while preserving intent and voice.

SCENE LOCATION (MUST NOT CHANGE): {ledger.location_current}

ANTI-META CRITICAL: Do not add any author commentary, narrative explanation, or meta-reference.
SCENE CONTAINMENT CRITICAL: Do not introduce backstory, flashbacks, or location changes.
Fix violations by rewriting prose only. Stay inside the scene. Stay inside character POV.

Output the revised prose only. No commentary."""
    )
    return builder.build()
