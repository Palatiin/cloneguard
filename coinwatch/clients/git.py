# git.py

import re
import subprocess
from typing import Generator, List, NoReturn, Optional

import structlog

from coinwatch.clients import GitHubAPI
from coinwatch.src.common import log_wrapper

logger = structlog.get_logger(__name__)


class Git:
    """Identifies repository object and adds additional features for working with it.

    Features:
        * GitHub API utilization for extracting additional info about commits/PRs.
    """

    api = GitHubAPI()
    _re_url_contents = re.compile(r"[/:](?P<owner>\w+)/(?P<repo>\w+)\.git")

    base_path = "_cache/clones"

    @log_wrapper
    def __init__(self, url: str):
        """Initialize git repository object."""
        url_contents = self._re_url_contents.search(url)
        if not url_contents:
            logger.error("clients: git: Couldn't extract repo name from url.")
            return
        self.url = url
        self.owner = url_contents.group("owner")
        self.repo = url_contents.group("repo")
        self.path_to_repo = f"{self.base_path}/{self.repo}"

    @log_wrapper
    def clone(self) -> NoReturn:
        """Create copy of repository in _cache/clones/ in project files."""
        command = ["git", "clone", self.url, self.base_path]
        logger.info("git: clone: Command: " + " ".join(command), repo=self.repo)
        process = subprocess.run(command, stdout=subprocess.PIPE)
        if process.returncode != 0:
            logger.error("clients: git: clone: Couldn't clone the repository.", repo=self.repo)

    def rev_list(
        self,
        after: Optional[str] = None,
        before: Optional[str] = None,
        tag_range: Optional[str] = None,
        commit_id: Optional[str] = None,
        file: Optional[str] = None,
    ) -> Generator:
        """Get list of logs/commits in repository in reverse chronological order.

        Synopsis (man git-rev-list):
            git rev-list [<options>] <commit>... [[--] <path>...]

        Args:
            after (Optional[str]): List only commits after this date.
            before (Optional[str]): List only commits before this date.
            tag_range (Optional[str]): List only commits within this tag range.
            commit_id (Optional[str]): List only commits before this commit.
            file (Optional[str]): List only commits affecting this file.

        Returns:
            Generator of commits before selected date/commit_id.
        """
        command = ["git", "rev-list"]
        command += ["--after", after] if after else []
        command += ["--before", before] if before else []
        command += [tag_range] if tag_range else []
        command += [commit_id or "origin"]
        command += ["--", file] if file else []

        logger.info("git: rev_list: Command: " + " ".join(command), repo=self.repo)
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
        hashes = process.stdout.decode("ascii").split()

        for _hash in hashes:
            commit = self.show(_hash, quiet=True)
            yield _hash, commit

    def show(self, _hash: str, quiet: Optional[bool] = True) -> str:
        command = ["git", "show", "--quiet" if quiet else "", "--date=iso", _hash]
        logger.info("git: show: Command: " + " ".join(command), repo=self.repo)
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
        return process.stdout.decode(errors="replace")

    def diff(self, *commits: str, context_lines: int = 0, path: Optional[str] = None) -> str:
        command = ["git", "diff", f"-U{context_lines}", "--raw", *commits]
        command += ["--", path] if path else []
        logger.info("git: diff: Command: " + " ".join(command), repo=self.repo)
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
        return process.stdout.decode(errors="replace")

    def annotate(self, commit: str, path: str) -> List[str]:
        command = ["git", "annotate", commit, "--", path]
        logger.info("git: annotate: Command: " + " ".join(command), repo=self.repo)
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
        return process.stdout.decode(errors="replace").split("\n")

    def grep(self, pattern) -> List[str]:
        command = ["git", "grep", "-n", pattern]
        logger.info("git: grep: Command: " + " ".join(command), repo=self.repo)
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
        return process.stdout.decode(errors="replace").split("\n")

    def open_file(self, path: str) -> List[str]:
        with open(f"{self.path_to_repo}/{path}", "r", encoding="UTF-8") as file:
            lines = file.readlines()
        return lines

    def sync(self) -> NoReturn:
        """Sync with remote repository."""
        command = ["git", "checkout", "master"]
        logger.info("git: sync: Command: " + " ".join(command), repo=self.repo)
        subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)

        command = ["git", "pull"]
        logger.info("git: sync Command: " + " ".join(command), repo=self.repo)
        subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)

    def get_version_from_date(self, date: str) -> NoReturn:
        rev_list = self.rev_list(before=date)
        rev = next(rev_list)
        del rev_list

        command = ["git", "reset", "--hard", rev]
        logger.info("git: get_version_from_date: " + " ".join(command), repo=self.repo)
        subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
