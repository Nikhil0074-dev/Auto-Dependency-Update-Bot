"""
Tests for pip and npm scanners.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import os

from src.scanner.pip_scanner import PipScanner, _parse_requirements_line
from src.scanner.npm_scanner import NpmScanner, _clean_version
from src.scanner.base_scanner import DependencyInfo


# ─── Helpers ──────────────────────────────────────────────────────


FAKE_PYPI_RESPONSE = {
    "info": {
        "name": "requests",
        "version": "2.32.0",
        "summary": "Python HTTP for Humans.",
        "home_page": "https://requests.readthedocs.io",
        "project_urls": {"Changelog": "https://github.com/psf/requests/blob/main/HISTORY.md"},
    },
    "releases": {},
}

FAKE_NPM_RESPONSE = {
    "name": "express",
    "version": "4.19.2",
    "description": "Fast, unopinionated, minimalist web framework",
    "homepage": "https://expressjs.com/",
    "repository": {"type": "git", "url": "git+https://github.com/expressjs/express.git"},
}


# ─── parse_requirements_line ──────────────────────────────────────


class TestParseRequirementsLine:
    def test_pinned_version(self):
        result = _parse_requirements_line("requests==2.28.0")
        assert result == ("requests", "2.28.0")

    def test_tilde_operator(self):
        result = _parse_requirements_line("flask~=2.3.0")
        assert result == ("flask", "2.3.0")

    def test_ge_operator(self):
        result = _parse_requirements_line("numpy>=1.24.0")
        assert result == ("numpy", "1.24.0")

    def test_extra_in_name(self):
        result = _parse_requirements_line("uvicorn[standard]==0.22.0")
        assert result is not None
        assert result[0] == "uvicorn"
        assert result[1] == "0.22.0"

    def test_comment_line(self):
        assert _parse_requirements_line("# this is a comment") is None

    def test_blank_line(self):
        assert _parse_requirements_line("") is None
        assert _parse_requirements_line("   ") is None

    def test_editable_install(self):
        assert _parse_requirements_line("-e .") is None

    def test_recursive_include(self):
        assert _parse_requirements_line("-r requirements/base.txt") is None

    def test_inline_comment_stripped(self):
        result = _parse_requirements_line("django==4.2.0  # production")
        assert result is not None
        assert result[0] == "django"
        assert result[1] == "4.2.0"

    def test_no_version(self):
        result = _parse_requirements_line("pytest")
        assert result is not None
        assert result[0] == "pytest"
        assert result[1] == ""


# ─── PipScanner ───────────────────────────────────────────────────


class TestPipScanner:
    def test_no_manifest(self, tmp_path):
        scanner = PipScanner(project_root=str(tmp_path))
        assert not scanner.manifest_exists()
        result = scanner.scan()
        assert result == []

    def test_scan_outdated(self, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.20.0\n")

        with patch("src.scanner.pip_scanner._fetch_pypi_info", return_value=FAKE_PYPI_RESPONSE):
            scanner = PipScanner(project_root=str(tmp_path))
            deps = scanner.scan()

        assert len(deps) == 1
        dep = deps[0]
        assert dep.name == "requests"
        assert dep.current_version == "2.20.0"
        assert dep.latest_version == "2.32.0"
        assert dep.update_type == "minor"
        assert dep.needs_update is True
        assert dep.ecosystem == "pip"

    def test_scan_up_to_date(self, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.32.0\n")

        with patch("src.scanner.pip_scanner._fetch_pypi_info", return_value=FAKE_PYPI_RESPONSE):
            scanner = PipScanner(project_root=str(tmp_path))
            deps = scanner.scan()

        assert len(deps) == 1
        assert deps[0].needs_update is False

    def test_scan_pypi_failure(self, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.20.0\n")

        with patch("src.scanner.pip_scanner._fetch_pypi_info", return_value=None):
            scanner = PipScanner(project_root=str(tmp_path))
            deps = scanner.scan()

        assert deps == []


# ─── clean_version ────────────────────────────────────────────────


class TestCleanVersion:
    def test_caret(self):
        assert _clean_version("^4.18.0") == "4.18.0"

    def test_tilde(self):
        assert _clean_version("~2.0.0") == "2.0.0"

    def test_plain(self):
        assert _clean_version("1.0.0") == "1.0.0"

    def test_ge(self):
        assert _clean_version(">=1.0.0") == "1.0.0"


# ─── NpmScanner ───────────────────────────────────────────────────


class TestNpmScanner:
    def test_no_manifest(self, tmp_path):
        scanner = NpmScanner(project_root=str(tmp_path))
        assert not scanner.manifest_exists()
        result = scanner.scan()
        assert result == []

    def test_scan_outdated(self, tmp_path):
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text('{"dependencies": {"express": "^4.18.0"}}')

        with patch("src.scanner.npm_scanner._fetch_npm_info", return_value=FAKE_NPM_RESPONSE):
            scanner = NpmScanner(project_root=str(tmp_path))
            deps = scanner.scan()

        assert len(deps) == 1
        dep = deps[0]
        assert dep.name == "express"
        assert dep.current_version == "4.18.0"
        assert dep.latest_version == "4.19.2"
        assert dep.update_type == "minor"  # 4.18 → 4.19 is a minor bump
        assert dep.needs_update is True
        assert dep.ecosystem == "npm"
        assert dep.is_dev_dependency is False

    def test_dev_dependency_flagged(self, tmp_path):
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text('{"devDependencies": {"express": "^4.18.0"}}')

        with patch("src.scanner.npm_scanner._fetch_npm_info", return_value=FAKE_NPM_RESPONSE):
            scanner = NpmScanner(project_root=str(tmp_path))
            deps = scanner.scan()

        assert len(deps) == 1
        assert deps[0].is_dev_dependency is True

    def test_invalid_json(self, tmp_path):
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text("not valid json")

        scanner = NpmScanner(project_root=str(tmp_path))
        deps = scanner.scan()
        assert deps == []
