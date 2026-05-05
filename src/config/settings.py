"""
Configuration settings for the Auto-Dependency Update Bot.
Loads from environment variables and config.yaml.
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GitConfig:
    token: str = ""
    repo: str = ""
    base_branch: str = "main"
    bot_name: str = "Dependency Bot"
    bot_email: str = "dependency-bot@github-actions.com"


@dataclass
class UpdateRules:
    allow_major: bool = False
    allow_minor: bool = True
    allow_patch: bool = True
    skip_packages: List[str] = field(default_factory=list)
    pin_packages: dict = field(default_factory=dict)


@dataclass
class NotificationConfig:
    slack_webhook: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    notify_email: Optional[str] = None
    enabled: bool = False


@dataclass
class AIConfig:
    openai_api_key: Optional[str] = None
    enabled: bool = False
    model: str = "gpt-3.5-turbo"


@dataclass
class Settings:
    git: GitConfig = field(default_factory=GitConfig)
    update_rules: UpdateRules = field(default_factory=UpdateRules)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    scan_pip: bool = True
    scan_npm: bool = True
    dry_run: bool = False
    log_level: str = "INFO"


def load_settings() -> Settings:
    """Load settings from config.yaml and environment variables."""
    settings = Settings()
    config_path = Path("config.yaml")

    # Load from YAML if it exists
    if config_path.exists():
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}

        rules = config_data.get("update_rules", {})
        settings.update_rules = UpdateRules(
            allow_major=rules.get("allow_major", False),
            allow_minor=rules.get("allow_minor", True),
            allow_patch=rules.get("allow_patch", True),
            skip_packages=rules.get("skip_packages", []),
            pin_packages=rules.get("pin_packages", {}),
        )

        settings.scan_pip = config_data.get("scan_pip", True)
        settings.scan_npm = config_data.get("scan_npm", True)
        settings.dry_run = config_data.get("dry_run", False)
        settings.log_level = config_data.get("log_level", "INFO")

    # Override with environment variables
    settings.git = GitConfig(
        token=os.environ.get("GITHUB_TOKEN", ""),
        repo=os.environ.get("GITHUB_REPO", ""),
        base_branch=os.environ.get("BASE_BRANCH", "main"),
        bot_name=os.environ.get("BOT_NAME", "Dependency Bot"),
        bot_email=os.environ.get("BOT_EMAIL", "dependency-bot@github-actions.com"),
    )

    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
    smtp_host = os.environ.get("SMTP_HOST")
    settings.notifications = NotificationConfig(
        slack_webhook=slack_webhook,
        smtp_host=smtp_host,
        smtp_port=int(os.environ.get("SMTP_PORT", 587)),
        smtp_user=os.environ.get("SMTP_USER"),
        smtp_password=os.environ.get("SMTP_PASSWORD"),
        notify_email=os.environ.get("NOTIFY_EMAIL"),
        enabled=bool(slack_webhook or smtp_host),
    )

    openai_key = os.environ.get("OPENAI_API_KEY")
    settings.ai = AIConfig(
        openai_api_key=openai_key,
        enabled=bool(openai_key),
        model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
    )

    return settings
