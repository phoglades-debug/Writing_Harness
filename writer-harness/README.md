# Writing Harness

CLI tool for enforcing continuity and style in serialized narratives. Uses LLM-powered drafting and revision with automated linting to maintain consistency across scenes.

## Requirements

- Python 3.11+
- An API key for Anthropic or OpenAI

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your API key
```

## Usage

```bash
# Initialize workspace with starter config files
harness init

# Create a new scene file
harness new-scene --title "Opening"

# Edit the scene file with your seed text, then generate a draft
harness draft workspace/scenes/0001_scene.md

# Revise a draft to fix lint violations
harness revise workspace/outputs/0001_scene_draft.md

# Lint any text file
harness lint workspace/outputs/0001_scene_draft.md
```

## Workflow

1. `harness init` creates `workspace/` with `state.yaml`, `style_rules.yaml`, and `banned_phrases.yaml`
2. `harness new-scene` creates a numbered scene file pre-filled with current state context
3. Edit the scene file with seed text (opening lines, dialogue, directions)
4. `harness draft` sends the seed + continuity ledger + style rules + lore to the LLM, then lints the output
5. Review the lint reports, then `harness revise` to fix violations automatically
6. Repeat until clean

## Configuration

- **state.yaml** — Continuity ledger: location, time, characters present, relationships, physical constraints, scene goal, tone
- **style_rules.yaml** — Hard rules (must enforce) and soft preferences (guidance) for prose style
- **banned_phrases.yaml** — Regex patterns flagged as errors (banned) or warnings (caution)
- **workspace/lore/** — Drop `.md` or `.txt` files here; the system retrieves relevant snippets via fuzzy matching

## Linting

Style checks (8 categories): banned phrases, scene containment, meta-narrative, POV/address, editorializing, object anthropomorphism, dialogue exposition, POV consistency.

Continuity checks (3 categories): location mentions, character presence, timeline consistency.

## Tests

```bash
pytest
pytest --cov=harness --cov-report=term-missing
```

## License

MIT
