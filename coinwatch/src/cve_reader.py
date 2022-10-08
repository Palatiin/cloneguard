# cve_reader.py

import requests
from typing import List, Dict

from bs4 import BeautifulSoup

from .schemas import *
from utils import logger  # noqa
from settings import USER_AGENT  # noqa


__all__ = ["load_references", "read_cve"]


def load_references(references: List[Reference]) -> Dict[str, str]:
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


def read_cve(cve: CVE):
    references: Dict[str, str] = load_references(cve.references)
