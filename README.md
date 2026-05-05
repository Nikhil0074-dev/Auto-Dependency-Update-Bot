#  Auto Dependency Update Bot
---
A production-ready DevOps automation tool that scans your project dependencies weekly, creates a Pull Request with all updates, and optionally notifies your team via Slack or email.
 
---

##  Features

| Feature | Details |
|---|---|
| **Multi-ecosystem** | Python (`requirements.txt`) + Node.js (`package.json`) |
| **Smart filtering** | Control major / minor / patch, skip lists, pinned versions |
| **Changelog fetching** | Pulls release notes from GitHub API |
| **AI summaries** | Optional OpenAI-powered PR descriptions |
| **GitHub PR** | Auto-creates PRs with risk labels and changelog tables |
| **Notifications** | Slack webhook + SMTP email |
| **Dry-run mode** | Preview updates without modifying anything |
| **GitHub Actions** | Runs every Monday at 9 AM UTC, or on demand |

---

##  Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-org/auto-dependency-bot.git
cd auto-dependency-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
``` 

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your GITHUB_TOKEN and GITHUB_REPO
```

Edit `config.yaml` to set your update rules:

```yaml
update_rules:
  allow_major: false   # Block breaking changes
  allow_minor: true
  allow_patch: true
  skip_packages:
    - some-legacy-lib
```

### 4. Run locally

```bash
python src/main.py
```

Or in dry-run mode (no files changed, no PRs created):

```bash
DRY_RUN=true python src/main.py
# or set dry_run: true in config.yaml
```

---

##  GitHub Actions Setup

### Required Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` |  Auto-provided | Used for PR creation |
| `SLACK_WEBHOOK_URL` | Optional | Slack notifications |
| `SMTP_HOST` | Optional | Email notifications |
| `SMTP_PORT` | Optional | Default: 587 |
| `SMTP_USER` | Optional | SMTP username |
| `SMTP_PASSWORD` | Optional | SMTP password |
| `NOTIFY_EMAIL` | Optional | Recipient email |
| `OPENAI_API_KEY` | Optional | AI changelog summaries |

The workflow runs automatically every **Monday at 9 AM UTC** and can be triggered manually from the Actions tab.

---

##  Architecture

```
Scheduler (GitHub Actions / Cron)
        │
        ▼
PipScanner + NpmScanner          ← Reads requirements.txt / package.json
        │                           Queries PyPI + npm registry APIs
        ▼
VersionComparator                 ← Filters by allow_major/minor/patch rules,
        │                           skip_packages, pin_packages
        ▼
ChangelogFetcher                  ← Fetches GitHub release notes
        │
ChangelogSummarizer               ← AI or rule-based summary
        │
        ▼
BranchManager                    ← git checkout -b deps/auto-update-YYYY-MM-DD
        │
FileUpdater                      ← Writes updated versions to files
        │
CommitManager                    ← git add, commit, push
        │
        ▼
PRCreator                        ← GitHub REST API → creates Pull Request
        │
        ▼
SlackNotifier + EmailNotifier    ← Optional notifications
```

---

##  Project Structure

```
auto-dependency-bot/
├── .github/workflows/
│   └── dependency-update.yml     # GitHub Actions workflow
├── src/
│   ├── main.py                   # Orchestrator entry point
│   ├── config/
│   │   └── settings.py           # Settings loader (YAML + env vars)
│   ├── scanner/
│   │   ├── base_scanner.py       # Abstract base + DependencyInfo model
│   │   ├── pip_scanner.py        # Scans requirements.txt via PyPI API
│   │   └── npm_scanner.py        # Scans package.json via npm registry
│   ├── comparator/
│   │   └── version_comparator.py # Filters deps by update rules
│   ├── changelog/
│   │   ├── fetcher.py            # Fetches release notes from GitHub
│   │   └── summarizer.py         # AI or rule-based summarizer
│   ├── updater/
│   │   ├── file_updater.py       # Writes updated versions to files
│   │   └── version_rules.py      # Version line rewriting helpers
│   ├── git/
│   │   ├── branch_manager.py     # Creates update branches
│   │   ├── commit_manager.py     # Stages, commits, pushes
│   │   └── pr_creator.py         # GitHub PR creation via REST API
│   ├── notifier/
│   │   ├── slack_notifier.py     # Slack webhook notifications
│   │   └── email_notifier.py     # SMTP email notifications
│   └── utils/
│       ├── logger.py             # Structured logging
│       └── helpers.py            # Semver helpers, formatters
├── tests/
│   ├── test_scanner.py
│   ├── test_comparator.py
│   └── test_updater.py
├── config.yaml                   # Project configuration
├── requirements.txt
├── .env.example
└── README.md
```

---

##  Running Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Run a specific test file
pytest tests/test_scanner.py -v
```

---

##  Configuration Reference

### `config.yaml`

```yaml
scan_pip: true          # Scan requirements.txt
scan_npm: true          # Scan package.json
dry_run: false          # Preview-only mode
log_level: INFO         # DEBUG | INFO | WARNING | ERROR

update_rules:
  allow_major: false    # 🔴 Breaking changes
  allow_minor: true     # 🟡 New features
  allow_patch: true     # 🟢 Bug fixes

  skip_packages:        # Never update these
    - legacy-package

  pin_packages:         # Keep these at exact versions
    my-lib: "1.2.3"
```

### Environment Variables

All settings in `config.yaml` can be overridden by environment variables. See `.env.example` for the full list.

---

##  Optional: AI Changelog Summaries

Install the OpenAI package and set your key:

```bash
pip install openai
export OPENAI_API_KEY=sk-...
```

The bot will automatically use GPT-3.5-Turbo to summarize release notes into concise bullet points in the PR description.

---

##  PR Example

The generated PR includes:

- A table of all updated packages with risk level (🔴/🟡/🟢)
- Links to release notes / changelogs
- Collapsible changelog summaries for each package
- Summary stats (total updates, by risk level)
- A reminder to run tests before merging

---

##  Safety

- **Major updates are blocked by default** — opt-in via `allow_major: true`
- **Pinned packages** are never touched
- **Skip lists** let you exclude packages that need manual attention
- All PRs require human review and approval before merging

---
