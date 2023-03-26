# update_repos.py

from typing import List, Optional

import coinwatch.src.db.crud as crud
from coinwatch.clients.git import Git
from coinwatch.src.db.session import db_session


def get_repo_objects(source: Git) -> List[Git]:
    source = crud.project.get_by_name(db_session, source.repo)
    return [Git(repo) for repo in crud.project.get_all_clones(db_session, source)]


def update_repos(repo_list: List[Git], date: Optional[str] = None) -> None:
    for repo in repo_list:
        if date:
            repo.get_version_from_date(date)
        else:
            repo.sync()
