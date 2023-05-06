#!/usr/bin/env python3

# File: cli.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2022-09-28
# Description: Command line interface of the detection tool


from datetime import datetime as dt
from typing import List, Tuple

import click
import structlog
from crontab import CronTab

import cloneguard.src.db.crud as crud
from cloneguard.clients.detection_methods import BlockScope, Simian
from cloneguard.clients.git import Git
from cloneguard.src.db.schema import Bug, Project
from cloneguard.src.db.session import DBSession, db_session
from cloneguard.src.errors import CLIError
from cloneguard.src.fixing_commits import FixCommitFinder
from cloneguard.src.notifications import Postman
from cloneguard.src.update_repos import get_repo_objects, update_repos

logger = structlog.get_logger(__name__)


def session_wrapper(func):
    def inner_wrapper(*args, **kwargs):
        with DBSession():
            result = func(*args, **kwargs)
        return result

    return inner_wrapper


@click.group()
def cli():
    ...


@cli.command()
@click.argument("cve", required=True, type=str, nargs=1)
@click.argument("repo", required=False, type=str, nargs=1)
@click.argument("method", required=False, type=str, nargs=1, default="blockscope")
@click.argument("repo_date", required=False, type=str, nargs=1)
def run(cve: str, repo: str = "bitcoin", method: str = "blockscope", repo_date: str = ""):
    """Run the detection.

    CVE: ID of vulnerability to scan
    REPO: source repository where vulnerability was discovered
    SIMIAN: switch to use tool Simian for clone detection
    REPO_DATE: freeze scanned repositories at this date
    """

    @session_wrapper
    def wrapped_run():
        logger.info("cli: Run started.")

        repository: Git = Git(repo)
        finder = FixCommitFinder(repository, cve=cve)
        bug = finder.get_bug()
        logger.info(f"Detected fix commits: {bug.commits=}")

        if method == "simian" and not bug.code:
            raise CLIError("No code is specified for Simian detection method. Update the bug.code attribute.")

        cloned_repos: List[Git] = get_repo_objects(source=repository)
        # update_repos(cloned_repos, repo_date)

        method_class = Simian if method == "simian" else BlockScope
        detection_method = method_class(repository, bug)
        for clone in cloned_repos:
            detection_method.run(clone)

        logger.info("cli: Run finished.")

    return wrapped_run()


@cli.command()
@click.argument("every", required=False, type=str, nargs=1, default="1d")
def scan(every: str = "1d"):
    """Run discovery scan."""

    def to_cron_syntax(time: str):
        # process format HH:MM
        if len(time.split(":")) == 2:
            time = time.split(":")
            try:
                time = [int(x) for x in time]
            except Exception as e:
                logger.error("cli: Invalid time format. Supported formats: 10h | 10d | 17:00", time=time)
                return None
            return f"{time[1]} {time[0]} * * *"
        elif len(time.split(":")) > 2:
            logger.error("cli: Invalid time format. Supported formats: 10h | 10d | 17:00", time=time)
            return None

        # process format Hh | Dd (e.g. 10h | 10d)
        try:
            value, unit = int(time[:-1]), time[-1]
        except Exception as e:
            logger.error("cli: Invalid time format. Supported formats: 10h | 10d | 17:00", time=time)
            return None

        if unit == "h":  # hours
            return f"0 */{value} * * *"
        elif unit == "d":  # days
            return f"0 15 */{value} * *"

        logger.error("cli: Invalid time format. Supported formats: 10h | 10d | 17:00", time=time)
        return None

    @session_wrapper
    def wrapped_scanner():
        if every:
            cron_time = to_cron_syntax(every)
            if not cron_time:
                return
            logger.info("cli: Configure cron job.")
            cron = CronTab(user=True)
            cron.remove_all(comment="discovery_scan")
            command = f"cd /app && python3 -m cloneguard.cli scan > /app/cloneguard/_cache/discovery_scan.log"
            job = cron.new(command=command, comment="discovery_scan")
            logger.info(f"cli: Setting cron schedule to {cron_time}.")
            job.setall(cron_time)
            cron.write()
            logger.info("cli: Cron job configured.")
            return

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
                        fix_commit=f'["{commit}"]',
                        project=repo.id,
                    ),
                )
                detection_method = BlockScope(repo, bug)
                for clone in get_repo_objects(source=repo):
                    logger.info(f"cli: Scanning clone...", repo=clone.repo, bug_id=bug.id, commit=bug.fix_commit)
                    detection_method.run(clone)

        logger.info("cli: Daily scan finished.")

    return wrapped_scanner()


@cli.command()
@click.argument("URL", type=str)
@click.argument("language", type=str)
@click.option("--parent", type=str, default=None)
def register(url: str, language: str, parent: str | None):
    @session_wrapper
    def wrapped_register():
        logger.info("cli: Registering project...")

        project_info = Git._re_url_contents.search(url).groups()

        # check if project already exists
        if crud.project.get_by_name(db_session, project_info[1]):
            raise CLIError("Project already exists")
        # check if parent is registered - if specified
        if parent and not (reg_parent := crud.project.get_by_name(db_session, parent)):
            raise CLIError("Parent project not found")

        # create new project record
        project = crud.project.create(
            db_session,
            Project(
                url=url,
                name=project_info[1],
                author=project_info[0],
                language=language,
                parent_id=None if not parent else reg_parent.id,
            ),
        )

        logger.info("cli: Project registered.")

        # clone project
        logger.info("cli: Cloning project...")
        Git(project)
        logger.info("cli: Project cloned.")

    return wrapped_register()


@cli.command()
def db_init():
    from cloneguard.src.db.session import DBSchemaSetup

    # from cloneguard.utils.db_init import init

    with DBSchemaSetup():
        # init(db_session)
        pass


@cli.command()
def test_blockscope():
    @session_wrapper
    def run_test(source, bug, date, target):
        date = None
        repo = Git(source)
        bug = FixCommitFinder(repo, bug, cache=True).get_bug()
        bs = BlockScope(repo, bug)
        target = Git(target)
        update_repos([target], date)
        result = bs.run(target)
        del bs
        return result

    from cloneguard.tests.test_blockscope import test_cases

    logger.info("================ Test BS ================")
    for repo, bug, target, date, expected_result in test_cases:
        result = run_test(repo, bug, date, target)
        try:
            result[0][0]
        except Exception as e:
            print(f"Failed: {str(e)}")
            continue
        assert result[0][0] == expected_result[0][0], "FAILED"
        print("Passed")


if __name__ == "__main__":
    cli()
