import re
from pathlib import Path
from typing import List
from rapidfuzz import fuzz
from harness.lore.ingest import load_lore_entries


def extract_keywords(text: str) -> List[str]:
    """Extract capitalized terms from text."""
    tokens = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    return list(set(tokens))


def retrieve_lore(
    keywords: List[str],
    lore_dir: Path,
    top_k: int = 8,
    max_chars_per_snippet: int = 600,
) -> List[str]:
    """Retrieve top-K lore snippets matching keywords."""
    entries = load_lore_entries(lore_dir)

    if not entries:
        return []

    scores = []
    for title, content in entries:
        best_score = 0
        for keyword in keywords:
            title_score = fuzz.partial_ratio(keyword.lower(), title.lower())
            content_sample = content[:1000]
            content_score = fuzz.partial_ratio(keyword.lower(), content_sample.lower())
            best_score = max(best_score, title_score, content_score)
        scores.append((best_score, title, content))

    scores.sort(key=lambda x: x[0], reverse=True)

    snippets = []
    for score, title, content in scores[:top_k]:
        if score > 30:
            snippet = content[:max_chars_per_snippet]
            if len(content) > max_chars_per_snippet:
                snippet += "..."
            snippets.append(f"**{title}**\n{snippet}")

    return snippets
