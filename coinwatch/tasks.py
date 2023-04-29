# File: tasks.py
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-28
# Description: Worker tasks

import os

import structlog

from copy import deepcopy

import coinwatch.src.db.crud as crud
from coinwatch.clients.detection_methods import Simian, BlockScope
from coinwatch.clients.git import Git
from coinwatch.src.db.session import db_session
from coinwatch.src.update_repos import get_repo_objects, update_repos
import coinwatch.settings as settings

logger = structlog.get_logger(__name__)


def execute_task(bug_id: str, commit: str, patch: str, method: str, project_name: str, date: str, timestamp):
    if not os.path.exists(f"{settings.CACHE_PATH}/logs"):
        os.makedirs(f"{settings.CACHE_PATH}/logs")
    settings.configure_logging(f"{settings.CACHE_PATH}/logs/{timestamp}.log")
    logger.info("Starting detection method...")
    bug = crud.bug.get_cve(db_session, bug_id)
    bug = deepcopy(bug)
    bug.commits = [commit]
    if method == "simian":
        bug.code = patch
    else:
        bug.patch = patch

    repo = crud.project.get_by_name(db_session, project_name)
    repo = Git(repo)

    clones = get_repo_objects(source=repo)
    update_repos(clones, date)

    for clone in clones:
        detection_method = (Simian if method == "simian" else BlockScope)(repo, bug)
        detection_method.run(clone)

    logger.info("Detection method finished.")
