import re
from typing import List
from harness.models import LintViolation, BannedPhrases


def lint_banned_phrases(text: str, banned_phrases: BannedPhrases) -> List[LintViolation]:
    """Check for banned phrases using regex patterns."""
    violations = []
    lines = text.split('\n')

    for pattern in banned_phrases.banned_regex:
        try:
            regex = re.compile(pattern)
            for line_num, line in enumerate(lines, 1):
                match = regex.search(line)
                if match:
                    violations.append(
                        LintViolation(
                            category="style",
                            severity="error",
                            message=f"Banned: {match.group(0)}",
                            line_number=line_num,
                            context=line.strip()[:120],
                        )
                    )
        except re.error as e:
            print(f"Warning: malformed regex pattern '{pattern}': {e}")

    for pattern in banned_phrases.warn_regex:
        try:
            regex = re.compile(pattern)
            for line_num, line in enumerate(lines, 1):
                match = regex.search(line)
                if match:
                    violations.append(
                        LintViolation(
                            category="style",
                            severity="warning",
                            message=f"Caution: {match.group(0)}",
                            line_number=line_num,
                            context=line.strip()[:120],
                        )
                    )
        except re.error as e:
            print(f"Warning: malformed regex pattern '{pattern}': {e}")

    return violations


def lint_scene_containment(text: str, scene_location: str = None) -> List[LintViolation]:
    """Detect scene containment violations."""
    violations = []
    lines = text.split('\n')

    exposition_patterns = [
        (r"(?i)\bflashback\b", "Flashback (breaks scene containment)"),
        (r"(?i)(?:in\s+)?(?:a\s+)?(?:flashback|reverie|memory)", "Flashback insertion (breaks containment)"),
        (r"(?i)(?:she\s+)?(?:had\s+)?been\s+(?:the\s+)?(?:type\s+)?(?:years?|months?)\s+(?:ago|before|earlier)", "Historical exposition (stay in present moment)"),
        (r"(?i)(?:this\s+)?(?:wasn't\s+)?(?:the\s+)?(?:first|second|only)\\s+time\\s+(?:he|she|they)", "Referencing past event (only if actively discussed)"),
        (r"(?i)(?:once|when),?\s+(?:years?|months?|weeks?|days?)\s+(?:ago|earlier|before)", "Backstory exposition (only if dialogue-relevant)"),
        (r"(?i)(?:he|she|they)\s+(?:had\s+)?(?:once|used\s+to|always)\s+been", "Character history insertion (keep to present moment)"),
        (r"(?i)(?:back\s+)?(?:when|then),?\s+(?:she|he|they)\s+(?:had|was|were|did)", "Past event summary mid-scene (avoid unless dialogue-driven)"),
    ]

    for pattern, msg in exposition_patterns:
        try:
            regex = re.compile(pattern)
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    violations.append(
                        LintViolation(
                            category="style",
                            severity="error",
                            message=msg,
                            line_number=line_num,
                            context=line.strip()[:120],
                        )
                    )
        except re.error:
            pass

    return violations


def lint_meta_narrative(text: str) -> List[LintViolation]:
    """Detect meta-narrative intrusions."""
    violations = []
    lines = text.split('\n')

    meta_patterns = [
        (r"(?i)\b(?:the\s+)?reader\b", "Meta-narrative: direct reference to reader"),
        (r"(?i)\bthe\s+(?:story|narrative)\b", "Meta-narrative: story self-reference"),
        (r"(?i)\bauthorial\s+(?:intent|voice)", "Meta-narrative: author commentary"),
        (r"(?i)\bas\s+the\s+author\b", "Meta-narrative: author intrusion"),
        (r"(?i)(?:to\s+)?(?:build|escalate|heighten|deepen)\s+(?:the\s+)?tension", "Narrative explanation: don't explain tension mechanics"),
        (r"(?i)(?:the\s+)?(?:mood|atmosphere)\s+(?:shifts|changes|deepens|grows)", "Narrative explanation: mood shift labeling"),
        (r"(?i)(?:this|that|it)\s+(?:would|could|should)\s+(?:reveal|show|prove|demonstrate)", "Narrative explanation: explaining what action means"),
    ]

    for pattern, msg in meta_patterns:
        try:
            regex = re.compile(pattern)
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    violations.append(
                        LintViolation(
                            category="style",
                            severity="error",
                            message=msg,
                            line_number=line_num,
                            context=line.strip()[:120],
                        )
                    )
        except re.error:
            pass

    return violations


def lint_pov_and_address(text: str) -> List[LintViolation]:
    """Check for second-person narration outside dialogue."""
    violations = []
    lines = text.split('\n')

    for line_num, line in enumerate(lines, 1):
        double_quotes = line.count('"')
        single_quotes = line.count("'")
        likely_dialogue = (double_quotes >= 2) or (single_quotes >= 2 and "'" not in line[:3])

        if not likely_dialogue:
            if re.search(r'\byou\b', line, re.IGNORECASE):
                violations.append(
                    LintViolation(
                        category="style",
                        severity="error",
                        message="Second-person pronoun 'you' in narration",
                        line_number=line_num,
                        context=line.strip()[:120],
                    )
                )

    return violations


def lint_editorializing(text: str) -> List[LintViolation]:
    """Detect editorializing and naming relational states."""
    violations = []
    lines = text.split('\n')

    editorializing_patterns = [
        (r"(?i)\bwon\b.*(?:over|her|him|the\s+day|control|the\s+upper\s+hand)", "Relational outcome named: 'won...'"),
        (r"(?i)\b(victory|triumph|surrender|submission|dominance|submission|defeat|conquest)\b", "Abstract state named (show behavior instead)"),
        (r"(?i)he\s+had\s+(won|conquered|captured|claimed)", "Relational outcome named"),
        (r"(?i)(?:was|is)\s+(?:victorious|triumphant|defeated|conquered)", "State named (avoid diagnosis)"),
        (r"(?i)this\s+(?:revealed|showed|proved|demonstrated)\s+(?:that|her|his|the)", "Narrative explanation: explaining meaning"),
        (r"(?i)(?:in\s+)?(?:this\s+moment|that\s+instant),?\s+(?:she|he|they)\s+(?:understood|realized|knew)", "Diagnosis line: realizing/understanding"),
    ]

    for pattern, msg in editorializing_patterns:
        try:
            regex = re.compile(pattern)
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    violations.append(
                        LintViolation(
                            category="style",
                            severity="error",
                            message=msg,
                            line_number=line_num,
                            context=line.strip()[:120],
                        )
                    )
        except re.error:
            pass

    return violations


def lint_object_anthropomorphism(text: str) -> List[LintViolation]:
    """Detect inanimate objects emoting or symbolizing."""
    violations = []
    lines = text.split('\n')

    inanimate_subjects = [
        "silence", "room", "light", "table", "chair", "desk",
        "painting", "photo", "box", "door", "window",
        "ventilation", "shoes", "clock", "mirror",
        "wall", "floor", "ceiling", "air", "space", "shadows",
        "fabric", "glass", "marble", "stone", "wood",
    ]

    emotional_verbs = [
        "watches", "listens", "hears", "sees", "knows",
        "remembers", "judges", "accuses", "demands",
        "mirrors", "reflects", "echoes", "whispers",
        "breathes", "holds", "embraces", "waits",
    ]

    for line_num, line in enumerate(lines, 1):
        lower_line = line.lower()

        for noun in inanimate_subjects:
            for verb in emotional_verbs:
                pattern = rf'\b{re.escape(noun)}\b\s+(?:\w+\s+)*{re.escape(verb)}\b'
                if re.search(pattern, lower_line):
                    violations.append(
                        LintViolation(
                            category="style",
                            severity="warning",
                            message=f"Object anthropomorphism: '{noun}' + '{verb}'",
                            line_number=line_num,
                            context=line.strip()[:120],
                        )
                    )

    return violations


def lint_dialogue_exposition(text: str) -> List[LintViolation]:
    """Detect monologues and over-explanation."""
    violations = []
    lines = text.split('\n')

    in_dialogue = False
    dialogue_start = 0
    dialogue_lines = 0

    for line_num, line in enumerate(lines, 1):
        has_quote = '"' in line

        if has_quote:
            if not in_dialogue:
                in_dialogue = True
                dialogue_start = line_num
                dialogue_lines = 1
            else:
                dialogue_lines += 1
        else:
            if in_dialogue and dialogue_lines > 10:
                violations.append(
                    LintViolation(
                        category="style",
                        severity="warning",
                        message=f"Long dialogue block ({dialogue_lines} lines): consider breaking up",
                        line_number=dialogue_start,
                        context=f"Lines {dialogue_start}–{line_num-1}",
                    )
                )
            in_dialogue = False
            dialogue_lines = 0

    return violations


def lint_pov_consistency(text: str) -> List[LintViolation]:
    """Detect character summary/typing."""
    violations = []
    lines = text.split('\n')

    pov_violations = [
        (r"(?i)(?:she|he)\s+(?:was\s+)?(?:the\s+type\s+)?(?:of|to)", "Character summary/typing (breaks POV)"),
        (r"(?i)(?:in\s+)?(?:her|his)\s+(?:nature|character|way)", "Character summary (breaks POV)"),
        (r"(?i)(?:like|as)\s+(?:she|he)\s+(?:always|usually|often)\s+(?:did|was)", "Habitual summary (breaks POV)"),
        (r"(?i)she\s+(?:had\s+)?(?:never|always)\s+(?:been\s+)?(?:one\s+)?to", "Character typing (breaks POV)"),
    ]

    for pattern, msg in pov_violations:
        try:
            regex = re.compile(pattern)
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    violations.append(
                        LintViolation(
                            category="style",
                            severity="warning",
                            message=msg,
                            line_number=line_num,
                            context=line.strip()[:120],
                        )
                    )
        except re.error:
            pass

    return violations


def lint_style(text: str, banned_phrases: BannedPhrases, scene_location: str = None) -> List[LintViolation]:
    """Run all style checks."""
    violations = []
    violations.extend(lint_banned_phrases(text, banned_phrases))
    violations.extend(lint_scene_containment(text, scene_location))
    violations.extend(lint_meta_narrative(text))
    violations.extend(lint_pov_and_address(text))
    violations.extend(lint_editorializing(text))
    violations.extend(lint_object_anthropomorphism(text))
    violations.extend(lint_dialogue_exposition(text))
    violations.extend(lint_pov_consistency(text))

    seen = set()
    unique_violations = []
    for v in violations:
        key = (v.line_number, v.message)
        if key not in seen:
            seen.add(key)
            unique_violations.append(v)

    return unique_violations
