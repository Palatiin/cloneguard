# github.py

from typing import Dict, Optional

import requests
from settings import GITHUB_API_ACCESS_TOKEN  # noqa


class GitHubAPI:
    """
    GitHub API client.

    https://docs.github.com/en/rest

    Methods:
        * get_pull
        * get_commits_on_pull
        * get_affected_files_by_pull
        * get_issue
        * get_issue_timeline
        * get_file
    """

    base_url = "https://api.github.com"
    _headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_API_ACCESS_TOKEN}",
    }

    def get_pull(self, owner: str, repo: str, pull_number: int):
        """
        Get specific pull in project on GitHub.

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
        """
        Get commits on a specific PR in project on GitHub.

        https://docs.github.com/en/rest/pulls/pulls#list-commits-on-a-pull-request

        Args:
            owner (str): Owner of the repository
            repo (str): Name of the repository
            pull_number (int): ID of wanted pull

        Returns:
            Commits on a PR if found else None.
        """
        response = requests.get(
            f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/commits", headers=self._headers
        )
        if response.status_code != 200:
            return

        return response.json()

    def get_affected_files_by_pull(self, owner: str, repo: str, pull_number: int):
        """
        Get affected files in a specific PR in project on GitHub.

        https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files

        Args:
            owner (str): Owner of the repository
            repo (str): Name of the repository
            pull_number (int): ID of wanted pull

        Returns:
            Affected files in a PR if found else None.
        """
        response = requests.get(
            f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/files", headers=self._headers
        )
        if response.status_code != 200:
            return

        return response.json()

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Optional[Dict]:
        """
        Get specific issue in project on GitHub.

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

    def get_issue_timeline(self, owner: str, repo: str, issue_number: int) -> Optional[Dict]:
        """
        Get issue timeline in project on GitHub.

        https://docs.github.com/en/rest/issues/timeline#list-timeline-events-for-an-issue

        Args:
            owner (str): Owner of the repository
            repo (str): Name of the repository
            issue_number (int): ID of wanted issue

        Returns:
            Issue timeline if found else None.
        """
        response = requests.get(
            f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/timeline", headers=self._headers
        )
        if response.status_code != 200:
            return

        return response.json()

    def get_file(self, owner: str, repo: str, path: str) -> Optional[Dict]:
        """
        Get file from GitHub repository.

        https://docs.github.com/en/rest/repos/contents#get-repository-content

        Args:
            owner (str): Owner of the repository
            repo (str): Name of the repository
            path (str): path to file

        Returns:
            Encoded file data
        """
        response = requests.get(f"{self.base_url}/repos/{owner}/{repo}/contents/{path}", headers=self._headers)
        if response.status_code != 200:
            return

        return response.json()
