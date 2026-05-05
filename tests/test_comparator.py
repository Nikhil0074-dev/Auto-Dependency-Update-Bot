"""
Tests for version comparator and helpers.
"""

import pytest
from src.comparator.version_comparator import VersionComparator
from src.config.settings import UpdateRules
from src.scanner.base_scanner import DependencyInfo
from src.utils.helpers import classify_update, sanitize_branch_name, format_table


# ─── classify_update ──────────────────────────────────────────────


class TestClassifyUpdate:
    def test_patch(self):
        assert classify_update("1.0.0", "1.0.1") == "patch"

    def test_minor(self):
        assert classify_update("1.0.0", "1.1.0") == "minor"

    def test_major(self):
        assert classify_update("1.0.0", "2.0.0") == "major"

    def test_same_version(self):
        assert classify_update("1.0.0", "1.0.0") == "none"

    def test_downgrade(self):
        assert classify_update("2.0.0", "1.0.0") == "none"

    def test_invalid_version(self):
        assert classify_update("invalid", "1.0.0") == "unknown"

    def test_empty_current(self):
        result = classify_update("", "1.0.0")
        assert result == "unknown"


# ─── VersionComparator ────────────────────────────────────────────


def make_dep(name, current, latest, update_type, ecosystem="pip"):
    return DependencyInfo(
        name=name,
        current_version=current,
        latest_version=latest,
        ecosystem=ecosystem,
        update_type=update_type,
    )


class TestVersionComparator:
    def _make_deps(self):
        return [
            make_dep("requests", "2.28.0", "2.32.0", "minor"),
            make_dep("flask", "2.0.0", "3.0.0", "major"),
            make_dep("click", "8.1.0", "8.1.7", "patch"),
            make_dep("pinned-pkg", "1.0.0", "2.0.0", "major"),
            make_dep("skip-this", "1.0.0", "2.0.0", "major"),
            make_dep("up-to-date", "1.0.0", "1.0.0", "none"),
        ]

    def test_default_rules(self):
        rules = UpdateRules(allow_major=False, allow_minor=True, allow_patch=True)
        comparator = VersionComparator(rules)
        deps = self._make_deps()
        approved = comparator.filter(deps)
        names = [d.name for d in approved]
        assert "requests" in names
        assert "click" in names
        assert "flask" not in names  # major blocked
        assert "up-to-date" not in names  # no update needed

    def test_allow_major(self):
        rules = UpdateRules(allow_major=True, allow_minor=True, allow_patch=True)
        comparator = VersionComparator(rules)
        deps = [make_dep("flask", "2.0.0", "3.0.0", "major")]
        approved = comparator.filter(deps)
        assert len(approved) == 1

    def test_skip_packages(self):
        rules = UpdateRules(
            allow_major=True, allow_minor=True, allow_patch=True,
            skip_packages=["skip-this"]
        )
        comparator = VersionComparator(rules)
        deps = [
            make_dep("skip-this", "1.0.0", "2.0.0", "major"),
            make_dep("keep-this", "1.0.0", "2.0.0", "major"),
        ]
        approved = comparator.filter(deps)
        assert len(approved) == 1
        assert approved[0].name == "keep-this"

    def test_pinned_packages(self):
        rules = UpdateRules(
            allow_major=True, allow_minor=True, allow_patch=True,
            pin_packages={"pinned-pkg": "1.0.0"}
        )
        comparator = VersionComparator(rules)
        deps = [make_dep("pinned-pkg", "1.0.0", "2.0.0", "major")]
        approved = comparator.filter(deps)
        assert len(approved) == 0

    def test_block_minor(self):
        rules = UpdateRules(allow_major=False, allow_minor=False, allow_patch=True)
        comparator = VersionComparator(rules)
        deps = [make_dep("requests", "2.28.0", "2.32.0", "minor")]
        assert comparator.filter(deps) == []

    def test_empty_input(self):
        rules = UpdateRules()
        comparator = VersionComparator(rules)
        assert comparator.filter([]) == []


# ─── sanitize_branch_name ─────────────────────────────────────────


class TestSanitizeBranchName:
    def test_spaces_to_hyphens(self):
        assert sanitize_branch_name("deps update 2024") == "deps-update-2024"

    def test_slashes_preserved(self):
        result = sanitize_branch_name("deps/auto-update-2024")
        assert "/" in result

    def test_special_chars_removed(self):
        result = sanitize_branch_name("deps@update#2024!")
        assert "@" not in result
        assert "#" not in result

    def test_lowercase(self):
        assert sanitize_branch_name("DEPS/Update") == "deps/update"


# ─── format_table ────────────────────────────────────────────────


class TestFormatTable:
    def test_basic_table(self):
        headers = ["Name", "Version"]
        rows = [["requests", "2.32.0"], ["flask", "3.0.0"]]
        result = format_table(headers, rows)
        assert "Name" in result
        assert "requests" in result
        assert "|" in result
        assert "---" in result

    def test_empty_rows(self):
        result = format_table(["Name"], [])
        assert result == ""
