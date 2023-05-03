# git.py

import os
import re
import subprocess
from typing import Generator, List, NoReturn, Optional

import structlog

import coinwatch.src.db.crud as crud
from coinwatch.clients.github import GitHubAPI
from coinwatch.settings import CACHE_PATH
from coinwatch.src.common import log_wrapper
from coinwatch.src.db.schema import Project
from coinwatch.src.db.session import db_session

logger = structlog.get_logger(__name__)


class Git:
    """Identifies repository object and adds additional features for working with it.

    Features:
        * GitHub API utilization for extracting additional info about commits/PRs.
    """

    api = GitHubAPI()
    _re_url_contents = re.compile(r"[/:](?P<owner>\w+)/(?P<repo>\w+)\.git")

    base_path = f"{CACHE_PATH}/clones"

    @log_wrapper
    def __init__(self, project: str | Project):
        project = project if isinstance(project, Project) else crud.project.get_by_name(db_session, project)

        self.id = project.id
        self.url = project.url
        self.owner = project.author
        self.repo = project.name
        self.path_to_repo = f"{self.base_path}/{self.repo}"
        self.language = project.language

        if not os.path.exists(self.path_to_repo):
            self.clone()

    @log_wrapper
    def clone(self) -> NoReturn:
        """Create copy of repository in _cache/clones/ in project files."""
        os.makedirs(self.path_to_repo, exist_ok=True)

        command = ["git", "clone", self.url, self.path_to_repo]
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
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE, universal_newlines=True)
        hashes = process.stdout.split()

        for _hash in hashes:
            yield _hash, self.show(_hash, quiet=True)

    def show(self, _hash: str, quiet: Optional[bool] = True, context: int = 0) -> str:
        command = ["git", "show", "--date=iso"]
        command += ["--quiet"] if quiet else []
        command += [f"-U{context}"] if context else []
        command += [_hash]
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
        return process.stdout.decode(errors="replace").splitlines()

    def grep(self, pattern: str, files: str) -> Generator:
        command = ["git", "grep", "-n", f"\\b{pattern}\\b", "--", files]
        logger.info("git: grep: Command: " + " ".join(command), repo=self.repo)
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
        for occurrence in process.stdout.decode(errors="replace").splitlines():
            yield occurrence

    def open_file(self, path: str) -> List[str]:
        with open(f"{self.path_to_repo}/{path}", "r", encoding="UTF-8") as file:
            lines = file.readlines()
        return lines

    def checkout(self, branch: str = "master"):
        command = ["git", "checkout", branch]
        logger.info("git: checkout: Command: " + " ".join(command), repo=self.repo)
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)

        if process.returncode == 0 or branch != "master":
            return
        # else try 'main'

        command = ["git", "checkout", "main"]
        logger.info("git: checkout: Command: " + " ".join(command), repo=self.repo)
        subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)

    def sync(self) -> NoReturn:
        """Sync with remote repository."""
        self.checkout()

        command = ["git", "pull"]
        logger.info("git: sync Command: " + " ".join(command), repo=self.repo)
        subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)

        self.checkout()  # digibyte automatically switches to branch `develop`

    def get_version_from_date(self, date: str) -> NoReturn:
        rev_list = self.rev_list(before=date)
        rev = next(rev_list)[0]
        del rev_list

        command = ["git", "reset", "--hard", rev]
        logger.info("git: get_version_from_date: " + " ".join(command), repo=self.repo)
        subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
