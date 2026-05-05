"""
Base scanner providing shared interface for all dependency scanners.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class DependencyInfo:
    """Represents a single dependency with its version information."""
    name: str
    current_version: str
    latest_version: str
    ecosystem: str          # "pip" or "npm"
    update_type: str        # "major", "minor", "patch", "none", "unknown"
    homepage: Optional[str] = None
    description: Optional[str] = None
    changelog_url: Optional[str] = None
    release_notes: Optional[str] = None
    is_dev_dependency: bool = False

    @property
    def needs_update(self) -> bool:
        return self.update_type not in ("none", "unknown")

    def __repr__(self) -> str:
        return (
            f"<Dependency {self.name}: {self.current_version} → "
            f"{self.latest_version} [{self.update_type}]>"
        )


class BaseScanner(ABC):
    """Abstract base scanner for dependency files."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)

    @abstractmethod
    def scan(self) -> List[DependencyInfo]:
        """Scan dependencies and return list of DependencyInfo objects."""
        pass

    @abstractmethod
    def get_manifest_path(self) -> Optional[Path]:
        """Return the path to the dependency manifest file."""
        pass

    def manifest_exists(self) -> bool:
        """Check if the manifest file exists."""
        path = self.get_manifest_path()
        return path is not None and path.exists()
