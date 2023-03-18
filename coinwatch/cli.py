# cli.py

from typing import Tuple

import click
import structlog

import coinwatch.src.db.crud as crud
from coinwatch.clients import CVEClient, Git
from coinwatch.src.comparator import Comparator
from coinwatch.src.context_extractor import Context, Extractor
from coinwatch.src.cve_reader import load_references
from coinwatch.src.db.session import DBSession, db_session
from coinwatch.src.fixing_commits import FixCommitFinder
from coinwatch.src.patch_fetcher import PatchCode
from coinwatch.src.schemas import CVE
from coinwatch.src.searcher import Searcher
from coinwatch.src.szz.szz import SZZ

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
@click.argument("cve", required=True, type=str)
@click.argument("repo", required=False, type=str)
def run(cve: str, repo: str):
    @session_wrapper
    def wrapped_run(cve: str, repo: str):
        logger.info("Scrape CVE...")
        cve: CVE = CVEClient().cve_id(cve)
        logger.info("Scrape CVE done.")

        repository: Git = Git(repo or "git@github.com:bitcoin/bitcoin.git")

        logger.info("Load references...")
        load_references(repository, cve.references)
        logger.info("Load references done.")

        finder = FixCommitFinder(cve, repository)
        fix_commits = finder.get_fix_commit()
        logger.info(f"{fix_commits=}")

        szz = SZZ(repository, fix_commits)
        # fix_big_commit_pairs = szz.run()
        pass

    return wrapped_run(cve, repo)


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
