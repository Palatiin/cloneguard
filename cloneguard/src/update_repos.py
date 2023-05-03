# File: src/update_repos.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-03-13
# Description: Functions for fetching registered repositories and updating them.

from typing import List, Optional

import cloneguard.src.db.crud as crud
from cloneguard.clients.git import Git
from cloneguard.src.db.session import db_session


def get_repo_objects(source: Git) -> List[Git]:
    source = crud.project.get_by_name(db_session, source.repo)
    return [Git(repo) for repo in crud.project.get_all_clones(db_session, source)]


def update_repos(repo_list: List[Git], date: Optional[str] = None) -> None:
    for repo in repo_list:
        if date:
            repo.get_version_from_date(date)
        else:
            repo.sync()
