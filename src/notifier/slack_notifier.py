"""
Slack notification service for dependency updates.
"""

import json
import requests
from typing import List, Optional
from src.scanner.base_scanner import DependencyInfo
from src.utils import get_logger


logger = get_logger(__name__)


class SlackNotifier:
    """Sends Slack notifications when dependency PRs are created."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def notify_pr_created(
        self,
        pr_url: str,
        pr_number: int,
        dependencies: List[DependencyInfo],
    ) -> bool:
        """Send a Slack message about a newly created PR."""
        major_count = sum(1 for d in dependencies if d.update_type == "major")
        minor_count = sum(1 for d in dependencies if d.update_type == "minor")
        patch_count = sum(1 for d in dependencies if d.update_type == "patch")

        color = "#FF4444" if major_count > 0 else "#FFAA00" if minor_count > 0 else "#36a64f"

        attachment = {
            "color": color,
            "title": f"🤖 Dependency Update PR #{pr_number} Created",
            "title_link": pr_url,
            "fields": [
                {"title": "Total Updates", "value": str(len(dependencies)), "short": True},
                {"title": "🔴 Major", "value": str(major_count), "short": True},
                {"title": "🟡 Minor", "value": str(minor_count), "short": True},
                {"title": "🟢 Patch", "value": str(patch_count), "short": True},
            ],
            "footer": "Auto Dependency Bot",
            "footer_icon": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
        }

        # Add top packages
        if dependencies:
            top_pkgs = ", ".join(
                f"`{d.name}` ({d.current_version}→{d.latest_version})"
                for d in dependencies[:5]
            )
            if len(dependencies) > 5:
                top_pkgs += f" and {len(dependencies) - 5} more…"
            attachment["text"] = f"Updated packages: {top_pkgs}"

        payload = {
            "text": f"📦 New dependency update PR ready for review: <{pr_url}|PR #{pr_number}>",
            "attachments": [attachment],
        }

        return self._send(payload)

    def notify_no_updates(self) -> bool:
        """Notify that no updates were found."""
        payload = {
            "text": "✅ Dependency scan complete — all packages are up to date!",
            "icon_emoji": ":white_check_mark:",
        }
        return self._send(payload)

    def _send(self, payload: dict) -> bool:
        """Send a payload to the Slack webhook."""
        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if response.status_code == 200:
                logger.info("Slack notification sent.")
                return True
            else:
                logger.warning(f"Slack webhook returned {response.status_code}: {response.text}")
        except requests.RequestException as e:
            logger.error(f"Failed to send Slack notification: {e}")
        return False
