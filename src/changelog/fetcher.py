"""
Fetches release notes and changelogs from GitHub or package registries.
"""

import re
import requests
from typing import Optional, List
from src.scanner.base_scanner import DependencyInfo
from src.utils import get_logger, truncate


logger = get_logger(__name__)

GITHUB_API = "https://api.github.com"
REQUEST_TIMEOUT = 10


class ChangelogFetcher:
    """Fetches release notes for updated dependencies."""

    def __init__(self, github_token: Optional[str] = None):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"

    def fetch_all(self, dependencies: List[DependencyInfo]) -> List[DependencyInfo]:
        """Fetch release notes for each dependency in place."""
        for dep in dependencies:
            dep.release_notes = self._fetch_notes(dep)
        return dependencies

    def _fetch_notes(self, dep: DependencyInfo) -> Optional[str]:
        """Try to get release notes from GitHub or fallback to registry URL."""
        # Try to detect GitHub repo from changelog_url
        if dep.changelog_url:
            repo = self._extract_github_repo(dep.changelog_url)
            if repo:
                notes = self._fetch_github_release(repo, dep.latest_version)
                if notes:
                    return truncate(notes, 500)

        # Fallback: return changelog URL as text hint
        if dep.changelog_url:
            return f"See release notes: {dep.changelog_url}"

        return None

    def _extract_github_repo(self, url: str) -> Optional[str]:
        """Extract owner/repo from a GitHub URL."""
        match = re.search(r"github\.com/([^/]+/[^/]+?)(?:\.git|/|$)", url)
        return match.group(1) if match else None

    def _fetch_github_release(self, repo: str, version: str) -> Optional[str]:
        """Fetch GitHub release notes for a specific version tag."""
        # Try common tag formats
        tag_candidates = [
            f"v{version}",
            version,
            f"release-{version}",
            f"release/v{version}",
        ]

        for tag in tag_candidates:
            try:
                url = f"{GITHUB_API}/repos/{repo}/releases/tags/{tag}"
                resp = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    data = resp.json()
                    body = data.get("body", "").strip()
                    if body:
                        return body
            except requests.RequestException:
                pass

        # Try fetching the latest release as fallback
        try:
            url = f"{GITHUB_API}/repos/{repo}/releases/latest"
            resp = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                tag = data.get("tag_name", "")
                body = data.get("body", "").strip()
                if body and tag:
                    return f"(Latest release {tag})\n{body}"
        except requests.RequestException:
            pass

        return None
