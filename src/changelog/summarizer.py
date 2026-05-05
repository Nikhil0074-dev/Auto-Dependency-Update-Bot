"""
Summarizes changelogs using AI (OpenAI) or rule-based fallback.
"""

from typing import List, Optional
from src.scanner.base_scanner import DependencyInfo
from src.utils import get_logger, truncate


logger = get_logger(__name__)


class ChangelogSummarizer:
    """Summarizes release notes; uses OpenAI when available."""

    def __init__(self, openai_api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.openai_api_key = openai_api_key
        self.model = model
        self._openai_available = self._check_openai()

    def _check_openai(self) -> bool:
        if not self.openai_api_key:
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            logger.info("openai package not installed; using rule-based summarizer.")
            return False

    def summarize_all(self, dependencies: List[DependencyInfo]) -> List[DependencyInfo]:
        """Summarize release notes for each dependency that has them."""
        for dep in dependencies:
            if dep.release_notes:
                dep.release_notes = self._summarize(dep)
        return dependencies

    def _summarize(self, dep: DependencyInfo) -> str:
        """Summarize the release notes for a single dependency."""
        notes = dep.release_notes or ""

        if self._openai_available and len(notes) > 200:
            summary = self._ai_summarize(dep.name, dep.latest_version, notes)
            if summary:
                return summary

        return self._rule_based_summarize(notes)

    def _ai_summarize(self, name: str, version: str, notes: str) -> Optional[str]:
        """Use OpenAI to summarize release notes."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            prompt = (
                f"Summarize these release notes for {name} v{version} in 2-3 bullet points. "
                f"Focus on breaking changes, new features, and security fixes. "
                f"Be concise.\n\nRelease notes:\n{truncate(notes, 1500)}"
            )
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI summarization failed: {e}")
            return None

    def _rule_based_summarize(self, notes: str) -> str:
        """
        Extract meaningful lines from release notes using heuristic rules.
        Keeps lines mentioning: fix, feat, break, security, add, remove, update, deprecat.
        """
        KEYWORDS = (
            "fix", "feat", "break", "security", "add", "remov",
            "updat", "deprecat", "new", "change", "bug", "patch",
            "improvement", "enhancement", "critical",
        )
        lines = notes.splitlines()
        important = []

        for line in lines:
            stripped = line.strip().lstrip("*-# ").strip()
            if not stripped or len(stripped) < 10:
                continue
            if any(kw in stripped.lower() for kw in KEYWORDS):
                important.append(f"- {stripped}")
            if len(important) >= 5:
                break

        if important:
            return "\n".join(important)

        # If nothing matched, return the first 3 non-empty lines
        non_empty = [l.strip() for l in lines if l.strip()]
        return "\n".join(f"- {l}" for l in non_empty[:3]) if non_empty else truncate(notes, 300)
