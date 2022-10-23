# fixing_commits.py

import json
import re
from datetime import timedelta
from typing import List, Tuple

from clients import Git  # noqa
from keybert import KeyBERT
from settings import logger  # noqa

from ..schemas import *

CANDIDATES_LIMIT = 10000


class FixCommitFinder:
    work_flow = [
        "issue_scan",
        "pull_scan",
        "release_notes_scan",
        "default",
    ]

    _res = {
        "release_notes": {
            "change_log_1": re.compile(r"#(\d+)\s*`(\w+)`\s*(.*)"),
        },
        "default": {
            "keyword": re.compile(r"[Ff]ix|[Bb]ug"),
            "issue": re.compile(r"issue\s*#(\d+)\b"),
        },
    }

    _keyword_count = 10
    _keyphrase_ngram_range = (1, 3)

    def __init__(self, cve: CVE, repo: Git):
        self.issue = [ref for ref in cve.references if ref.type_ == ReferenceType.issue]
        self.pull = [ref for ref in cve.references if ref.type_ == ReferenceType.pull]
        self.release_notes = [ref for ref in cve.references if ref.type_ == ReferenceType.release_notes]
        self.cve = cve
        self.repo = repo
        self.kw_model = KeyBERT(model="all-mpnet-base-v2")
        self.cve_keywords: List[Tuple[str, float]] = self.kw_model.extract_keywords(
            cve.descriptions["en"],
            keyphrase_ngram_range=self._keyphrase_ngram_range,
            highlight=False,
            top_n=self._keyword_count,
        )
        self.cve_keywords = list(filter(lambda x: "bitcoin" not in x[0], self.cve_keywords))

    def get_fix_commit(self) -> str:
        fix_commit = None
        if self.issue:
            self.issue = self.issue[0]
            fix_commit = self.issue_scan()
        elif self.pull:
            self.pull = self.pull[0]
            fix_commit = self.pull_scan()
        elif self.release_notes:
            self.release_notes = self.release_notes[0]
            fix_commit = self.release_notes_scan()
        if not fix_commit:
            fix_commit = self.default_scan()
        return fix_commit

    def issue_scan(self):
        for pulls in self._is_get_pull_reference():
            for pull in pulls:
                pull_request = self.repo.api.get_pull(self.repo.owner, self.repo.repo, int(pull))
                if pull_request["merged"]:
                    pull_commits = self.repo.api.get_commits_on_pull(self.repo.owner, self.repo.repo, int(pull))
                    return self._select_commit(pull_commits)

    def pull_scan(self):
        pull_request = self.pull.json
        if pull_request["merged"]:
            pull_commits = self.repo.api.get_commits_on_pull(self.repo.owner, self.repo.repo, pull_request["number"])
            return self._select_commit(pull_commits)
        # TODO: if not merged

    def release_notes_scan(self):
        change_log = []

        for match in self._res["release_notes"]["change_log_1"].finditer(self.release_notes.body):
            pull_request = self.repo.api.get_pull(self.repo.owner, self.repo.repo, int(match.group(1)))
            pull_commits = self.repo.api.get_commits_on_pull(self.repo.owner, self.repo.repo, int(match.group(1)))
            if (
                self.cve.id_ in match.group(0)
                or self.cve.id_ in pull_request["body"]
                or self.cve.id_ in pull_request["title"]
            ):
                return self._select_commit(pull_commits)

            timeline = self.repo.api.get_issue_timeline(self.repo.owner, self.repo.repo, int(match.group(1)))
            if self.cve.id_ in json.dumps(timeline):
                return self._select_commit(pull_commits)

            _change_log = list(match.groups())
            search_text = f"{_change_log[2]} {pull_request['title']} {pull_request['body']} "
            search_text += " ".join(commit["commit"]["message"] for commit in pull_commits)
            _change_log.extend([self._rn_change_log_eval(search_text), pull_commits])
            change_log.append(_change_log)

        change_log = sorted(change_log, key=lambda x: x[3], reverse=True)
        return self._select_commit(change_log[0][4])

    def default_scan(self):
        _after = self.cve.published - timedelta(days=10)
        _after = _after.strftime("%Y-%m-%d")
        _before = self.cve.published + timedelta(days=2)
        _before = _before.strftime("%Y-%m-%d")
        candidate_commits = {"count": 0, "commits": []}

        for _hash, commit in self.repo.logs(after=_after, before=_before, tag_range=get_tag_range(self.cve)):
            if self.cve.id_ in commit:
                return _hash
            weight = 0.0
            if self._res["default"]["keyword"].search(commit):
                weight += 0.1
            weight += self._rn_change_log_eval(commit)
            if weight:
                candidate_commits["count"] += 1
                candidate_commits["commits"].append((_hash, weight, commit))

        commits = sorted(candidate_commits["commits"], key=lambda x: x[1], reverse=True)
        return commits[0][0]

    def _is_get_pull_reference(self):
        issue_timeline = self.repo.api.get_issue_timeline(self.repo.owner, self.repo.repo, self.issue.json["number"])
        start_index = len(issue_timeline)

        if self.issue.json["state"] == "closed":
            for event in issue_timeline[::-1]:
                start_index -= 1
                if event["event"] == "closed":
                    break

        issue_timeline = issue_timeline[:start_index]
        for event in issue_timeline[::-1]:
            if event["event"] == "commented":
                if match := re.findall(r"#(\d+)", event["body"]):
                    yield match

    def _rn_change_log_eval(self, text):
        value = 0
        for keyword, weight in self.cve_keywords:
            if keyword in text:
                value += weight
        return value

    def _select_commit(self, commits, kw_check: bool = False):
        if not commits:
            return
        commits = commits[::-1]
        candidate = None
        for commit in commits:
            if "[qa]" in commit["commit"]["message"]:  # CVE-2018-17144
                continue

            if not candidate:
                candidate = commit["sha"]

            if self._res["default"]["keyword"].search(commit["commit"]["message"]):
                return commit["sha"]

        return candidate or commits[0]["sha"]


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


def commit_selector(repo: Git, cve: CVE, commits, selected_weight=0):
    candidates = []
    for _hash, commit, weight in commits:
        if weight < selected_weight:
            continue
        if not re.search(r"[Mm]erge|[Cc]herry|[Nn]oting", commit):
            if match := re.findall(r"CVE-\d+-\d+", commit):
                if cve.id_ not in match:
                    continue
            candidates.append((_hash, commit, weight))
        elif match := re.search(r"[Mm]erge\s*(?:\w+/\w+|pull request)\s*#(\d+)", commit):
            pull_request = repo.api.get_pull(repo.owner, repo.repo, int(match.group(1)))
            if cve.id_ in json.dumps(pull_request):
                logger.info("selector: fixing_commits: commit_selector: Found CVE in pull request data.")
                return _hash, commit, weight
            if match := re.search(r"issue\s*#(\d+)", pull_request["body"]):
                issue = repo.api.get_issue(repo.owner, repo.repo, int(match.group(1)))

    return commits[0]


def get_fixing_commits(repo: Git, cve: CVE) -> str:
    finder = FixCommitFinder(cve, repo)
    return finder.get_fix_commit()
