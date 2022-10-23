# fixing_commits.py

import json
import re
from datetime import timedelta

from clients import Git  # noqa
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
        },
    }

    def __init__(self, cve: CVE, repo: Git):
        self.issue = [ref for ref in cve.references if ref.type_ == ReferenceType.issue]
        self.pull = [ref for ref in cve.references if ref.type_ == ReferenceType.pull]
        self.release_notes = [ref for ref in cve.references if ref.type_ == ReferenceType.release_notes]
        self.cve = cve
        self.repo = repo

    def get_fix_commit(self) -> str:
        if self.issue:
            self.issue = self.issue[0]
            fix_commit = self.issue_scan()
        elif self.pull:
            self.pull = self.pull[0]
            fix_commit = self.pull_scan()
        elif self.release_notes:
            self.release_notes = self.release_notes[0]
            fix_commit = self.release_notes_scan()
        return fix_commit

    def issue_scan(self):
        for pulls in self._is_get_pull_reference():
            for pull in pulls:
                pull_request = self.repo.api.get_pull(self.repo.owner, self.repo.repo, int(pull))
                if pull_request["merged"]:
                    return pull_request["head"]["sha"]

    def pull_scan(self):
        return "Not Implemented"

    def release_notes_scan(self):
        def select_commit(commits):
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

        for match in self._res["release_notes"]["change_log_1"].finditer(self.release_notes.body):
            pull_request = self.repo.api.get_pull(self.repo.owner, self.repo.repo, int(match.group(1)))
            pull_commits = self.repo.api.get_commits_on_pull(self.repo.owner, self.repo.repo, int(match.group(1)))
            if (
                self.cve.id_ in match.group(0)
                or self.cve.id_ in pull_request["body"]
                or self.cve.id_ in pull_request["title"]
            ):
                return select_commit(pull_commits)

            timeline = self.repo.api.get_issue_timeline(self.repo.owner, self.repo.repo, int(match.group(1)))
            if self.cve.id_ in json.dumps(timeline):
                return select_commit(pull_commits)

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


def get_issue_from_references(repo: Git, cve: CVE):
    for reference in cve.references:
        if not (match := re.search(f"{repo.owner}/{repo.repo}/issues/(\\d+)", reference.url)):
            continue
        issue = repo.api.get_issue(repo.owner, repo.repo, int(match.group(1)))


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

    _re_basic_fix_validators = [
        re.compile(r"[Ff]ix|[Bb]ug|[Dd]efect|[Pp]atch"),  # basic
        re.compile(r"issue\s*#\d+\b"),  # issue
        re.compile(cve.id_),  # CVE
        re.compile(r"^\s*\+\s*(.*?//|/?\*).*?" + cve.id_),  # CVE in diff
    ]

    _after = cve.published - timedelta(days=10)
    _after = _after.strftime("%Y-%m-%d")
    _before = cve.published + timedelta(days=2)
    _before = _before.strftime("%Y-%m-%d")
    candidate_commits = {"count": 0, "hashes": []}
    max_weight = 0
    for _hash, commit in repo.logs(after=_after, before=_before, tag_range=get_tag_range(cve)):
        weight = 0
        for i in range(len(_re_basic_fix_validators)):
            if _re_basic_fix_validators[i].search(commit):
                weight += 1 << i

        if not weight or weight < max_weight:
            continue
        max_weight = weight

        candidate_commits["count"] += 1
        candidate_commits["hashes"].append((_hash, commit, weight))

        if candidate_commits["count"] >= CANDIDATES_LIMIT:
            break

    tmp_fix_commit = commit_selector(repo, cve, candidate_commits["hashes"])

    return [candidate[0] for candidate in candidate_commits["hashes"]]
