# github.py

import requests
from typing import Optional, Dict

from coinwatch.settings import GITHUB_API_ACCESS_TOKEN


class GitHubAPI:
    """GitHub API client.

    https://docs.github.com/en/rest
    """

    base_url = "https://api.github.com"
    _headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_API_ACCESS_TOKEN}",
    }

    def get_pull(self, owner: str, repo: str, pull_number: int):
        """Get specific pull in project on GitHub.

        https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request

        Args:
            owner (str): Owner of the repository
            repo (str): Name of the repository
            pull_number (int): ID of wanted pull

        Returns:
            Pull request if found else None.
        """
        response = requests.get(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}", headers=self._headers)
        if response.status_code != 200:
            return

        return response.json()

    def get_commits_on_pull(self, owner: str, repo: str, pull_number: int):
        """Get commits on a specific PR in project on GitHub.

        https://docs.github.com/en/rest/pulls/pulls#list-commits-on-a-pull-request

        Args:
            owner (str): Owner of the repository
            repo (str): Name of the repository
            pull_number (int): ID of wanted pull

        Returns:
            Commits on a PR if found else None.
        """
        response = requests.get(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/commits")
        if response.status_code != 200:
            return

        return response.json()

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Optional[Dict]:
        """Get specific issue in project on GitHub.

        https://docs.github.com/en/rest/issues/issues#get-an-issue

        Args:
            owner (str): Owner of the repository
            repo (str): Name of the repository
            issue_number (int): ID of wanted issue

        Returns:
            Issue data if found else None.
        """
        response = requests.get(f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}", headers=self._headers)
        if response.status_code != 200:
            return

        return response.json()


if __name__ == "__main__":
    gh = GitHubAPI()
    issue = gh.get_issue("bitcoin", "bitcoin", 26193)
    pass
