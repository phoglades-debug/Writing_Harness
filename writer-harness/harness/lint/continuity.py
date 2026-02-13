import re
from typing import List
from harness.models import LintViolation, ContinuityLedger


def lint_location_change(text: str, ledger: ContinuityLedger) -> List[LintViolation]:
    """Check for location changes without explicit travel."""
    violations = []

    lines = text.split('\n')
    location_mentioned = any(
        ledger.location_current.lower() in line.lower()
        for line in lines
    )

    if not location_mentioned and len(text) > 100:
        violations.append(
            LintViolation(
                category="continuity",
                severity="warning",
                message=f"Current location '{ledger.location_current}' not mentioned in text",
                context="Confirm scene is still in this location",
            )
        )

    return violations


def lint_who_present(text: str, ledger: ContinuityLedger) -> List[LintViolation]:
    """Check that characters from who_present list appear."""
    violations = []

    text_lower = text.lower()

    for character in ledger.who_present:
        char_lower = character.lower()
        if char_lower in ["aide", "assistant", "staff", "attendant"]:
            continue

        count = len(re.findall(rf'\b{re.escape(char_lower)}\b', text_lower))

        if count == 0:
            violations.append(
                LintViolation(
                    category="continuity",
                    severity="warning",
                    message=f"Character '{character}' supposed present but not mentioned",
                    context="Check if character should still be in scene",
                )
            )

    return violations


def lint_timeline(text: str, ledger: ContinuityLedger) -> List[LintViolation]:
    """Check for timeline inconsistencies."""
    violations = []

    elapsed_match = re.search(
        r'(\d+)\s+(?:minutes?|hours?|days?)',
        ledger.elapsed_time_since_last_scene,
        re.IGNORECASE
    )

    if elapsed_match:
        elapsed_value = int(elapsed_match.group(1))

        time_refs = re.findall(
            r'(\d+)\s+(?:minutes?|hours?|days?)',
            text,
            re.IGNORECASE
        )

        for time_str in time_refs:
            try:
                ref_value = int(time_str)
                if ref_value > elapsed_value * 3:
                    violations.append(
                        LintViolation(
                            category="continuity",
                            severity="warning",
                            message=f"Time reference ({time_str}) may exceed elapsed time",
                            context=f"Elapsed: {ledger.elapsed_time_since_last_scene}",
                        )
                    )
            except ValueError:
                pass

    return violations


def lint_continuity(text: str, ledger: ContinuityLedger) -> List[LintViolation]:
    """Run all continuity checks."""
    violations = []
    violations.extend(lint_location_change(text, ledger))
    violations.extend(lint_who_present(text, ledger))
    violations.extend(lint_timeline(text, ledger))
    return violations
