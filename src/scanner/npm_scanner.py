"""
Scanner for Node.js npm dependencies in package.json.
"""

import json
import requests
from pathlib import Path
from typing import List, Optional

from .base_scanner import BaseScanner, DependencyInfo
from src.utils import get_logger, classify_update


logger = get_logger(__name__)

NPM_REGISTRY_URL = "https://registry.npmjs.org/{package}/latest"
REQUEST_TIMEOUT = 10


def _fetch_npm_info(package: str) -> Optional[dict]:
    """Fetch latest package info from npm registry."""
    try:
        # Handle scoped packages like @babel/core
        encoded = package.replace("/", "%2F")
        url = NPM_REGISTRY_URL.format(package=encoded)
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"npm registry returned {response.status_code} for {package}")
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch npm info for {package}: {e}")
    return None


def _clean_version(version: str) -> str:
    """Remove semver range operators from a version string."""
    return version.lstrip("^~>=<").strip().split(" ")[0]


class NpmScanner(BaseScanner):
    """Scans package.json for outdated Node.js packages."""

    def get_manifest_path(self) -> Optional[Path]:
        path = self.project_root / "package.json"
        return path if path.exists() else None

    def scan(self) -> List[DependencyInfo]:
        manifest = self.get_manifest_path()
        if not manifest:
            logger.info("No package.json found, skipping npm scan.")
            return []

        logger.info(f"Scanning npm dependencies in: {manifest}")

        try:
            with open(manifest, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read package.json: {e}")
            return []

        dependencies = {}
        for dep_name, version in pkg_data.get("dependencies", {}).items():
            dependencies[dep_name] = (version, False)
        for dep_name, version in pkg_data.get("devDependencies", {}).items():
            dependencies[dep_name] = (version, True)

        results = []
        for name, (raw_version, is_dev) in dependencies.items():
            current_version = _clean_version(raw_version)

            npm_data = _fetch_npm_info(name)
            if not npm_data:
                logger.warning(f"Could not fetch npm info for {name}, skipping.")
                continue

            try:
                latest_version = npm_data.get("version", "")
                if not latest_version:
                    continue

                update_type = classify_update(current_version, latest_version)

                dep = DependencyInfo(
                    name=name,
                    current_version=current_version or "unspecified",
                    latest_version=latest_version,
                    ecosystem="npm",
                    update_type=update_type,
                    homepage=npm_data.get("homepage"),
                    description=npm_data.get("description", ""),
                    changelog_url=_extract_npm_changelog(npm_data),
                    is_dev_dependency=is_dev,
                )
                results.append(dep)
                logger.debug(f"  {dep}")
            except (KeyError, TypeError) as e:
                logger.warning(f"Error parsing npm data for {name}: {e}")

        outdated = [d for d in results if d.needs_update]
        logger.info(f"Found {len(outdated)} outdated npm packages out of {len(results)} total.")
        return results


def _extract_npm_changelog(npm_data: dict) -> Optional[str]:
    """Try to extract a changelog URL from npm package metadata."""
    repo = npm_data.get("repository")
    if isinstance(repo, dict):
        url = repo.get("url", "")
    elif isinstance(repo, str):
        url = repo
    else:
        return None

    # Convert git+https or git:// to plain HTTPS
    url = url.replace("git+https://", "https://").replace("git://", "https://")
    url = url.removesuffix(".git")

    if "github.com" in url:
        return url + "/releases"
    return None
