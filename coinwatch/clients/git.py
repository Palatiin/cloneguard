# git.py

import re
import subprocess
from typing import Optional, NoReturn, Generator

from coinwatch.clients import GitHubAPI
from settings import logger  # noqa


class Git:
    api = GitHubAPI
    _re_url_contents = re.compile(r"/(?P<owner>\w+)/(?P<repo>\w+)\.git")

    base_path = "_cache/clones"

    def __init__(self, url: str):
        url_contents = self._re_url_contents.search(url)
        if not url_contents:
            logger.error("clients: git: Couldn't extract repo name from url.")
            return
        self.url = url
        self.owner = url_contents.group("owner")
        self.repo = url_contents.group("repo")
        self.path_to_repo = f"{self.base_path}/{self.repo}"

    def clone(self) -> NoReturn:
        process = subprocess.run(["git", "clone", self.url, self.path_to_repo], stdout=subprocess.PIPE)
        if process.returncode != 0:
            logger.error("clients: git: clone: Couldn't clone the repository.")

    def logs(self, before: str, commit_id: Optional[str] = None) -> Generator:
        command = ["git", "rev-list"]
        if not commit_id:
            commit_id = "origin"
            command.extend(["--before", before])
        command.append(commit_id)

        process = subprocess.run(command, cwd=self.path_to_repo, stdout=subprocess.PIPE)
        hashes = process.stdout.decode("ascii").split()

        for _hash in hashes:
            process = subprocess.run(
                ["git", "show", "--quiet", "--date=iso", _hash], cwd=self.path_to_repo, stdout=subprocess.PIPE
            )
            commit = process.stdout.decode(errors="replace")
            yield commit
