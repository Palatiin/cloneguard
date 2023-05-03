# File: src/cve_reader.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2022-08-08
# Description: CVE references reader implementation.

import base64
import re
from typing import NoReturn

import structlog

from cloneguard.clients.git import Git
from cloneguard.settings import USER_AGENT
from cloneguard.src.common import log_wrapper
from cloneguard.src.schemas import *

__all__ = ["load_references"]

_re_issue = r"https?://(?:www\.)?github\.com/{author}/{project}/issues/(\d+)"
_re_pull = r"https?://(?:www\.)?github\.com/{author}/{project}/pull/(\d+)"
_re_commit = r"https?://(?:www\.)?github\.com/{author}/{project}/commit/(\w+)"
_re_release_notes = r"https?://(?:www\.)?github\.com/{author}/{project}/blob/(.*?)/doc/release-notes\.md"


logger = structlog.get_logger(__name__)


@log_wrapper
def load_references(repo: Git, references: List[Reference]) -> NoReturn:
    _headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US;en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": USER_AGENT,
    }

    for reference in references:
        if match := re.match(_re_issue.format(author=repo.owner, project=repo.repo), reference.url):
            logger.info("cve_reader: load_references: Reference to issue matched.")
            reference.json = repo.api.get_issue(repo.owner, repo.repo, int(match.group(1)))
            reference.type_ = ReferenceType.issue
        elif match := re.match(_re_pull.format(author=repo.owner, project=repo.repo), reference.url):
            logger.info("cve_reader: load_references: Reference to pull request matched.")
            reference.json = repo.api.get_pull(repo.owner, repo.repo, int(match.group(1)))
            reference.type_ = ReferenceType.pull
        elif match := re.match(_re_release_notes.format(author=repo.owner, project=repo.repo), reference.url):
            logger.info("cve_reader: load_references: Reference to release notes matched.")
            version = match.group(1)
            reference.body = repo.api.get_file(
                repo.owner, repo.repo, f"doc/release-notes/release-notes-{version.strip('v')}.md"
            )["content"]
            reference.body = str(base64.b64decode(reference.body), "utf-8")
            reference.json = {"version": version}
            reference.type_ = ReferenceType.release_notes
        elif match := re.match(_re_commit.format(author=repo.owner, project=repo.repo), reference.url):
            logger.info("cve_reader: load_references: Reference to commit matched.")
            reference.json = {"id": match.group(1)}
            reference.type_ = ReferenceType.commit
        else:
            logger.info(f"cve_reader: load_references: Unknown reference ({reference.url}).")
