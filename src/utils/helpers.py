"""
Common helper functions for the dependency bot.
"""

import re
from typing import Optional, Tuple
from packaging.version import Version, InvalidVersion


def parse_version(version_str: str) -> Optional[Version]:
    """Safely parse a version string."""
    try:
        cleaned = re.sub(r"[^\d.\-+a-zA-Z]", "", version_str.strip())
        return Version(cleaned)
    except (InvalidVersion, AttributeError):
        return None


def classify_update(current: str, latest: str) -> str:
    """
    Classify an update as 'major', 'minor', 'patch', or 'unknown'.
    Uses semantic versioning rules.
    """
    cur = parse_version(current)
    lat = parse_version(latest)

    if cur is None or lat is None:
        return "unknown"

    if lat <= cur:
        return "none"

    if lat.major > cur.major:
        return "major"
    elif lat.minor > cur.minor:
        return "minor"
    else:
        return "patch"


def truncate(text: str, max_length: int = 300) -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def sanitize_branch_name(name: str) -> str:
    """Convert a string to a valid git branch name."""
    sanitized = re.sub(r"[^a-zA-Z0-9/_.-]", "-", name)
    sanitized = re.sub(r"-+", "-", sanitized)
    return sanitized.strip("-").lower()


def format_table(headers: list, rows: list) -> str:
    """Format data as a markdown table."""
    if not rows:
        return ""

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(cells):
        return "| " + " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(cells)) + " |"

    separator = "| " + " | ".join("-" * w for w in col_widths) + " |"
    lines = [fmt_row(headers), separator] + [fmt_row(r) for r in rows]
    return "\n".join(lines)
