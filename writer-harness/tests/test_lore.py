"""Tests for harness.lore.ingest and harness.lore.retrieve."""
import pytest
from pathlib import Path
from harness.lore.ingest import load_lore_entries
from harness.lore.retrieve import extract_keywords, retrieve_lore


# ── load_lore_entries ───────────────────────────────────────────────
class TestLoadLoreEntries:
    def test_missing_dir(self, tmp_path):
        entries = load_lore_entries(tmp_path / "nonexistent")
        assert entries == []

    def test_empty_dir(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        assert load_lore_entries(lore_dir) == []

    def test_loads_md_files(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        (lore_dir / "alpha.md").write_text("Alpha content")
        (lore_dir / "beta.md").write_text("Beta content")
        entries = load_lore_entries(lore_dir)
        assert len(entries) == 2
        titles = [t for t, _ in entries]
        assert "alpha" in titles
        assert "beta" in titles

    def test_loads_txt_files(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        (lore_dir / "notes.txt").write_text("Some notes")
        entries = load_lore_entries(lore_dir)
        assert len(entries) == 1
        assert entries[0][0] == "notes"

    def test_skips_empty_files(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        (lore_dir / "empty.md").write_text("")
        (lore_dir / "full.md").write_text("Content here")
        entries = load_lore_entries(lore_dir)
        assert len(entries) == 1
        assert entries[0][0] == "full"

    def test_skips_other_extensions(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        (lore_dir / "data.json").write_text('{"key": "value"}')
        (lore_dir / "real.md").write_text("Real content")
        entries = load_lore_entries(lore_dir)
        assert len(entries) == 1

    def test_sorted_order(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        (lore_dir / "charlie.md").write_text("C")
        (lore_dir / "alpha.md").write_text("A")
        (lore_dir / "bravo.md").write_text("B")
        entries = load_lore_entries(lore_dir)
        titles = [t for t, _ in entries]
        assert titles == ["alpha", "bravo", "charlie"]


# ── extract_keywords ────────────────────────────────────────────────
class TestExtractKeywords:
    def test_extracts_capitalized(self):
        text = "Alice went to the Moscow office with Bob."
        kw = extract_keywords(text)
        assert "Alice" in kw
        assert "Moscow" in kw
        assert "Bob" in kw

    def test_no_lowercase(self):
        text = "she walked to the door and waited."
        kw = extract_keywords(text)
        assert kw == []

    def test_deduplicates(self):
        text = "Alice met Alice in Moscow near Moscow."
        kw = extract_keywords(text)
        assert kw.count("Alice") == 1
        assert kw.count("Moscow") == 1

    def test_multi_word_names(self):
        text = "Novo Ogaryovo is beautiful."
        kw = extract_keywords(text)
        assert "Novo Ogaryovo" in kw


# ── retrieve_lore ───────────────────────────────────────────────────
class TestRetrieveLore:
    def test_empty_dir(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        snippets = retrieve_lore(["Alice"], lore_dir)
        assert snippets == []

    def test_retrieves_matching(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        (lore_dir / "Alice.md").write_text("Alice is a protagonist who lives in Moscow.")
        (lore_dir / "Weather.md").write_text("The weather is always cold in winter.")
        snippets = retrieve_lore(["Alice"], lore_dir, top_k=2)
        assert len(snippets) >= 1
        assert any("Alice" in s for s in snippets)

    def test_respects_top_k(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        for i in range(10):
            (lore_dir / f"entry_{i}.md").write_text(f"Entry {i} about Topic Alpha")
        snippets = retrieve_lore(["Topic"], lore_dir, top_k=3)
        assert len(snippets) <= 3

    def test_truncates_long_content(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        long_content = "x" * 1000
        (lore_dir / "long.md").write_text(long_content)
        snippets = retrieve_lore(["long"], lore_dir, max_chars_per_snippet=100)
        assert len(snippets) == 1
        # snippet includes title prefix "**long**\n" + 100 chars + "..."
        assert "..." in snippets[0]

    def test_no_keywords(self, tmp_path):
        lore_dir = tmp_path / "lore"
        lore_dir.mkdir()
        (lore_dir / "entry.md").write_text("Some content")
        snippets = retrieve_lore([], lore_dir)
        # with no keywords, scores default to 0, below threshold
        assert snippets == []
