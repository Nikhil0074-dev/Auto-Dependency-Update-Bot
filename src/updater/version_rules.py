"""
Version update rules and safety checks.
"""

import re
from typing import Optional
from src.scanner.base_scanner import DependencyInfo
from src.utils import parse_version


RISK_COLORS = {
    "major": "🔴",
    "minor": "🟡",
    "patch": "🟢",
    "unknown": "⚪",
}


def get_risk_label(dep: DependencyInfo) -> str:
    """Return a risk label with emoji for the update type."""
    emoji = RISK_COLORS.get(dep.update_type, "⚪")
    return f"{emoji} {dep.update_type.upper()}"


def new_pip_version_line(original_line: str, new_version: str) -> Optional[str]:
    """
    Replace the version in a requirements.txt line with a new version.
    Preserves the original operator (==, >=, ~=, etc.).
    Returns None if the line should not be modified.
    """
    stripped = original_line.strip()
    if not stripped or stripped.startswith(("#", "-")):
        return None

    # Remove inline comment for processing
    comment = ""
    if "#" in stripped:
        idx = stripped.index("#")
        comment = "  " + stripped[idx:]
        stripped = stripped[:idx].strip()

    # Replace version after operator
    updated = re.sub(
        r"([><=!~^]+)\s*[\d.\-+a-zA-Z]+",
        lambda m: f"{m.group(1)}{new_version}",
        stripped,
    )

    if updated == stripped:
        # No operator found; append ==version
        match = re.match(r"^([A-Za-z0-9_.\-]+(?:\[.*?\])?)", stripped)
        if match:
            updated = f"{match.group(1)}=={new_version}"

    return updated + comment + "\n" if comment else updated + "\n"


def new_npm_version_specifier(original_specifier: str, new_version: str) -> str:
    """
    Return a new npm version specifier preserving the original range prefix (^, ~, =, none).
    """
    match = re.match(r"^([^0-9]*)", original_specifier)
    prefix = match.group(1) if match else ""
    # Keep meaningful prefixes only
    if prefix not in ("^", "~", "", "=", ">=", "<=", ">", "<"):
        prefix = "^"
    return f"{prefix}{new_version}"
