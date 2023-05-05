# File: src/fixing_commits.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2022-11-15
# Description: Implementation of component FixCommitFinder.

import datetime as dt
import json
import re
from typing import List, Optional, Set

import nltk
import structlog

import cloneguard.src.db.crud as crud
from cloneguard.clients.cve import CVEClient
from cloneguard.clients.git import Git
from cloneguard.src.common import log_wrapper
from cloneguard.src.cve_reader import load_references
from cloneguard.src.db.schema import Bug
from cloneguard.src.db.session import db_session
from cloneguard.src.schemas import CVE, ReferenceType

# CANDIDATES_LIMIT = 100

nltk.download("punkt", quiet=True)
nltk.download("averaged_perceptron_tagger", quiet=True)


class FixCommitFinder:
    work_flow = [
        "issue_scan",
        "pull_scan",
        "release_notes_scan",
        "default",
    ]

    IGNORED_COMMITS = ["test", "ci", "doc"]

    _res = {
        "release_notes": {
            "change_log_1": re.compile(r"#(\d+)\s*`(\w+)`\s*(.*)"),
        },
        "default": {
            "keyword": re.compile(r"fix|\bbug|CVE-\d+|CWE-\d+", flags=re.IGNORECASE),
            "issue": re.compile(r"issue\s*#(\d+)\b"),
        },
        "merge_commit": re.compile(r"(?:Merge\s*.*?#\d+:)?\s*([\w-]+):"),
        "commit": re.compile(r"(\w{40}) +(.+)"),
        "commit_message": re.compile(r"([\w-]+): .+"),
        "cwe": re.compile(r"DOS|overflow|underflow|race|deadlock|infinite|leak|insecure|bypass"),
    }

    _keyword_count = 10
    _whitelisted_word_tags = ["NN", "VB", "JJ"]

    def __init__(self, repo: Git, cve: Optional[str] = None, cache: bool = False):
        """Initialize commit finder.

        Args:
            repo (Git): scanned repository
            cve (str): searched CVE identifier
            cache (bool): use cached data in DB
        """
        self.logger = structlog.get_logger(__name__)

        if not cve:
            self.repo = repo
            return
        self.stored_cve = self.check_db(cve)
        if cache and self.stored_cve:
            return
        if not cve.startswith("CVE-"):
            return

        self.cve: CVE = CVEClient().cve_id(cve)
        load_references(repo, self.cve.references)
        self.commit, self.issue, self.pull, self.release_notes = [], [], [], []
        self._categorize_references()
        self.repo = repo
        self.cve_keywords: Set[str] = self._extract_keywords(self.cve.descriptions["en"][0])

    def _categorize_references(self):
        for ref in self.cve.references:
            match ref.type_:
                case ReferenceType.commit:
                    self.commit.append(ref)
                case ReferenceType.issue:
                    self.issue.append(ref)
                case ReferenceType.pull:
                    self.pull.append(ref)
                case ReferenceType.release_notes:
                    self.release_notes.append(ref)

    def _extract_keywords(self, text: str, lang: str = "english") -> Set[str]:
        kwords = nltk.word_tokenize(text, language=lang)
        kwords = nltk.pos_tag(kwords)
        kwords = [x for x in kwords if x[1][:2] in self._whitelisted_word_tags and "bitcoin" not in x[0].lower()]
        return set([kw[0] for kw in kwords])

    def get_bug(self) -> Bug | None:
        fix_commits = self.get_fix_commit()
        if not fix_commits:
            return None

        if not self.stored_cve:
            bug = Bug(cve_id=self.cve.id_ if self.cve else "SCAN", project=self.repo.id)
            bug.commits = fix_commits
            self.stored_cve = crud.bug.create(db_session, bug)
        elif not self.stored_cve.commits:
            self.stored_cve.commits = fix_commits
            crud.bug.update(db_session, self.stored_cve)

        return self.stored_cve

    def scan_recent(self):
        def ignore_commit(_commit):
            if match := self._res["commit_message"].match(_commit.strip()):
                if match.group(1) in self.IGNORED_COMMITS:
                    return True
            return False

        time_window = dt.datetime.now() - dt.timedelta(days=3)  # TODO: just tmp 3 days
        recent_commits = self.repo.rev_list(after=time_window.strftime("%Y-%m-%d"))

        candidates = []
        for _hash, commit in recent_commits:
            commit_parts = commit.split("\n\n")

            if (keyword_1 := self._res["default"]["keyword"].search(commit)) or (
                keyword_2 := self._res["cwe"].search(commit)
            ):
                keyword = (keyword_1 or keyword_2).group(0)
                self.logger.info(f"scan_recent: Matched {keyword=}.")
                if commit_parts[1].strip().startswith("Merge"):
                    for line in self._res["commit"].finditer(commit):
                        if not ignore_commit(line.group(2)):
                            candidates.append(line.group(1))
                elif self._res["commit_message"].match(commit_parts[1]):
                    if not ignore_commit(commit_parts[1]):
                        candidates.append(_hash)
                else:
                    candidates.append(_hash)

        return candidates

    @log_wrapper
    def get_fix_commit(self) -> List[str]:
        if self.stored_cve:
            if self.stored_cve.commits:
                return self.stored_cve.commits
        if not self.cve:
            return self.scan_recent()

        fix_commits = []

        if self.commit:
            return [self.commit[0].json["id"]]

        # ISSUE SCAN
        if self.issue:
            self.issue = self.issue[0]
            if fix_commit := self.issue_scan():
                return [fix_commit]

        # PULL SCAN
        if self.pull:
            self.pull = self.pull[0]
            if fix_commit := self.pull_scan():
                return fix_commit if isinstance(fix_commit, list) else [fix_commit]

        # RELEASE NOTES SCAN
        if self.release_notes:
            self.release_notes = self.release_notes[0]
            if fix_commits := self.release_notes_scan():
                return fix_commits if isinstance(fix_commits, list) else [fix_commits]

        # DEFAULT SCAN
        fix_commits.extend(self.default_scan())

        return fix_commits

    def issue_scan(self) -> str:
        for pulls in self._is_get_pull_reference():
            for pull in pulls:
                pull_request = self.repo.api.get_pull(self.repo.owner, self.repo.repo, int(pull))
                if not pull_request["merged"]:
                    continue
                pull_commits = self.repo.api.get_commits_on_pull(self.repo.owner, self.repo.repo, int(pull))
                return self._select_commit(pull_commits)

    def pull_scan(self) -> str:
        pull_request = self.pull.json
        if pull_request["merged"]:
            pull_commits = self.repo.api.get_commits_on_pull(self.repo.owner, self.repo.repo, pull_request["number"])
            return self._select_commit(pull_commits)
        # TODO: if not merged

    def release_notes_scan(self) -> List[str] | str:
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
                return self._select_commit(pull_commits)  # return all commits?

            change_log_item = list(match.groups())
            search_text = f"{change_log_item[2]} {pull_request['title']} {pull_request['body']} "
            search_text += " ".join(commit["commit"]["message"] for commit in pull_commits)
            # add information value to each commit
            change_log_item.extend([self._rn_change_log_eval(search_text), pull_commits])
            # append commits from PR in change log
            change_log.append(change_log_item)

        # sort by information value
        change_log = sorted(change_log, key=lambda x: x[3], reverse=True)
        # _change_log = list(filter(lambda x: x[3] > 0, change_log))
        # change_log = _change_log or change_log

        commits = [commit["sha"] for log in change_log for commit in log[4]]

        return commits  # self._select_commit(change_log[0][4])

    def default_scan(self) -> List[str]:
        _after = f"{self.cve.published - dt.timedelta(days=10):%Y-%m-%d}"
        _before = f"{self.cve.published + dt.timedelta(days=2):%Y-%m-%d}"
        candidate_commits = {"count": 0, "commits": []}

        for _hash, commit in self.repo.rev_list(after=_after, before=_before, tag_range=get_tag_range(self.cve)):
            if self.cve.id_ in commit:
                return _hash
            weight = 0.0
            if self._res["default"]["keyword"].search(commit):
                weight += 0.1
            weight += self._rn_change_log_eval(commit)
            if not weight:
                continue

            candidate_commits["count"] += 1
            candidate_commits["commits"].append((_hash, weight, commit))

        commits = sorted(candidate_commits["commits"], key=lambda x: x[1], reverse=True)
        # TODO: if 'Merge' in commit, pull scan?
        return [commit[0] for commit in commits]

    @staticmethod
    def check_db(cve: str):
        if cve := crud.bug.get_cve(db_session, cve):
            return cve
        return None

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
        for keyword in self.cve_keywords:
            if keyword in text:
                value += 1
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
