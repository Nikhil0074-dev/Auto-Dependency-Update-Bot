"""
Auto Dependency Update Bot — Main Entry Point
Orchestrates the full pipeline: scan → compare → fetch changelog → update → PR → notify
"""

import sys
from pathlib import Path
from typing import List

# Ensure src/ is on the path when running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_settings
from src.scanner import PipScanner, NpmScanner, DependencyInfo
from src.comparator import VersionComparator
from src.changelog import ChangelogFetcher, ChangelogSummarizer
from src.updater import FileUpdater
from src.git import BranchManager, CommitManager, PRCreator
from src.notifier import SlackNotifier, EmailNotifier
from src.utils import get_logger


def run():
    settings = load_settings()
    logger = get_logger("dependency-bot", settings.log_level)

    logger.info("=" * 60)
    logger.info("  🤖 Auto Dependency Update Bot Starting")
    logger.info("=" * 60)

    if settings.dry_run:
        logger.info("⚠️  DRY RUN mode — no files will be modified, no PRs created.")

    # ── Step 1: Scan dependencies ──────────────────────────────────
    logger.info("\n[1/6] Scanning dependencies...")
    all_deps: List[DependencyInfo] = []

    if settings.scan_pip:
        pip_scanner = PipScanner()
        all_deps.extend(pip_scanner.scan())

    if settings.scan_npm:
        npm_scanner = NpmScanner()
        all_deps.extend(npm_scanner.scan())

    if not all_deps:
        logger.info("No dependencies found. Check that requirements.txt or package.json exists.")
        _notify_no_updates(settings, logger)
        return

    # ── Step 2: Filter by update rules ────────────────────────────
    logger.info("\n[2/6] Filtering by update rules...")
    comparator = VersionComparator(settings.update_rules)
    approved_deps = comparator.filter(all_deps)

    if not approved_deps:
        logger.info("✅ All dependencies are up to date (or filtered by rules). Nothing to do.")
        _notify_no_updates(settings, logger)
        return

    logger.info(f"   {len(approved_deps)} updates approved for processing.")

    # ── Step 3: Fetch changelogs ───────────────────────────────────
    logger.info("\n[3/6] Fetching changelogs...")
    fetcher = ChangelogFetcher(github_token=settings.git.token)
    approved_deps = fetcher.fetch_all(approved_deps)

    summarizer = ChangelogSummarizer(
        openai_api_key=settings.ai.openai_api_key if settings.ai.enabled else None,
        model=settings.ai.model,
    )
    approved_deps = summarizer.summarize_all(approved_deps)

    # ── Step 4: Apply file updates ────────────────────────────────
    logger.info("\n[4/6] Applying file updates...")

    if settings.dry_run:
        for dep in approved_deps:
            logger.info(f"   [DRY RUN] Would update: {dep.name} {dep.current_version} → {dep.latest_version}")
        return

    # Create git branch
    branch_manager = BranchManager(base_branch=settings.git.base_branch)
    branch_name = branch_manager.create_update_branch()

    # Update files
    file_updater = FileUpdater()
    changes_by_file = file_updater.apply_updates(approved_deps)

    if not any(changes_by_file.values()):
        logger.warning("No file changes were made. The files may already be up to date.")
        return

    # ── Step 5: Commit and push ───────────────────────────────────
    logger.info("\n[5/6] Committing and pushing changes...")
    commit_manager = CommitManager(
        bot_name=settings.git.bot_name,
        bot_email=settings.git.bot_email,
    )

    files_to_commit = []
    if "requirements.txt" in changes_by_file:
        files_to_commit.append("requirements.txt")
    if "package.json" in changes_by_file:
        files_to_commit.append("package.json")

    commit_msg = _build_commit_message(approved_deps)
    committed = commit_manager.stage_and_commit(files_to_commit, commit_msg)

    if not committed:
        logger.warning("Nothing committed — files unchanged or already staged.")
        return

    commit_manager.push_branch(branch_name)

    # ── Step 6: Create PR ─────────────────────────────────────────
    logger.info("\n[6/6] Creating Pull Request...")
    pr_creator = PRCreator(
        token=settings.git.token,
        repo=settings.git.repo,
        base_branch=settings.git.base_branch,
    )
    pr_data = pr_creator.create_pr(branch_name, approved_deps)

    pr_url = pr_data.get("html_url", "") if pr_data else ""
    pr_number = pr_data.get("number", 0) if pr_data else 0

    # ── Notifications ─────────────────────────────────────────────
    if settings.notifications.enabled and pr_data:
        logger.info("Sending notifications...")
        if settings.notifications.slack_webhook:
            slack = SlackNotifier(settings.notifications.slack_webhook)
            slack.notify_pr_created(pr_url, pr_number, approved_deps)

        if settings.notifications.smtp_host and settings.notifications.notify_email:
            email = EmailNotifier(
                smtp_host=settings.notifications.smtp_host,
                smtp_port=settings.notifications.smtp_port,
                smtp_user=settings.notifications.smtp_user,
                smtp_password=settings.notifications.smtp_password,
            )
            email.notify_pr_created(
                settings.notifications.notify_email,
                pr_url,
                pr_number,
                approved_deps,
            )

    # ── Summary ───────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ Dependency Bot Finished Successfully")
    logger.info("=" * 60)
    logger.info(f"  Branch  : {branch_name}")
    logger.info(f"  Updates : {len(approved_deps)}")
    if pr_url:
        logger.info(f"  PR      : {pr_url}")
    logger.info("=" * 60)


def _build_commit_message(deps: List[DependencyInfo]) -> str:
    summary_parts = []
    for dep in deps[:5]:
        summary_parts.append(f"{dep.name} {dep.current_version}→{dep.latest_version}")
    summary = ", ".join(summary_parts)
    if len(deps) > 5:
        summary += f" (+{len(deps)-5} more)"

    return (
        f"chore(deps): auto-update {len(deps)} dependencies\n\n"
        f"Updated: {summary}\n\n"
        f"[skip ci]"
    )


def _notify_no_updates(settings, logger):
    if settings.notifications.enabled and settings.notifications.slack_webhook:
        slack = SlackNotifier(settings.notifications.slack_webhook)
        slack.notify_no_updates()
    logger.info("Done.")


if __name__ == "__main__":
    run()
