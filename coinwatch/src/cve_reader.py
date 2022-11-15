# cve_reader.py

import base64
import re
from typing import List, NoReturn

from coinwatch.clients import Git
from coinwatch.settings import USER_AGENT, logger
from coinwatch.src.schemas import *

__all__ = ["load_references"]

_re_issue = re.compile(r"https?://(?:www\.)?github\.com/bitcoin/bitcoin/issues/(\d+)")
_re_pull = re.compile(r"https?://(?:www\.)?github\.com/bitcoin/bitcoin/pull/(\d+)")
_re_release_notes = re.compile(r"https?://(?:www\.)?github\.com/bitcoin/bitcoin/blob/(.*?)/doc/release-notes\.md")


def load_references(repo: Git, references: List[Reference]) -> NoReturn:
    _headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US;en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": USER_AGENT,
    }

    for reference in references:
        if match := _re_issue.match(reference.url):
            logger.info("cve_reader: load_refernces: Reference to issue matched.")
            reference.json = repo.api.get_issue(repo.owner, repo.repo, int(match.group(1)))
            reference.type_ = ReferenceType.issue
        elif match := _re_pull.match(reference.url):
            logger.info("cve_reader: load_refernces: Reference to pull request matched.")
            reference.json = repo.api.get_pull(repo.owner, repo.repo, int(match.group(1)))
            reference.type_ = ReferenceType.pull
        elif match := _re_release_notes.match(reference.url):
            logger.info("cve_reader: load_references: Reference to release notes matched.")
            version = match.group(1)
            reference.body = repo.api.get_file(
                repo.owner, repo.repo, f"doc/release-notes/release-notes-{version.strip('v')}.md"
            )["content"]
            reference.body = str(base64.b64decode(reference.body), "utf-8")
            reference.json = {"version": version}
            reference.type_ = ReferenceType.release_notes
        else:
            logger.info(f"cve_reader: load_references: Unknown reference ({reference.url}).")
