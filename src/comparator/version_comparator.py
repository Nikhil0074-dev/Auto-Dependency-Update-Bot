"""
Version comparator: filters dependencies based on update rules.
"""

from typing import List
from src.scanner.base_scanner import DependencyInfo
from src.config.settings import UpdateRules
from src.utils import get_logger


logger = get_logger(__name__)


class VersionComparator:
    """
    Filters a list of dependencies according to the configured update rules.
    Respects major/minor/patch allowances, skip lists, and pinned versions.
    """

    def __init__(self, rules: UpdateRules):
        self.rules = rules

    def filter(self, dependencies: List[DependencyInfo]) -> List[DependencyInfo]:
        """Return only the dependencies that should be updated."""
        approved = []

        for dep in dependencies:
            if not dep.needs_update:
                continue

            reason = self._should_skip(dep)
            if reason:
                logger.info(f"  Skipping {dep.name}: {reason}")
                continue

            approved.append(dep)
            logger.info(f"  Approved: {dep.name} {dep.current_version} → {dep.latest_version} [{dep.update_type}]")

        logger.info(f"Approved {len(approved)} updates after filtering.")
        return approved

    def _should_skip(self, dep: DependencyInfo) -> str:
        """Return a reason string if the dependency should be skipped, else empty string."""
        # Skip list
        if dep.name in self.rules.skip_packages:
            return "in skip list"

        # Pinned packages
        if dep.name in self.rules.pin_packages:
            pinned = self.rules.pin_packages[dep.name]
            return f"pinned to {pinned}"

        # Major version control
        if dep.update_type == "major" and not self.rules.allow_major:
            return "major update not allowed"

        if dep.update_type == "minor" and not self.rules.allow_minor:
            return "minor update not allowed"

        if dep.update_type == "patch" and not self.rules.allow_patch:
            return "patch update not allowed"

        if dep.update_type == "unknown":
            return "unknown update type"

        return ""
