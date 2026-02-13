"""Tests for harness.lint.style — all 8 style checkers + aggregator."""
import pytest
from harness.models import BannedPhrases
from harness.lint.style import (
    lint_banned_phrases,
    lint_scene_containment,
    lint_meta_narrative,
    lint_pov_and_address,
    lint_editorializing,
    lint_object_anthropomorphism,
    lint_dialogue_exposition,
    lint_pov_consistency,
    lint_style,
)


# ── helpers ─────────────────────────────────────────────────────────
def _bp(banned=None, warn=None):
    return BannedPhrases(banned_regex=banned or [], warn_regex=warn or [])


# ── lint_banned_phrases ─────────────────────────────────────────────
class TestLintBannedPhrases:
    def test_no_matches(self):
        text = "She walked to the window and looked out."
        bp = _bp(banned=[r"(?i)breath\s+hitch"])
        assert lint_banned_phrases(text, bp) == []

    def test_banned_match(self):
        text = "Her breath hitched in the dark."
        bp = _bp(banned=[r"(?i)breath\s+hitch"])
        vs = lint_banned_phrases(text, bp)
        assert len(vs) == 1
        assert vs[0].severity == "error"
        assert "Banned" in vs[0].message
        assert vs[0].line_number == 1

    def test_warn_match(self):
        text = "He adjusted his cufflinks slowly."
        bp = _bp(warn=[r"(?i)cufflinks\b"])
        vs = lint_banned_phrases(text, bp)
        assert len(vs) == 1
        assert vs[0].severity == "warning"
        assert "Caution" in vs[0].message

    def test_multiple_lines(self):
        text = "Line one.\nHer breath hitched.\nLine three.\nSilence pools around them."
        bp = _bp(banned=[r"(?i)breath\s+hitch", r"(?i)silence\s+pools"])
        vs = lint_banned_phrases(text, bp)
        assert len(vs) == 2
        lines = {v.line_number for v in vs}
        assert lines == {2, 4}

    def test_malformed_regex_ignored(self):
        text = "Some text"
        bp = _bp(banned=["[invalid"])
        vs = lint_banned_phrases(text, bp)
        assert vs == []

    def test_context_truncated(self):
        text = "x" * 200 + " breath hitch"
        bp = _bp(banned=[r"(?i)breath\s+hitch"])
        vs = lint_banned_phrases(text, bp)
        assert len(vs[0].context) <= 120


# ── lint_scene_containment ──────────────────────────────────────────
class TestLintSceneContainment:
    def test_clean_text(self):
        text = "He poured water into the glass and set it down."
        assert lint_scene_containment(text) == []

    def test_flashback_detected(self):
        text = "In a flashback, she remembered the house."
        vs = lint_scene_containment(text)
        assert any("Flashback" in v.message for v in vs)

    def test_historical_exposition(self):
        text = "Once, years ago, they had met in the same room."
        vs = lint_scene_containment(text)
        assert len(vs) >= 1

    def test_character_history(self):
        text = "She had once been a dancer in Moscow."
        vs = lint_scene_containment(text)
        assert any("history" in v.message.lower() or "present moment" in v.message.lower() for v in vs)

    def test_past_event_summary(self):
        text = "Back then, she had lived in a different city."
        vs = lint_scene_containment(text)
        assert len(vs) >= 1


# ── lint_meta_narrative ─────────────────────────────────────────────
class TestLintMetaNarrative:
    def test_clean_text(self):
        text = "He set the glass down and waited."
        assert lint_meta_narrative(text) == []

    def test_reader_reference(self):
        text = "The reader would notice the tension."
        vs = lint_meta_narrative(text)
        assert any("reader" in v.message.lower() for v in vs)

    def test_story_self_reference(self):
        text = "The story takes a dark turn here."
        vs = lint_meta_narrative(text)
        assert any("story" in v.message.lower() for v in vs)

    def test_tension_explanation(self):
        text = "He moved closer to heighten the tension."
        vs = lint_meta_narrative(text)
        assert any("tension" in v.message.lower() for v in vs)

    def test_mood_shift_labeling(self):
        text = "The mood shifts as she enters."
        vs = lint_meta_narrative(text)
        assert any("mood" in v.message.lower() or "Narrative" in v.message for v in vs)

    def test_authorial_intent(self):
        text = "As the author intended, the scene resolves."
        vs = lint_meta_narrative(text)
        assert len(vs) >= 1


# ── lint_pov_and_address ────────────────────────────────────────────
class TestLintPovAndAddress:
    def test_clean_narration(self):
        text = "She looked at him. He said nothing."
        assert lint_pov_and_address(text) == []

    def test_second_person_in_narration(self):
        text = "You could see the tension in the room."
        vs = lint_pov_and_address(text)
        assert len(vs) == 1
        assert "you" in vs[0].message.lower()

    def test_second_person_in_dialogue_ok(self):
        text = '"You should leave," she said.'
        vs = lint_pov_and_address(text)
        assert vs == []

    def test_second_person_in_single_quote_dialogue(self):
        # The code requires >=2 single quotes AND apostrophe not in first 3 chars.
        # Starting with ' means line[:3] contains ', so it's NOT treated as dialogue.
        text = "'You should leave,' she said."
        vs = lint_pov_and_address(text)
        # This triggers because the heuristic doesn't recognize it as dialogue
        assert len(vs) == 1

    def test_second_person_in_offset_single_quote_dialogue(self):
        # Single-quote dialogue not starting at position 0
        text = "She said, 'You should leave.'"
        vs = lint_pov_and_address(text)
        assert vs == []


# ── lint_editorializing ─────────────────────────────────────────────
class TestLintEditorializing:
    def test_clean_text(self):
        text = "She picked up the glass and drank."
        assert lint_editorializing(text) == []

    def test_abstract_state_named(self):
        text = "It was a victory for him."
        vs = lint_editorializing(text)
        assert any("victory" in v.message.lower() or "Abstract" in v.message for v in vs)

    def test_surrender_detected(self):
        text = "Her surrender was complete."
        vs = lint_editorializing(text)
        assert len(vs) >= 1

    def test_diagnosis_line(self):
        text = "In this moment, she understood that he was lying."
        vs = lint_editorializing(text)
        assert any("Diagnosis" in v.message or "realizing" in v.message.lower() for v in vs)

    def test_narrative_explanation(self):
        text = "This revealed that she had been right all along."
        vs = lint_editorializing(text)
        assert any("explanation" in v.message.lower() or "explaining" in v.message.lower() for v in vs)


# ── lint_object_anthropomorphism ────────────────────────────────────
class TestLintObjectAnthropomorphism:
    def test_clean_text(self):
        text = "The room was empty. He closed the door."
        assert lint_object_anthropomorphism(text) == []

    def test_silence_watches(self):
        text = "The silence watches them from every corner."
        vs = lint_object_anthropomorphism(text)
        assert any("silence" in v.message and "watches" in v.message for v in vs)

    def test_walls_listen(self):
        # "wall" (singular) is in inanimate_subjects, matched via \bwall\b
        text = "The wall listens to every word."
        vs = lint_object_anthropomorphism(text)
        assert any("wall" in v.message and "listens" in v.message for v in vs)

    def test_inanimate_with_gap_words(self):
        # pattern allows intervening words between noun and verb
        text = "The door slowly waits for him."
        vs = lint_object_anthropomorphism(text)
        assert any("door" in v.message and "waits" in v.message for v in vs)


# ── lint_dialogue_exposition ────────────────────────────────────────
class TestLintDialogueExposition:
    def test_short_dialogue_ok(self):
        text = '"Hello," she said.\n"Hi," he replied.'
        assert lint_dialogue_exposition(text) == []

    def test_long_monologue_detected(self):
        lines = [f'"Line {i} of a very long speech."' for i in range(12)]
        text = "\n".join(lines)
        # 12 consecutive lines with quotes, then no break means no trigger
        # (the trigger fires when a non-dialogue line follows)
        text += "\nShe paused."
        vs = lint_dialogue_exposition(text)
        assert len(vs) >= 1
        assert "dialogue block" in vs[0].message.lower() or "Long" in vs[0].message

    def test_broken_dialogue_ok(self):
        lines = []
        for i in range(6):
            lines.append(f'"Line {i}."')
            lines.append("He paused.")
        text = "\n".join(lines)
        assert lint_dialogue_exposition(text) == []


# ── lint_pov_consistency ────────────────────────────────────────────
class TestLintPovConsistency:
    def test_clean_text(self):
        text = "She stood and walked to the door."
        assert lint_pov_consistency(text) == []

    def test_character_typing(self):
        text = "She was the type to leave without warning."
        vs = lint_pov_consistency(text)
        assert len(vs) >= 1

    def test_habitual_summary(self):
        text = "Like she always did, she turned away."
        vs = lint_pov_consistency(text)
        assert len(vs) >= 1

    def test_never_one_to(self):
        text = "She had never been one to complain."
        vs = lint_pov_consistency(text)
        assert len(vs) >= 1


# ── lint_style (aggregator) ─────────────────────────────────────────
class TestLintStyle:
    def test_clean_text(self):
        bp = _bp()
        text = "He sat in the chair. She poured coffee."
        vs = lint_style(text, bp)
        assert vs == []

    def test_deduplication(self):
        # "the reader" triggers both banned_phrases AND meta_narrative
        bp = _bp(banned=[r"(?i)the\s+reader"])
        text = "The reader should understand this."
        vs = lint_style(text, bp)
        messages = [v.message for v in vs]
        # each (line_number, message) pair should appear only once
        keys = [(v.line_number, v.message) for v in vs]
        assert len(keys) == len(set(keys))

    def test_multiple_categories(self):
        bp = _bp(banned=[r"(?i)breath\s+hitch"])
        text = "Her breath hitched. You could see it."
        vs = lint_style(text, bp)
        # banned phrase + POV violation
        assert len(vs) >= 2

    def test_scene_location_passed_through(self):
        bp = _bp()
        text = "He stood and waited. " * 10  # >100 chars
        vs = lint_style(text, bp, scene_location="Library")
        # no scene containment errors for clean text
        assert all("containment" not in v.message.lower() for v in vs)
