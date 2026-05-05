"""
Tests for the file updater and version_rules helpers.
"""

import json
import pytest
from pathlib import Path

from src.updater.file_updater import FileUpdater
from src.updater.version_rules import (
    new_pip_version_line,
    new_npm_version_specifier,
    get_risk_label,
)
from src.scanner.base_scanner import DependencyInfo


# ─── new_pip_version_line ────────────────────────────────────────


class TestNewPipVersionLine:
    def test_pinned(self):
        result = new_pip_version_line("requests==2.28.0\n", "2.32.0")
        assert "2.32.0" in result
        assert "==" in result

    def test_tilde(self):
        result = new_pip_version_line("flask~=2.0.0\n", "3.0.0")
        assert "3.0.0" in result

    def test_ge(self):
        result = new_pip_version_line("numpy>=1.24.0\n", "2.0.0")
        assert "2.0.0" in result

    def test_comment_preserved(self):
        result = new_pip_version_line("requests==2.28.0  # HTTP client\n", "2.32.0")
        assert "# HTTP client" in result
        assert "2.32.0" in result

    def test_comment_line_returns_none(self):
        assert new_pip_version_line("# a comment\n", "1.0.0") is None

    def test_empty_line_returns_none(self):
        assert new_pip_version_line("\n", "1.0.0") is None


# ─── new_npm_version_specifier ───────────────────────────────────


class TestNewNpmVersionSpecifier:
    def test_caret(self):
        assert new_npm_version_specifier("^4.18.0", "4.19.2") == "^4.19.2"

    def test_tilde(self):
        assert new_npm_version_specifier("~4.18.0", "4.18.3") == "~4.18.3"

    def test_exact(self):
        assert new_npm_version_specifier("4.18.0", "4.19.2") == "4.19.2"

    def test_wildcard_prefix_normalized(self):
        # Unknown prefix should default to ^
        result = new_npm_version_specifier("*", "4.19.2")
        assert "4.19.2" in result


# ─── get_risk_label ──────────────────────────────────────────────


class TestGetRiskLabel:
    def _dep(self, update_type):
        return DependencyInfo(
            name="pkg", current_version="1.0.0", latest_version="2.0.0",
            ecosystem="pip", update_type=update_type,
        )

    def test_major_red(self):
        label = get_risk_label(self._dep("major"))
        assert "🔴" in label
        assert "MAJOR" in label

    def test_minor_yellow(self):
        label = get_risk_label(self._dep("minor"))
        assert "🟡" in label

    def test_patch_green(self):
        label = get_risk_label(self._dep("patch"))
        assert "🟢" in label


# ─── FileUpdater ─────────────────────────────────────────────────


def make_dep(name, current, latest, update_type, ecosystem="pip"):
    return DependencyInfo(
        name=name,
        current_version=current,
        latest_version=latest,
        ecosystem=ecosystem,
        update_type=update_type,
    )


class TestFileUpdater:
    def test_update_requirements_txt(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.28.0\nflask==2.0.0\n")

        updater = FileUpdater(project_root=str(tmp_path))
        deps = [
            make_dep("requests", "2.28.0", "2.32.0", "minor"),
            make_dep("flask", "2.0.0", "3.0.0", "major"),
        ]
        changes = updater.apply_updates(deps)

        assert "requirements.txt" in changes
        assert len(changes["requirements.txt"]) == 2

        content = req.read_text()
        assert "2.32.0" in content
        assert "3.0.0" in content

    def test_update_package_json(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg_data = {"dependencies": {"express": "^4.18.0"}}
        pkg.write_text(json.dumps(pkg_data))

        updater = FileUpdater(project_root=str(tmp_path))
        deps = [make_dep("express", "4.18.0", "4.19.2", "patch", ecosystem="npm")]
        changes = updater.apply_updates(deps)

        assert "package.json" in changes

        updated = json.loads(pkg.read_text())
        assert "4.19.2" in updated["dependencies"]["express"]

    def test_no_manifest_no_crash(self, tmp_path):
        updater = FileUpdater(project_root=str(tmp_path))
        deps = [make_dep("requests", "2.28.0", "2.32.0", "minor")]
        changes = updater.apply_updates(deps)
        assert changes == {} or changes.get("requirements.txt", []) == []

    def test_preserves_unmodified_packages(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.28.0\ndjango==4.2.0\n")

        updater = FileUpdater(project_root=str(tmp_path))
        deps = [make_dep("requests", "2.28.0", "2.32.0", "minor")]
        updater.apply_updates(deps)

        content = req.read_text()
        assert "django==4.2.0" in content
