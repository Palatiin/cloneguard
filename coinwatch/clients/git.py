# git.py

import re
import subprocess
from typing import Generator, NoReturn, Optional

from coinwatch.clients import GitHubAPI
from coinwatch.settings import logger


class Git:
    """Identifies repository object and adds additional features for working with it.

    Features:
        * GitHub API utilization for extracting additional info about commits/PRs.
    """

    api = GitHubAPI()
    _re_url_contents = re.compile(r"[/:](?P<owner>\w+)/(?P<repo>\w+)\.git")

    base_path = "_cache/clones"

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

    def clone(self) -> NoReturn:
        """Create copy of repository in _cache/clones/ in project files."""
        process = subprocess.run(["git", "clone", self.url, self.path_to_repo], stdout=subprocess.PIPE)
        if process.returncode != 0:
            logger.error("clients: git: clone: Couldn't clone the repository.")

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

        logger.info("git: rev_list: Command: " + " ".join(command))
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
        hashes = process.stdout.decode("ascii").split()

        for _hash in hashes:
            commit = self.show(_hash, quiet=True)
            yield _hash, commit

    def show(self, _hash: str, quiet: Optional[bool] = True) -> str:
        command = ["git", "show", "--quiet" if quiet else "", "--date=iso", _hash]
        logger.info("git: show: Command: " + " ".join(command))
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
        commit = process.stdout.decode(errors="replace")

        return commit
