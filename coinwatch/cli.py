# cli.py

from typing import List, Tuple

import click
import structlog

import coinwatch.src.db.crud as crud
from coinwatch.clients.cve import CVEClient
from coinwatch.clients.detection_methods import BlockScope, Simian
from coinwatch.clients.git import Git
from coinwatch.src.comparator import Comparator
from coinwatch.src.context_extractor import Context, Extractor
from coinwatch.src.cve_reader import load_references
from coinwatch.src.db.session import DBSession, db_session
from coinwatch.src.fixing_commits import FixCommitFinder
from coinwatch.src.notifications import Postman
from coinwatch.src.patch_fetcher import PatchCode
from coinwatch.src.schemas import CVE
from coinwatch.src.searcher import Searcher
from coinwatch.src.szz.szz import SZZ
from coinwatch.src.update_repos import get_repo_objects, update_repos

logger = structlog.get_logger(__name__)


def session_wrapper(func):
    def inner_wrapper(*args, **kwargs):
        with DBSession():
            func(*args, **kwargs)

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
            bug.patch = 'void BitcoinCore::shutdown()\n {\n     try\n     {\n         qDebug() << __func__ << ": Running Shutdown in thread";\n         m_node.appShutdown();\n         qDebug() << __func__ << ": Shutdown finished";\n         Q_EMIT shutdownResult();\n     } catch (const std::exception& e) {\n         handleRunawayException(&e);\n     } catch (...) {\n         handleRunawayException(nullptr);\n     }\n }\n \n-BitcoinApplication::BitcoinApplication(interfaces::Node& node, int &argc, char **argv):\n-    QApplication(argc, argv),\n+static int qt_argc = 1;\n+static const char* qt_argv = "bitcoin-qt";\n+\n+BitcoinApplication::BitcoinApplication(interfaces::Node& node):\n+    QApplication(qt_argc, const_cast<char **>(&qt_argv)),\n     coreThread(nullptr),\n     m_node(node),\n     optionsModel(nullptr),\n     clientModel(nullptr),\n     window(nullptr),\n     pollShutdownTimer(nullptr),\n     returnValue(0),\n     platformStyle(nullptr)\n {\n     setQuitOnLastWindowClosed(false);'
            crud.bug.update(db_session, bug)
        elif simian and not bug.code:
            # request input
            # patch: str = input("Input patch code/clone detection test:\n")
            bug.code = ""
            crud.bug.update(db_session, bug)

        cloned_repos: List[Git] = get_repo_objects(source=repo)
        update_repos(cloned_repos, repo_date)

        detection_method = (Simian if simian else BlockScope)(bug)
        for clone in cloned_repos:
            detection_result = detection_method.run(clone)
            detection_result = [result for result in detection_result if result[0] is not None]
            logger.info(f"{detection_result=}", repo=clone.repo)

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
            if not commits:
                logger.info(f"cli: Project OK.", repo=repo.repo)
                continue
            logger.info(f"cli: {repo.repo} found bug-fixes.", commits=commits)
            Postman().notify_bug_detection(commits, repo)
        logger.info("cli: Daily scan finished.")

    return wrapped_scanner()


@cli.command()
def db_init():
    from coinwatch.src.db.session import DBSchemaSetup, db_session
    from coinwatch.utils.db_init import init

    with DBSchemaSetup():
        init(db_session)


@cli.command()
def test_searcher():
    from tests.test_context_extraction import test_patch2

    repository: Git = Git("git@github.com:bitcoin/bitcoin.git")

    extractor = Extractor(5)
    patch_context: Tuple[Context, Context] = extractor.extract(test_patch2)

    searcher = Searcher(patch_context, repository)
    sr = searcher.search()

    patch_code = PatchCode(test_patch2.split("\n")).fetch()
    candidate_statuses = [Comparator.determine_patch_application(patch_code, candidate) for candidate in sr]
    pass


@cli.command()
def test():
    def test_run(cve):
        cve: CVE = CVEClient().cve_id(cve)

        repository: Git = Git("git@github.com:bitcoin/bitcoin.git")
        load_references(repository, cve.references)

        finder = FixCommitFinder(cve, repository)
        return finder.get_fix_commit()

    from tests.test import test_cve_fix_commit_pairs

    logger.info("Test CVE scraper + Commit finder")

    for i, test_case in enumerate(test_cve_fix_commit_pairs):
        logger.info(f"================ Test {i:2} ================")

        try:
            test_result = test_run(test_case[0])
            test_eval = test_result == test_case[1]
        except Exception as e:
            test_result = str(e)
            test_eval = False

        if test_eval:
            logger.info("Passed.")
        else:
            logger.error(f"Failed. {test_result}")

    logger.info("Test Context Extractor")
    from tests.test_context_extraction import test_list_context_extraction

    for i, test_case in enumerate(test_list_context_extraction):
        logger.info(f"================ Test {i:2} ================")

        try:
            ext = Extractor(5)
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


if __name__ == "__main__":
    cli()
