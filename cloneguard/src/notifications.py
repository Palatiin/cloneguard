# File: src/notifications.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-03-26
# Description: Implementation of the Postman class - email notifications.

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import structlog

import cloneguard.settings as auth
from cloneguard.settings import NOTIFY_LIST
from cloneguard.clients.git import Git


class Postman(object):
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587

    def __init__(self):
        self.logger = structlog.get_logger(__name__)

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
                for recipient in NOTIFY_LIST:
                    message["To"] = recipient
                    server.sendmail(message["From"], message["To"], message.as_string())
            self.logger.info("notifications: notify: Notification sent.")
        except Exception as e:
            self.logger.warning(f"notifications: notify: {str(e)}")
