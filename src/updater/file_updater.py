"""
Updates dependency manifest files (requirements.txt, package.json) in place.
"""

import json
import re
from pathlib import Path
from typing import List, Dict
from src.scanner.base_scanner import DependencyInfo
from src.updater.version_rules import new_pip_version_line, new_npm_version_specifier
from src.utils import get_logger


logger = get_logger(__name__)


class FileUpdater:
    """Updates requirements.txt and package.json with new dependency versions."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)

    def apply_updates(self, dependencies: List[DependencyInfo]) -> Dict[str, List[str]]:
        """
        Apply all updates to manifest files.
        Returns a dict mapping file paths to lists of changes made.
        """
        pip_deps = [d for d in dependencies if d.ecosystem == "pip" and d.needs_update]
        npm_deps = [d for d in dependencies if d.ecosystem == "npm" and d.needs_update]

        changes = {}

        if pip_deps:
            pip_changes = self._update_requirements(pip_deps)
            if pip_changes:
                changes["requirements.txt"] = pip_changes

        if npm_deps:
            npm_changes = self._update_package_json(npm_deps)
            if npm_changes:
                changes["package.json"] = npm_changes

        return changes

    def _update_requirements(self, deps: List[DependencyInfo]) -> List[str]:
        """Update requirements.txt and return a list of change descriptions."""
        candidates = [
            self.project_root / "requirements.txt",
            self.project_root / "requirements" / "base.txt",
            self.project_root / "requirements" / "prod.txt",
        ]
        req_file = next((p for p in candidates if p.exists()), None)

        if not req_file:
            logger.warning("requirements.txt not found, skipping pip updates.")
            return []

        version_map: Dict[str, str] = {
            d.name.lower(): d.latest_version for d in deps
        }

        with open(req_file, "r", encoding="utf-8") as f:
            original_lines = f.readlines()

        updated_lines = []
        changes = []

        for line in original_lines:
            stripped = line.strip().split("#")[0].strip()
            match = re.match(r"^([A-Za-z0-9_.\-]+)", stripped)

            if match:
                pkg_name = match.group(1).lower()
                if pkg_name in version_map:
                    new_line = new_pip_version_line(line, version_map[pkg_name])
                    if new_line and new_line != line:
                        # Find original dep for display
                        dep = next((d for d in deps if d.name.lower() == pkg_name), None)
                        if dep:
                            changes.append(
                                f"{dep.name}: {dep.current_version} → {dep.latest_version}"
                            )
                        updated_lines.append(new_line)
                        continue

            updated_lines.append(line)

        if changes:
            with open(req_file, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)
            logger.info(f"Updated {len(changes)} packages in {req_file}")

        return changes

    def _update_package_json(self, deps: List[DependencyInfo]) -> List[str]:
        """Update package.json and return a list of change descriptions."""
        pkg_file = self.project_root / "package.json"
        if not pkg_file.exists():
            logger.warning("package.json not found, skipping npm updates.")
            return []

        with open(pkg_file, "r", encoding="utf-8") as f:
            pkg_data = json.load(f)

        changes = []

        for dep in deps:
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                if section in pkg_data and dep.name in pkg_data[section]:
                    old_specifier = pkg_data[section][dep.name]
                    new_specifier = new_npm_version_specifier(old_specifier, dep.latest_version)
                    pkg_data[section][dep.name] = new_specifier
                    changes.append(f"{dep.name}: {dep.current_version} → {dep.latest_version}")
                    logger.debug(f"  npm {dep.name}: {old_specifier} → {new_specifier}")
                    break

        if changes:
            with open(pkg_file, "w", encoding="utf-8") as f:
                json.dump(pkg_data, f, indent=2)
                f.write("\n")
            logger.info(f"Updated {len(changes)} packages in {pkg_file}")

        return changes
