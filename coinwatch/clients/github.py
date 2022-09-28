# github.py

import requests
from typing import Optional, Dict

from coinwatch.settings import GITHUB_API_ACCESS_TOKEN


class GitHubAPI:
    base_url = "https://api.github.com"

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Optional[Dict]:
        """Get specific issue from github project.

        https://docs.github.com/en/rest/issues/issues#get-an-issue

        Args:
            owner (str): Owner of the repository
            repo (str): Name of the repository
            issue_number (int): ID of wanted issue

        Returns:
            Issue data if found else None.

        """
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_API_ACCESS_TOKEN}",
        }
        response = requests.get(f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}", headers=headers)
        if response.status_code != 200:
            return

        return response.json()


if __name__ == "__main__":
    gh = GitHubAPI()
    issue = gh.get_issue("bitcoin", "bitcoin", 26193)
    pass
