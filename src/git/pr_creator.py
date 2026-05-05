"""
Creates Pull Requests on GitHub via the GitHub REST API.
"""

import requests
from datetime import datetime
from typing import List, Optional
from src.scanner.base_scanner import DependencyInfo
from src.updater.version_rules import get_risk_label
from src.utils import get_logger, format_table


logger = get_logger(__name__)
GITHUB_API = "https://api.github.com"


class PRCreator:
    """Creates a GitHub Pull Request with the dependency updates."""

    def __init__(self, token: str, repo: str, base_branch: str = "main"):
        self.token = token
        self.repo = repo
        self.base_branch = base_branch
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def create_pr(
        self,
        branch_name: str,
        dependencies: List[DependencyInfo],
    ) -> Optional[dict]:
        """Create a PR with a detailed description of all updates."""
        if not self.token or not self.repo:
            logger.warning("GitHub token or repo not configured; skipping PR creation.")
            return None

        title = self._build_title(dependencies)
        body = self._build_body(dependencies)

        payload = {
            "title": title,
            "head": branch_name,
            "base": self.base_branch,
            "body": body,
            "draft": False,
        }

        url = f"{GITHUB_API}/repos/{self.repo}/pulls"
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=15)
            if response.status_code == 201:
                pr_data = response.json()
                pr_url = pr_data.get("html_url", "")
                pr_number = pr_data.get("number", "")
                logger.info(f"Created PR #{pr_number}: {pr_url}")
                return pr_data
            elif response.status_code == 422:
                # PR might already exist
                logger.warning("PR already exists or branch has no changes.")
                return self._get_existing_pr(branch_name)
            else:
                logger.error(
                    f"Failed to create PR: {response.status_code} - {response.text[:200]}"
                )
        except requests.RequestException as e:
            logger.error(f"GitHub API request failed: {e}")

        return None

    def _get_existing_pr(self, branch_name: str) -> Optional[dict]:
        """Find an existing open PR for this branch."""
        url = f"{GITHUB_API}/repos/{self.repo}/pulls"
        params = {"head": f"{self.repo.split('/')[0]}:{branch_name}", "state": "open"}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                prs = resp.json()
                if prs:
                    return prs[0]
        except requests.RequestException:
            pass
        return None

    def _build_title(self, deps: List[DependencyInfo]) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        ecosystems = sorted({d.ecosystem for d in deps})
        eco_str = " + ".join(e.upper() for e in ecosystems)
        return f"🤖 Auto Dependency Updates [{eco_str}] — {date_str}"

    def _build_body(self, deps: List[DependencyInfo]) -> str:
        lines = [
            "## 🤖 Automated Dependency Updates",
            "",
            f"This PR was automatically generated on **{datetime.now().strftime('%A, %B %d, %Y')}** "
            f"by the [Auto Dependency Bot](https://github.com/features/actions).",
            "",
            "### 📦 Updated Packages",
            "",
        ]

        # Group by ecosystem
        for ecosystem in ("pip", "npm"):
            eco_deps = [d for d in deps if d.ecosystem == ecosystem]
            if not eco_deps:
                continue

            emoji = "🐍" if ecosystem == "pip" else "📦"
            lines.append(f"#### {emoji} {ecosystem.upper()}")
            lines.append("")

            headers = ["Package", "From", "To", "Risk", "Notes"]
            rows = []
            for dep in eco_deps:
                changelog_link = (
                    f"[Release Notes]({dep.changelog_url})" if dep.changelog_url else "—"
                )
                rows.append([
                    f"`{dep.name}`",
                    dep.current_version,
                    dep.latest_version,
                    get_risk_label(dep),
                    changelog_link,
                ])
            lines.append(format_table(headers, rows))
            lines.append("")

        # Changelog summaries
        deps_with_notes = [d for d in deps if d.release_notes]
        if deps_with_notes:
            lines.append("### 📋 Changelog Highlights")
            lines.append("")
            for dep in deps_with_notes[:10]:  # Limit to 10 to keep PR readable
                lines.append(f"<details>")
                lines.append(f"<summary><strong>{dep.name}</strong> {dep.current_version} → {dep.latest_version}</summary>")
                lines.append("")
                lines.append(dep.release_notes)
                lines.append("")
                lines.append("</details>")
                lines.append("")

        # Summary stats
        major = sum(1 for d in deps if d.update_type == "major")
        minor = sum(1 for d in deps if d.update_type == "minor")
        patch = sum(1 for d in deps if d.update_type == "patch")

        lines += [
            "---",
            "### 📊 Summary",
            "",
            f"- Total updates: **{len(deps)}**",
            f"- 🔴 Major: **{major}**",
            f"- 🟡 Minor: **{minor}**",
            f"- 🟢 Patch: **{patch}**",
            "",
            "---",
            "> ⚠️ **Review carefully before merging.** Major version bumps may contain breaking changes.",
            "> Run your test suite to verify compatibility.",
        ]

        return "\n".join(lines)
