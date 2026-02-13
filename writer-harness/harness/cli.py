import click
import yaml
from pathlib import Path
from datetime import datetime
from rich.console import Console

from harness.config import settings
from harness.lint.rules import load_style_rules, load_banned_phrases
from harness.pipelines.draft import draft_scene, load_continuity_ledger
from harness.pipelines.revise import revise_draft
from harness.lint.style import lint_style
from harness.lint.continuity import lint_continuity

console = Console()


def create_workspace(workspace_root: Path):
    """Initialize workspace with starter files."""
    workspace_root.mkdir(exist_ok=True)

    (workspace_root / "lore").mkdir(exist_ok=True)
    (workspace_root / "scenes").mkdir(exist_ok=True)
    (workspace_root / "outputs").mkdir(exist_ok=True)

    state_path = workspace_root / "state.yaml"
    if not state_path.exists():
        starter_state = {
            "location_current": "Novo-Ogaryovo — private salon",
            "location_previous": "Novo-Ogaryovo — bathing wing antechamber",
            "time_of_day": "early afternoon",
            "date_or_day_count": "Day 17",
            "elapsed_time_since_last_scene": "25 minutes",
            "who_present": ["He", "Phoenix", "Aide (outside door)"],
            "transport_last_leg": {
                "vehicle": "helicopter",
                "from": "Moscow",
                "to": "Novo-Ogaryovo",
                "duration": "38 minutes"
            },
            "relationship_elapsed_time": "3 months since first contact",
            "relationship_last_contact": "10 days since last in-person meeting",
            "relationship_status_note": "proximity is controlled; contact is intermittent",
            "physical_constraints": {
                "injuries": ["Phoenix: faint bruising at wrists (older, healing)"],
                "restraints": [],
                "fatigue": ["Phoenix: mild post-swim fatigue"]
            },
            "devices_and_objects_in_scene": [
                "His phone on side table (silent)",
                "Water carafe and glass on low table"
            ],
            "scene_goal": "A controlled confrontation. He tests boundaries; she resists.",
            "tone_profile": "restrained, observational, unsentimental",
        }
        with open(state_path, "w") as f:
            yaml.dump(starter_state, f, default_flow_style=False)
        console.print(f"[green]✓[/green] Created {state_path}")

    rules_path = workspace_root / "style_rules.yaml"
    if not rules_path.exists():
        starter_rules = {
            "hard_rules": {
                "pov_and_address": [
                    "Narration is first person (I) or third person (he/she). Never second person outside direct dialogue.",
                    "Do not address the reader as 'you' in narration."
                ],
                "continuity_priority": [
                    "Continuity Ledger overrides all other text. Do not contradict it.",
                    "No location changes without explicit travel/transition.",
                    "No time jumps without explicit elapsed time."
                ],
                "anti_cheese_editorializing": [
                    "No thesis/diagnosis sentences (e.g., 'What he won't admit:', 'The truth is', 'He realizes', 'She realizes').",
                    "Do not name abstract relational states (victory, surrender, dominance, power) as authorial conclusions.",
                    "Do not moralize or explain the dynamic. Show behavior and let implication stand."
                ],
                "anti_haunted_objects": [
                    "Inanimate objects do not emote, symbolize, mirror emotion, or 'do work'.",
                    "Do not add decorative environmental details unless operationally relevant to action or continuity.",
                    "Avoid metaphor patterns that animate the room (e.g., silence pools/spills/hangs, light interrogates, walls listen)."
                ],
                "physiological_cliches": [
                    "Avoid melodramatic physiological cues ('breath hitches', gasping, shuddering, trembling) unless explicitly warranted.",
                    "If physiology is used, prefer neutral metrics (pulse rate, temperature, dry mouth, muscle tension)."
                ],
                "banned_domains": [
                    "Avoid strategic/game metaphors (chess, grandmaster, pawn, gambit) unless explicitly requested.",
                    "Avoid medals/trophies as shorthand props."
                ],
                "dialogue_and_exposition": [
                    "Dialogue is sparse and intentional. No monologues explaining motives.",
                    "Do not over-explain backstory. Do not recap unless necessary for immediate comprehension."
                ],
                "luxury_rendering": [
                    "Luxury is conveyed through precision, maintenance, and logistics—not spectacle or symbolism.",
                    "Staff are mostly invisible; service is frictionless; spaces are controlled (light, sound, temperature)."
                ],
                "anti_meta": [
                    "No references to 'the reader', 'the story', 'the narrative', or authorial intent.",
                    "Do not explain how tension should escalate.",
                    "Do not summarize characters or motivations mid-scene.",
                    "Stay inside character POV and observable behavior only."
                ],
                "scene_containment": [
                    "Do not change location unless explicitly instructed by user seed or justified by dialogue.",
                    "Do not introduce new backstory events unless directly relevant to immediate dialogue.",
                    "Do not insert historical exposition mid-scene. Stay in the present moment of the scene.",
                    "Do not reference past events unless they are being actively discussed in the current scene."
                ]
            },
            "soft_preferences": {
                "tension_tools": [
                    "Prefer micro-actions over metaphors: pauses, gaze timing, stillness, proximity.",
                    "Use silence as a beat, not a poetic object.",
                    "Show control via behavior and access, not via décor."
                ],
                "style": [
                    "Clean sentences. Minimal adjectives. No purple prose.",
                    "If a sentence reads like back-cover copy, rewrite it colder."
                ],
                "scene_management": [
                    "When uncertain, stay in-scene. Do not introduce new locations, characters, or plot devices.",
                    "If something must be implied, imply it once and move on."
                ]
            },
            "output_targets": {
                "length_words": [600, 1200],
                "include_continuity_footer": False
            }
        }
        with open(rules_path, "w") as f:
            yaml.dump(starter_rules, f, default_flow_style=False)
        console.print(f"[green]✓[/green] Created {rules_path}")

    banned_path = workspace_root / "banned_phrases.yaml"
    if not banned_path.exists():
        starter_banned = {
            "banned_regex": [
                "(?i)breath\\s+hitch",
                "(?i)silence\\s+pools",
                "(?i)spilled\\s+ink",
                "(?i)the\\s+truth\\s+is",
                "(?i)what\\s+he\\s+won'?t\\s+admit",
                "(?i)what\\s+she\\s+won'?t\\s+admit",
                "(?i)he\\s+realizes",
                "(?i)she\\s+realizes",
                "(?i)like\\s+a\\s+grandmaster",
                "(?i)chess(piece|board|\\s+pieces)?",
                "(?i)the\\s+room\\s+(watches|listens|holds\\s+its\\s+breath)",
                "(?i)the\\s+air\\s+(thickens|tightens)",
                "(?i)(walls|ceiling|floor)\\s+(listen|witness|remember)",
                "(?i)(light|shadow|darkness)\\s+(interrogates|judges|accuses)",
                "(?i)the\\s+reader",
                "(?i)the\\s+narrative",
                "(?i)the\\s+story",
                "(?i)authorial\\s+intent",
                "(?i)as\\s+the\\s+author"
            ],
            "warn_regex": [
                "(?i)cufflinks\\b",
                "(?i)designer\\b",
                "(?i)perfectly\\s+aligned",
                "(?i)hum\\w*\\b",
                "(?i)green\\s+blink",
                "(?i)tension\\s+(?:builds|escalates|mounts)",
                "(?i)(?:the\\s+)?(?:mood|atmosphere)\\s+(?:shifts|changes|deepens)",
                "(?i)(?:she|he)\\s+(?:knew|understood|realized)\\s+(?:that\\s+)?(?:he|she|it)"
            ]
        }
        with open(banned_path, "w") as f:
            yaml.dump(starter_banned, f, default_flow_style=False)
        console.print(f"[green]✓[/green] Created {banned_path}")

    console.print(f"[green]✓[/green] Workspace ready: {workspace_root}")


@click.group()
def cli():
    """Writing Harness: CLI for continuity-enforced narrative writing."""
    pass


@cli.command()
def init():
    """Initialize workspace."""
    try:
        create_workspace(settings.workspace_root)
        console.print("[green]Initialization complete.[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Exit(1)


@cli.command()
@click.option("--title", default="Untitled Scene", help="Scene title")
def new_scene(title):
    """Create a new numbered scene file."""
    try:
        scenes_dir = settings.workspace_root / "scenes"
        scenes_dir.mkdir(exist_ok=True)

        existing = list(scenes_dir.glob("*.md"))
        next_num = len(existing) + 1
        scene_path = scenes_dir / f"{next_num:04d}_scene.md"

        state_path = settings.workspace_root / "state.yaml"
        ledger = load_continuity_ledger(state_path)

        state_summary = f"""<!--
CURRENT STATE (copied from state.yaml):
Location: {ledger.location_current}
Time: {ledger.time_of_day} | {ledger.date_or_day_count} | +{ledger.elapsed_time_since_last_scene} since last scene
Present: {', '.join(ledger.who_present)}
Relationship: {ledger.relationship_elapsed_time} | {ledger.relationship_last_contact}
Goal: {ledger.scene_goal}
Tone: {ledger.tone_profile}
-->

# Scene {next_num:04d} — {title}

[Seed text goes here. Keep it simple. Dialogue allowed.]
"""
        with open(scene_path, "w") as f:
            f.write(state_summary)

        console.print(f"[green]✓[/green] Created {scene_path}")
        console.print(f"[yellow]Tip:[/yellow] Edit the scene file and replace [Seed text...] with your opening.")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Exit(1)


@cli.command()
@click.argument("scene_file", type=click.Path(exists=True))
@click.option("--lore-k", default=8, help="Number of lore snippets to retrieve")
@click.option("--no-lore", is_flag=True, help="Disable lore retrieval")
def draft(scene_file, lore_k, no_lore):
    """Generate a draft of a scene."""
    try:
        scene_path = Path(scene_file)
        console.print(f"[blue]Drafting...[/blue]")

        result = draft_scene(scene_path, settings.workspace_root, lore_k, use_lore=not no_lore)

        scene_num = scene_path.stem.split("_")[0]
        output_dir = settings.workspace_root / "outputs"
        output_dir.mkdir(exist_ok=True)

        draft_path = output_dir / f"{scene_num}_scene_draft.md"
        with open(draft_path, "w") as f:
            f.write(result["draft_text"])

        style_report_path = output_dir / f"{scene_num}_style_lint.md"
        with open(style_report_path, "w") as f:
            f.write("# Style Lint Report\n\n")
            if result["style_violations"]:
                for v in result["style_violations"]:
                    f.write(f"- **Line {v.line_number}**: {v.message}\n")
                    if v.context:
                        f.write(f"  > {v.context}\n")
            else:
                f.write("No style violations.\n")

        continuity_report_path = output_dir / f"{scene_num}_continuity_lint.md"
        with open(continuity_report_path, "w") as f:
            f.write("# Continuity Lint Report\n\n")
            if result["continuity_violations"]:
                for v in result["continuity_violations"]:
                    f.write(f"- {v.message}\n")
                    if v.context:
                        f.write(f"  > {v.context}\n")
            else:
                f.write("No continuity violations.\n")

        console.print(f"[green]✓[/green] Draft: {draft_path}")
        console.print(f"[green]✓[/green] Style Lint: {style_report_path}")
        console.print(f"[green]✓[/green] Continuity Lint: {continuity_report_path}")

        style_count = len(result["style_violations"])
        continuity_count = len(result["continuity_violations"])
        console.print(f"\n[yellow]Issues found:[/yellow] {style_count} style, {continuity_count} continuity")

        if style_count > 0 or continuity_count > 0:
            console.print("[yellow]Tip:[/yellow] Run 'revise' to fix violations:")
            console.print(f"  python -m harness.cli revise {draft_path}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Exit(1)


@cli.command()
@click.argument("draft_file", type=click.Path(exists=True))
@click.option("--strict", is_flag=True, help="Fail if violations remain")
def revise(draft_file, strict):
    """Revise a draft to fix violations."""
    try:
        draft_path = Path(draft_file)

        with open(draft_path, "r") as f:
            draft_text = f.read()

        console.print("[blue]Revising...[/blue]")
        result = revise_draft(draft_text, settings.workspace_root)

        scene_num = draft_path.stem.split("_")[0]
        output_dir = settings.workspace_root / "outputs"

        final_path = output_dir / f"{scene_num}_scene_out.md"
        with open(final_path, "w") as f:
            f.write(result["revised_text"])

        revise_report_path = output_dir / f"{scene_num}_revise_lint.md"
        with open(revise_report_path, "w") as f:
            f.write("# Post-Revision Lint Report\n\n")
            f.write("## Style Violations (Remaining)\n")
            if result["style_violations"]:
                for v in result["style_violations"]:
                    f.write(f"- {v.message}\n")
            else:
                f.write("None.\n")
            f.write("\n## Continuity Violations (Remaining)\n")
            if result["continuity_violations"]:
                for v in result["continuity_violations"]:
                    f.write(f"- {v.message}\n")
            else:
                f.write("None.\n")

        console.print(f"[green]✓[/green] Revised: {final_path}")
        console.print(f"[green]✓[/green] Report: {revise_report_path}")

        style_count = len(result["style_violations"])
        continuity_count = len(result["continuity_violations"])
        console.print(f"\n[yellow]Issues remaining:[/yellow] {style_count} style, {continuity_count} continuity")

        if strict and (style_count > 0 or continuity_count > 0):
            console.print("[red]Strict mode: violations remain. Exiting with error.[/red]")
            raise click.Exit(1)
    except click.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Exit(1)


@cli.command()
@click.argument("text_file", type=click.Path(exists=True))
def lint(text_file):
    """Lint a text file for style and continuity violations."""
    try:
        text_path = Path(text_file)

        with open(text_path, "r") as f:
            text = f.read()

        state_path = settings.workspace_root / "state.yaml"
        ledger = load_continuity_ledger(state_path)

        banned_path = settings.workspace_root / "banned_phrases.yaml"
        banned = load_banned_phrases(banned_path)

        style_violations = lint_style(text, banned, scene_location=ledger.location_current)
        continuity_violations = lint_continuity(text, ledger)

        if style_violations:
            console.print("\n[bold red]Style Violations:[/bold red]")
            for v in style_violations:
                severity_color = "red" if v.severity == "error" else "yellow"
                console.print(f"  [{severity_color}]{v.severity.upper()}[/{severity_color}] Line {v.line_number}: {v.message}")
                if v.context:
                    console.print(f"    > {v.context}")

        if continuity_violations:
            console.print("\n[bold red]Continuity Violations:[/bold red]")
            for v in continuity_violations:
                severity_color = "red" if v.severity == "error" else "yellow"
                console.print(f"  [{severity_color}]{v.severity.upper()}[/{severity_color}] {v.message}")
                if v.context:
                    console.print(f"    > {v.context}")

        if not style_violations and not continuity_violations:
            console.print("[green]No violations found.[/green]")
        else:
            total = len(style_violations) + len(continuity_violations)
            console.print(f"\n[yellow]Total violations:[/yellow] {total}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Exit(1)


def main():
    cli()


if __name__ == "__main__":
    main()
