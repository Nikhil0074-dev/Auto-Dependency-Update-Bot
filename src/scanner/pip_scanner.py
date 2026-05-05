"""
Scanner for Python pip dependencies in requirements.txt.
"""

import re
import requests
from pathlib import Path
from typing import List, Optional, Tuple

from .base_scanner import BaseScanner, DependencyInfo
from src.utils import get_logger, classify_update


logger = get_logger(__name__)

PYPI_URL = "https://pypi.org/pypi/{package}/json"
REQUEST_TIMEOUT = 10


def _parse_requirements_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse a single requirements.txt line.
    Returns (package_name, version) or None if the line should be skipped.
    Handles: package==1.0, package>=1.0, package~=1.0, package[extra]==1.0
    """
    line = line.strip()

    # Skip blank lines, comments, -r includes, -e editable installs, URLs
    if not line or line.startswith(("#", "-r", "-e", "http://", "https://", "git+")):
        return None

    # Remove inline comments
    line = line.split("#")[0].strip()

    # Match: name[extras]<operator>version
    match = re.match(r"^([A-Za-z0-9_.\-]+)(?:\[.*?\])?(?:[><=!~^]+(.+))?$", line)
    if not match:
        return None

    name = match.group(1).strip()
    version = (match.group(2) or "").strip().split(",")[0].strip()

    return name, version


def _fetch_pypi_info(package: str) -> Optional[dict]:
    """Fetch package info from PyPI."""
    try:
        url = PYPI_URL.format(package=package)
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"PyPI returned {response.status_code} for {package}")
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch PyPI info for {package}: {e}")
    return None


class PipScanner(BaseScanner):
    """Scans requirements.txt for outdated Python packages."""

    def get_manifest_path(self) -> Optional[Path]:
        candidates = [
            self.project_root / "requirements.txt",
            self.project_root / "requirements" / "base.txt",
            self.project_root / "requirements" / "prod.txt",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def scan(self) -> List[DependencyInfo]:
        manifest = self.get_manifest_path()
        if not manifest:
            logger.info("No requirements.txt found, skipping pip scan.")
            return []

        logger.info(f"Scanning pip dependencies in: {manifest}")
        dependencies = []

        with open(manifest, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            parsed = _parse_requirements_line(line)
            if not parsed:
                continue

            name, current_version = parsed

            pypi_data = _fetch_pypi_info(name)
            if not pypi_data:
                logger.warning(f"Could not fetch info for {name}, skipping.")
                continue

            try:
                info = pypi_data["info"]
                latest_version = info.get("version", "")

                if not latest_version:
                    continue

                update_type = classify_update(current_version, latest_version) if current_version else "unknown"

                dep = DependencyInfo(
                    name=name,
                    current_version=current_version or "unspecified",
                    latest_version=latest_version,
                    ecosystem="pip",
                    update_type=update_type,
                    homepage=info.get("home_page") or info.get("project_url"),
                    description=info.get("summary", ""),
                    changelog_url=_extract_changelog_url(pypi_data),
                )
                dependencies.append(dep)
                logger.debug(f"  {dep}")
            except (KeyError, TypeError) as e:
                logger.warning(f"Error parsing PyPI data for {name}: {e}")

        outdated = [d for d in dependencies if d.needs_update]
        logger.info(f"Found {len(outdated)} outdated pip packages out of {len(dependencies)} total.")
        return dependencies


def _extract_changelog_url(pypi_data: dict) -> Optional[str]:
    """Try to extract changelog URL from PyPI project URLs."""
    try:
        urls = pypi_data.get("info", {}).get("project_urls") or {}
        for key in ("Changelog", "CHANGELOG", "History", "Release Notes", "Changes"):
            if key in urls:
                return urls[key]
    except (AttributeError, TypeError):
        pass
    return None
