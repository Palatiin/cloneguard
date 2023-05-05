# File: tasks.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-28
# Description: Worker tasks

from copy import deepcopy
import os

import structlog

import cloneguard.src.db.crud as crud
from cloneguard.clients.detection_methods import Simian, BlockScope
from cloneguard.clients.git import Git
from cloneguard.src.db.session import db_session
from cloneguard.src.fixing_commits import FixCommitFinder
from cloneguard.src.notifications import Postman
from cloneguard.src.update_repos import get_repo_objects, update_repos
import cloneguard.settings as settings

logger = structlog.get_logger(__name__)


def clone_task(project_name: str):
    logger.info("Starting cloning task...")
    repo = crud.project.get_by_name(db_session, project_name)
    Git(repo)
    logger.info("Cloning task finished.")


def execute_task(bug_id: str, commit: str, patch: str, method: str, project_name: str, date: str, timestamp):
    if not os.path.exists(f"{settings.CACHE_PATH}/logs"):
        os.makedirs(f"{settings.CACHE_PATH}/logs")
    settings.configure_logging(f"{settings.CACHE_PATH}/logs/{timestamp}.log")
    logger.info("Starting detection method...", bug_id=bug_id, commit=commit)
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

    method_class = Simian if method == "simian" else BlockScope
    detection_method = method_class(repo, bug)
    for clone in clones:
        detection_method.run(clone)

    logger.info("Detection method finished.")
