# git.py

import re
import subprocess
from typing import Optional, NoReturn, Generator

from coinwatch.clients import GitHubAPI
from settings import logger  # noqa


class Git:
    """Identifies repository object and adds additional features for working with it.

    Features:
        * GitHub API utilization for extracting additional info about commits/PRs.
    """
    api = GitHubAPI
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

    def logs(self, before: str, commit_id: Optional[str] = None, tag_range: Optional[str] = None) -> Generator:
        """Get list of logs/commits in repository in reverse chronological order.

        Args:
            before (str): List only commits before this date.
            commit_id (Optional[str]): List only commits before this commit.
            tag_range (Optional[str]): List only commits within this tag range.

        Returns:
            Generator of commits before selected date/commit_id.
        """
        command = ["git", "rev-list"]
        if not commit_id and not tag_range:
            commit_id = "origin"
            command.extend(["--before", before])
            command.append(commit_id)
        if tag_range:
            command.append(tag_range)

        logger.info("git: logs: Command: " + " ".join(command))
        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
        hashes = process.stdout.decode("ascii").split()

        for _hash in hashes:
            command = ["git", "show", "--quiet", "--date=iso", _hash]
            logger.info("git: logs: Command: " + " ".join(command))
            process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
            commit = process.stdout.decode(errors="replace")
            yield _hash, commit
