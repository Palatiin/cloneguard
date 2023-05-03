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

import cloneguard.src.db.crud as crud
from cloneguard.clients.detection_methods import BlockScope, Simian
from cloneguard.clients.git import Git
from cloneguard.src.comparator import Comparator
from cloneguard.src.context_extractor import Context, Extractor
from cloneguard.src.cve_reader import load_references
from cloneguard.src.db.schema import Bug
from cloneguard.src.db.session import DBSession, db_session
from cloneguard.src.fixing_commits import FixCommitFinder
from cloneguard.src.notifications import Postman
from cloneguard.src.patch_fetcher import PatchCode
from cloneguard.src.searcher import Searcher
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
@click.argument("simian", required=False, type=bool, nargs=1)
@click.argument("repo_date", required=False, type=str, nargs=1)
def run(cve: str, repo: str = "bitcoin", simian: bool = False, repo_date: str = ""):
    """Run the detection.

    CVE: ID of vulnerability to scan
    REPO: source repository where vulnerability was discovered
    SIMIAN: switch to use tool Simian for clone detection
    REPO_DATE: freeze scanned repositories at this date
    """

    @session_wrapper
    def wrapped_run(cve: str, repo: str, simian: bool, repo_date: str):
        logger.info("cli: Run started.")

        repo: Git = Git(repo)
        finder = FixCommitFinder(repo, cve=cve)
        bug = finder.get_bug()
        logger.info(f"Detected fix commits: {bug.commits=}")

        if not simian and not bug.patch:
            # request input
            # patch: str = input("Input patch code/clone detection test:\n")
            # bug.patch = 'void BitcoinCore::shutdown()\n {\n     try\n     {\n         qDebug() << __func__ << ": Running Shutdown in thread";\n         m_node.appShutdown();\n         qDebug() << __func__ << ": Shutdown finished";\n         Q_EMIT shutdownResult();\n     } catch (const std::exception& e) {\n         handleRunawayException(&e);\n     } catch (...) {\n         handleRunawayException(nullptr);\n     }\n }\n \n-BitcoinApplication::BitcoinApplication(interfaces::Node& node, int &argc, char **argv):\n-    QApplication(argc, argv),\n+static int qt_argc = 1;\n+static const char* qt_argv = "bitcoin-qt";\n+\n+BitcoinApplication::BitcoinApplication(interfaces::Node& node):\n+    QApplication(qt_argc, const_cast<char **>(&qt_argv)),\n     coreThread(nullptr),\n     m_node(node),\n     optionsModel(nullptr),\n     clientModel(nullptr),\n     window(nullptr),\n     pollShutdownTimer(nullptr),\n     returnValue(0),\n     platformStyle(nullptr)\n {\n     setQuitOnLastWindowClosed(false);'
            # crud.bug.update(db_session, bug)
            ...
        elif simian and not bug.code:
            # request input
            # patch: str = input("Input patch code/clone detection test:\n")
            # bug.code = ""
            # crud.bug.update(db_session, bug)
            ...

        cloned_repos: List[Git] = get_repo_objects(source=repo)
        update_repos(cloned_repos, repo_date)

        for clone in cloned_repos:
            # reinitialization of the detection method improves performance
            # otherwise the code would get stuck in detection_method.run
            detection_method = (Simian if simian else BlockScope)(repo, bug)
            detection_method.run(clone)
            del detection_method

        logger.info("cli: Run finished.")

    return wrapped_run(cve, repo, simian, repo_date)


@cli.command()
def scanner():
    @session_wrapper
    def wrapped_scanner():
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
                        project=repo.repo,
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
                        project=repo.repo,
                    ),
                )
                detection_method = BlockScope(repo, bug)
                detection_method.run(repo)

        logger.info("cli: Daily scan finished.")

    return wrapped_scanner()


@cli.command()
def db_init():
    from cloneguard.src.db.session import DBSchemaSetup, db_session
    from cloneguard.utils.db_init import init

    with DBSchemaSetup():
        init(db_session)


@cli.command()
def test_searcher():
    from tests.test_context_extraction import test_patch2

    repository: Git = Git("bitcoin")

    extractor = Extractor("cpp", 5)
    patch_context: Tuple[Context, Context] = extractor.extract(test_patch2)

    searcher = Searcher(patch_context, repository)
    sr = searcher.search()

    patch_code = PatchCode(test_patch2.split("\n")).fetch()
    candidate_statuses = [Comparator.determine_patch_application(patch_code, candidate) for candidate in sr]
    pass


@cli.command()
def test():
    def test_run(cve):
        repository: Git = Git("bitcoin")
        load_references(repository, cve.references)

        finder = FixCommitFinder(repository, cve, cache=False)
        return finder.get_fix_commit()

    # from tests.test import test_cve_fix_commit_pairs
    #
    # logger.info("Test CVE scraper + Commit finder")
    #
    # for i, test_case in enumerate(test_cve_fix_commit_pairs):
    #     logger.info(f"================ Test {i:2} ================")
    #
    #     try:
    #         test_result = test_run(test_case[0])
    #         test_eval = test_result == test_case[1]
    #     except Exception as e:
    #         test_result = str(e)
    #         test_eval = False
    #
    #     if test_eval:
    #         logger.info("Passed.")
    #     else:
    #         logger.error(f"Failed. {test_result}")

    logger.info("Test Context Extractor")
    from tests.test_context_extraction import test_list_context_extraction, test_patch_exception

    from cloneguard.src.errors import ContextExtractionError

    for i, test_case in enumerate(test_list_context_extraction):
        logger.info(f"================ Test {i:2} ================")

        try:
            ext = Extractor("cpp", 5)
            test_result = ext.extract(test_case[0])
            upper_ctx = [pair[1] for pair in test_result[0].sentence_keyword_pairs]
            lower_ctx = [pair[1] for pair in test_result[1].sentence_keyword_pairs]
            test_eval = upper_ctx == test_case[1][0]
            test_eval &= lower_ctx == test_case[1][1]
        except Exception as e:
            test_result = str(e)
            test_eval = False

        if test_eval:
            logger.info("Passed.")
        else:
            logger.error(f"Failed. {test_result}")

    logger.info(f"================ Test {i + 1:2} ================")
    try:
        Extractor("cpp", 5).extract(test_patch_exception)
        logger.error("Failed. Exception ContextExtractionError expected.")
    except ContextExtractionError:
        logger.info("Passed.")
    except Exception:
        logger.error("Failed. Exception ContextExtractionError expected.")


@cli.command()
def test_blockscope():
    @session_wrapper
    def run_test(source, bug, date, target):
        repo = Git(source)
        bug = FixCommitFinder(repo, bug, cache=True).get_bug()
        bs = BlockScope(repo, bug)
        target = Git(target)
        update_repos([target], date)
        result = bs.run(target)
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
