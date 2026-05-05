"""
Git commit management for the dependency bot.
"""

import subprocess
from typing import List
from src.utils import get_logger


logger = get_logger(__name__)


class CommitManager:
    """Stages and commits dependency update changes."""

    def __init__(self, bot_name: str = "Dependency Bot", bot_email: str = "bot@example.com"):
        self.bot_name = bot_name
        self.bot_email = bot_email

    def configure_git(self):
        """Set git user config for the bot."""
        subprocess.run(
            ["git", "config", "user.name", self.bot_name], check=True
        )
        subprocess.run(
            ["git", "config", "user.email", self.bot_email], check=True
        )

    def stage_and_commit(self, files: List[str], message: str) -> bool:
        """
        Stage specified files and create a commit.
        Returns True if a commit was made, False if nothing to commit.
        """
        self.configure_git()

        # Stage specified files
        for file_path in files:
            try:
                subprocess.run(["git", "add", file_path], check=True)
            except subprocess.CalledProcessError:
                logger.warning(f"Could not stage {file_path}")

        # Check if there's anything to commit
        status = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
        )
        staged_files = status.stdout.strip()

        if not staged_files:
            logger.info("No staged changes to commit.")
            return False

        try:
            subprocess.run(["git", "commit", "-m", message], check=True)
            logger.info(f"Committed changes: {message}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Commit failed: {e}")
            raise

    def push_branch(self, branch_name: str):
        """Push the branch to origin."""
        try:
            subprocess.run(
                ["git", "push", "origin", branch_name, "--force-with-lease"],
                check=True,
            )
            logger.info(f"Pushed branch: {branch_name}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Push failed: {e}")
            raise
