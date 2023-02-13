# cli.py

import click

from coinwatch.clients import CVEClient, Git
from coinwatch.settings import logger
from coinwatch.src.context_extractor import Context, Extractor
from coinwatch.src.cve_reader import load_references
from coinwatch.src.fixing_commits import FixCommitFinder
from coinwatch.src.schemas import CVE
from coinwatch.src.szz.szz import SZZ


@click.group()
def cli():
    logger.verbose = True


@cli.command()
@click.argument("cve", required=True, type=str)
@click.argument("repo", required=False, type=str)
def run(cve: str, repo: str):
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
    fix_big_commit_pairs = szz.run()
    pass


@cli.command()
def test():
    def test_run(cve):
        cve: CVE = CVEClient().cve_id(cve)

        repository: Git = Git("git@github.com:bitcoin/bitcoin.git")
        load_references(repository, cve.references)

        finder = FixCommitFinder(cve, repository)
        return finder.get_fix_commit()

    logger.verbose = False

    from tests.test import test_cve_fix_commit_pairs

    logger.info("Test CVE scraper + Commit finder", v=True)

    for i, test_case in enumerate(test_cve_fix_commit_pairs):
        logger.info(f"================ Test {i:2} ================", v=True)

        try:
            test_result = test_run(test_case[0])
            test_eval = test_result == test_case[1]
        except Exception as e:
            test_result = str(e)
            test_eval = False

        if test_eval:
            logger.info("Passed.", v=True)
        else:
            logger.error(f"Failed. {test_result}", v=True)

    logger.info("Test Context Extractor", v=True)
    from tests.test_context_extraction import test_list_context_extraction

    for i, test_case in enumerate(test_list_context_extraction):
        logger.info(f"================ Test {i:2} ================", v=True)

        try:
            ext = Extractor(5)
            test_result = ext.extract(test_case[0])
            test_eval = test_result[0].keywords == test_case[1][0]
            test_eval &= test_result[1].keywords == test_case[1][1]
        except Exceptions as e:
            test_result = str(e)
            test_eval = False

        if test_eval:
            logger.info("Passed.", v=True)
        else:
            logger.error(f"Failed. {test_result}", v=True)


if __name__ == "__main__":
    cli()
