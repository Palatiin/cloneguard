# File: tasks.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-28
# Description: Worker tasks

from copy import deepcopy
from datetime import datetime as dt
import os
from typing import List

import structlog

import cloneguard.src.db.crud as crud
from cloneguard.clients.detection_methods import Simian, BlockScope
from cloneguard.clients.git import Git
from cloneguard.src.db.schema import Bug
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


def discovery_scan_task():
    if not os.path.exists(f"{settings.CACHE_PATH}/logs"):
        os.makedirs(f"{settings.CACHE_PATH}/logs")
    # '0' to be the last log file in the directory so it does not block logs from targeted detection
    settings.configure_logging(f"{settings.CACHE_PATH}/logs/0_discovery_scan.log")
    logger.info("cli: Daily scan started.")
    watched = [Git(repo) for repo in crud.project.get_all_watched(db_session)]
    update_repos(watched)

    for repo in watched:
        logger.info(f"cli: Scanning project.", repo=repo.repo)
        finder = FixCommitFinder(repo)
        commits = finder.scan_recent()

        complex_commits: List[str] = []
        simple_commits: List[str] = []
        for commit in commits:
            tmp_bug = Bug(cve_id=f"C#{commit[:10]}", fix_commit=f'["{commit}"]', project=repo.repo)
            detection_method = BlockScope(repo, tmp_bug)
            if len(detection_method.patch_contexts) > 1:
                complex_commits.append(commit)
            elif len(detection_method.patch_contexts):
                simple_commits.append(commit)

        commits = complex_commits + simple_commits
        if not commits:
            logger.info(f"cli: Project OK.", repo=repo.repo)
            continue
        logger.info(f"cli: {repo.repo} found bug-fixes.", commits=commits)
        Postman().notify_bug_detection(commits, repo)

        # create single record in table Bug for all complex commits
        if complex_commits:
            date = dt.now().strftime("%y%m%d")  # YYMMDD
            bug = crud.bug.create(
                db_session,
                Bug(
                    cve_id=f"SCAN-{date}",
                    project=repo.id,
                ),
            )
            bug.commits = complex_commits
            crud.bug.update(db_session, bug)

        # create single record in table Bug for each simple commits and run detection method for each
        for commit in simple_commits:
            bug = crud.bug.create(
                db_session,
                Bug(
                    cve_id=f"C#{commit[:10]}",
                    fix_commit=f'["{commit[:10]}"]',
                    project=repo.id,
                ),
            )
            detection_method = BlockScope(repo, bug)
            for clone in get_repo_objects(source=repo):
                logger.info(f"cli: Scanning clone...", repo=clone.repo, bug_id=bug.id, commit=bug.fix_commit)
                detection_method.run(clone)

    logger.info("cli: Daily scan finished.")
