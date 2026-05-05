"""
Git branch management for the dependency bot.
"""

import subprocess
from datetime import datetime
from typing import Optional
from src.utils import get_logger, sanitize_branch_name


logger = get_logger(__name__)


class BranchManager:
    """Creates and manages Git branches for dependency updates."""

    def __init__(self, base_branch: str = "main"):
        self.base_branch = base_branch

    def create_update_branch(self) -> str:
        """Create and checkout a new branch for this week's updates."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        branch_name = sanitize_branch_name(f"deps/auto-update-{date_str}")

        try:
            # Ensure we're on the base branch and up to date
            self._run(["git", "checkout", self.base_branch])
            self._run(["git", "pull", "origin", self.base_branch])

            # Check if branch already exists (idempotent)
            existing = self._run(
                ["git", "branch", "--list", branch_name],
                capture=True
            )
            if branch_name in (existing or ""):
                logger.info(f"Branch {branch_name} already exists, checking out.")
                self._run(["git", "checkout", branch_name])
            else:
                self._run(["git", "checkout", "-b", branch_name])
                logger.info(f"Created branch: {branch_name}")

            return branch_name
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create branch: {e}")
            raise

    def get_current_branch(self) -> str:
        result = self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
        return (result or "").strip()

    def _run(
        self,
        cmd: list,
        capture: bool = False,
        check: bool = True,
    ) -> Optional[str]:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=check,
        )
        return result.stdout if capture else None
