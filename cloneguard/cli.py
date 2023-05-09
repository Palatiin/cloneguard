#!/usr/bin/env python3

# File: cli.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2022-09-28
# Description: Command line interface of the detection tool


from typing import List
import subprocess

import click
import redis
from rq import Queue
import structlog
from crontab import CronTab

import cloneguard.src.db.crud as crud
from cloneguard.clients.detection_methods import BlockScope, Simian
from cloneguard.clients.git import Git
from cloneguard.settings import REDIS_URL
from cloneguard.src.db.schema import Project
from cloneguard.src.db.session import DBSession, db_session
from cloneguard.src.errors import CLIError
from cloneguard.src.fixing_commits import FixCommitFinder
from cloneguard.src.update_repos import get_repo_objects, update_repos
from cloneguard.tasks import discovery_scan_task

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
@click.option("--date", type=str, default="")
def run(cve: str, repo: str = "bitcoin", method: str = "blockscope", date: str = ""):
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
        update_repos(cloned_repos, date)

        method_class = Simian if method == "simian" else BlockScope
        detection_method = method_class(repository, bug)
        for clone in cloned_repos:
            detection_method.run(clone)

        logger.info("cli: Run finished.")

    return wrapped_run()


@cli.command()
@click.argument("every", required=False, type=str, nargs=1, default="")
def scan(every: str = ""):
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

    if every:
        cron_time = to_cron_syntax(every)
        if not cron_time:
            return
        logger.info("cli: Starting cron.service")
        try:
            subprocess.run(["systemctl", "start", "cron"], check=True)
        except subprocess.CalledProcessError as e:
            logger.error("cli: Failed to start cron.service", error=e.stderr)
            return

        logger.info("cli: Configure cron job.")
        cron = CronTab(user=True)
        cron.remove_all(comment="discovery_scan")
        command = f"cd /app && ./cli scan > /app/cloneguard/_cache/discovery_scan.log"
        job = cron.new(command=command, comment="discovery_scan")
        logger.info(f"cli: Setting cron schedule to {cron_time}.")
        job.setall(cron_time)
        cron.write()
        logger.info("cli: Cron job configured.")
        return

    # schedule discovery scan
    redis_conn = redis.Redis.from_url(REDIS_URL)
    queue = Queue("task_queue", connection=redis_conn, default_timeout=900)
    queue.enqueue(discovery_scan_task)
    logger.info("cli: Discovery scan scheduled.")


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
