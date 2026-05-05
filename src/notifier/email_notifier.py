"""
Email notification service for dependency updates.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional
from src.scanner.base_scanner import DependencyInfo
from src.utils import get_logger


logger = get_logger(__name__)


class EmailNotifier:
    """Sends email notifications when dependency PRs are created."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password

    def notify_pr_created(
        self,
        to_email: str,
        pr_url: str,
        pr_number: int,
        dependencies: List[DependencyInfo],
    ) -> bool:
        """Send an email about the newly created PR."""
        subject = f"[Dependency Bot] PR #{pr_number}: {len(dependencies)} packages updated"
        body_html = self._build_html(pr_url, pr_number, dependencies)
        body_text = self._build_text(pr_url, pr_number, dependencies)
        return self._send(to_email, subject, body_html, body_text)

    def _build_html(
        self,
        pr_url: str,
        pr_number: int,
        deps: List[DependencyInfo],
    ) -> str:
        rows = ""
        for dep in deps:
            color = {"major": "#FF4444", "minor": "#FFAA00", "patch": "#22CC44"}.get(
                dep.update_type, "#888888"
            )
            rows += (
                f"<tr>"
                f"<td style='padding:6px 12px'><code>{dep.name}</code></td>"
                f"<td style='padding:6px 12px'>{dep.current_version}</td>"
                f"<td style='padding:6px 12px'>{dep.latest_version}</td>"
                f"<td style='padding:6px 12px;color:{color};font-weight:bold'>{dep.update_type.upper()}</td>"
                f"<td style='padding:6px 12px'>{dep.ecosystem}</td>"
                f"</tr>\n"
            )

        return f"""
<html>
<body style="font-family:Arial,sans-serif;color:#333">
  <h2>🤖 Automated Dependency Updates</h2>
  <p>A new Pull Request has been created with <strong>{len(deps)}</strong> dependency updates.</p>
  <p><a href="{pr_url}" style="background:#0366d6;color:white;padding:10px 20px;text-decoration:none;border-radius:4px">
    View PR #{pr_number} on GitHub
  </a></p>
  <h3>Updated Packages</h3>
  <table border="1" cellspacing="0" cellpadding="0" style="border-collapse:collapse;width:100%">
    <thead style="background:#f6f8fa">
      <tr>
        <th style="padding:8px 12px;text-align:left">Package</th>
        <th style="padding:8px 12px;text-align:left">From</th>
        <th style="padding:8px 12px;text-align:left">To</th>
        <th style="padding:8px 12px;text-align:left">Risk</th>
        <th style="padding:8px 12px;text-align:left">Ecosystem</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="color:#888;font-size:12px;margin-top:24px">
    Sent by Auto Dependency Bot via GitHub Actions
  </p>
</body>
</html>
"""

    def _build_text(self, pr_url: str, pr_number: int, deps: List[DependencyInfo]) -> str:
        lines = [
            f"Auto Dependency Updates — PR #{pr_number}",
            f"PR URL: {pr_url}",
            "",
            f"Updated {len(deps)} packages:",
        ]
        for dep in deps:
            lines.append(
                f"  {dep.name}: {dep.current_version} -> {dep.latest_version} [{dep.update_type.upper()}]"
            )
        return "\n".join(lines)

    def _send(self, to_email: str, subject: str, html: str, text: str) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.smtp_user or "dependency-bot@noreply.local"
        msg["To"] = to_email

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(msg["From"], to_email, msg.as_string())
            logger.info(f"Email notification sent to {to_email}")
            return True
        except smtplib.SMTPException as e:
            logger.error(f"Failed to send email: {e}")
            return False
