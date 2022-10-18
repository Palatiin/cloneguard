# fixing_commits.py

import re
from typing import List
from datetime import timedelta

from ..schemas import CVE

from clients import Git  # noqa


CANDIDATES_LIMIT = 10000


def get_tag_range(cve: CVE) -> str:
    fix_tag = ""
    for reference in cve.references:
        if match := re.search(r"github.*?bitcoin.*?v(\d)\.(\d{,2})\.(\d{,2})", reference.url):
            fix_tag = match
            break
        if match := re.search(r"bitcoincore.*?release-(\d)\.(\d{,2})\.(\d{,2})", reference.url):
            fix_tag = match
            break

    if not isinstance(fix_tag, re.Match):
        return ""

    if int(fix_tag.group(3)) > 0:
        prev_tag = f"v{fix_tag.group(1)}.{fix_tag.group(2)}.{int(fix_tag.group(3))-1}"
        fix_tag = f"v{fix_tag.group(1)}.{fix_tag.group(2)}.{int(fix_tag.group(3))}"
        return f"{prev_tag}...{fix_tag}"
    else:
        prev_tag = f"v{fix_tag.group(1)}.{fix_tag.group(2)-1}.0"
        fix_tag = f"v{fix_tag.group(1)}.{fix_tag.group(2)}.{int(fix_tag.group(3))}"
        return f"{prev_tag}...{fix_tag}"


def commit_selector(commits, selected_weight=0):
    for _hash, commit, weight in commits:
        if weight < selected_weight:
            continue
        if not re.search(r"[Mm]erge|[Cc]herry|[Nn]oting", commit):
            return _hash, commit, weight
    return commits[0]


def get_fixing_commits(repo: Git, cve: CVE) -> List[str]:
    _re_basic_fix_validators = [
        re.compile(r"[Ff]ix|[Bb]ug|[Dd]efect|[Pp]atch"),  # basic
        re.compile(r"issue\s*(?!#)\d+\b"),  # issue
        re.compile(cve.id_),  # CVE
        re.compile(r"^\s*\+\s*(.*?//|/?\*).*?" + cve.id_)  # CVE in diff
    ]

    _before = cve.published + timedelta(days=2)
    _before = _before.strftime("%Y-%m-%d")
    candidate_commits = {"count": 0, "hashes": []}
    max_weight = 0
    for _hash, commit in repo.logs(before=_before, tag_range=get_tag_range(cve)):
        weight = 0
        for i in range(len(_re_basic_fix_validators)):
            if _re_basic_fix_validators[i].search(commit):
                weight += (1 << i)

        if not weight or weight < max_weight:
            continue
        max_weight = weight

        candidate_commits["count"] += 1
        candidate_commits["hashes"].append((_hash, commit, weight))

        if candidate_commits["count"] >= CANDIDATES_LIMIT:
            break

    tmp_fix_commit = commit_selector(candidate_commits["hashes"])

    return [candidate[0] for candidate in candidate_commits["hashes"]]
