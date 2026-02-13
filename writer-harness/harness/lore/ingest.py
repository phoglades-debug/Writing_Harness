from pathlib import Path
from typing import List, Tuple


def load_lore_entries(lore_dir: Path) -> List[Tuple[str, str]]:
    """Load lore entries from directory."""
    entries = []

    if not lore_dir.exists():
        return entries

    for file_path in sorted(lore_dir.glob("*.md")):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                title = file_path.stem
                entries.append((title, content))

    for file_path in sorted(lore_dir.glob("*.txt")):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                title = file_path.stem
                entries.append((title, content))

    return entries
