# cve_reader.py

import re
import requests
from typing import List, Dict, NoReturn

from bs4 import BeautifulSoup

from .schemas import *

from clients import Git  # noqa
from settings import logger, USER_AGENT  # noqa


__all__ = ["load_references", "read_cve"]

_re_issue = re.compile(r"https?://(?:www\.)?github\.com/bitcoin/bitcoin/issues/(\d+)")
_re_pull = re.compile(r"https?://(?:www\.)?github\.com/bitcoin/bitcoin/pull/(\d+)")
_re_release_notes = re.compile(r"https?://(?:www\.)?github\.com/bitcoin/bitcoin/blob/(.*?)/doc/release-notes\.md")


def _load_references(references: List[Reference]) -> Dict[str, str]:
    refs: Dict[str, str] = {}

    logger.info("cve_reader: Loading references...")
    _headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US;en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": USER_AGENT,
    }
    for ref in references:
        res = requests.get(ref.url, headers=_headers)
        try:
            refs[ref.url] = BeautifulSoup(res.text, "html.parser").text
        except Exception:
            refs[ref.url] = res.text

    logger.info("cve_reader: Loading references done.")
    return refs


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
            reference.body = requests.get(reference.url, headers=_headers)
            reference.json = {"version": match.group(1)}
            reference.type_ = ReferenceType.release_notes
        else:
            logger.info(f"cve_reader: load_references: Unknown reference ({reference.url}).")
