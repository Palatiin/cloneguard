# notifications.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import structlog

import coinwatch.settings as auth
from coinwatch.clients.git import Git

logger = structlog.get_logger(__name__)


class Postman(object):
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587

    def notify_bug_detection(self, commits: List[str], repo: Git):
        message = MIMEMultipart()
        message["From"] = auth.SMTP_LOGIN
        message["To"] = "xremen01@stud.fit.vutbr.cz"
        message["Subject"] = f"CG: New bug-fix detected in {repo.repo}!"

        commit_bodies = "\n".join([repo.show(_hash, quiet=True) for _hash in commits])
        message.attach(
            MIMEText(
                "Hi!\n"
                f"I've detected new bug-fix(es) in {repo.repo} - commit(s): {commits}.\n"
                "Should I start scanning clones?\n\n"
                f"{commit_bodies}"
                "\n\nYour Postman.",
                "plain",
            )
        )

        self._notify(message)

    def _notify(self, message):
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(auth.SMTP_LOGIN, auth.SMTP_PASSWORD)
                server.sendmail(message["From"], message["To"], message.as_string())
            logger.info("notifications: notify: Notification sent.")
        except Exception as e:
            logger.warning(f"notifications: notify: {str(e)}")
