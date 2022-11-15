# cli.py

import click

from coinwatch.clients import CVEClient, Git
from coinwatch.settings import logger
from coinwatch.src.cve_reader import load_references
from coinwatch.src.fixing_commits import FixCommitFinder
from coinwatch.src.schemas import CVE


@click.group()
def cli():
    logger.verbose = True


@cli.command()
@click.argument("cve", required=True, type=str)
def run(cve: str):
    """Scrape information about CVE."""
    logger.info("Scrape CVE...")
    cve: CVE = CVEClient().cve_id(cve)
    logger.info("Scrape CVE done.")

    repository: Git = Git("git@github.com:bitcoin/bitcoin.git")

    logger.info("Load references...")
    load_references(repository, cve.references)
    logger.info("Load references done.")

    finder = FixCommitFinder(cve, repository)
    fix_commits = finder.get_fix_commit()
    print(fix_commits)


@cli.command()
def test():
    def test_run(cve):
        cve: CVE = CVEClient().cve_id(cve)

        repository: Git = Git("git@github.com:bitcoin/bitcoin.git")
        load_references(repository, cve.references)

        finder = FixCommitFinder(cve, repository)
        return finder.get_fix_commit()

    from tests.test import test_cve_fix_commit_pairs

    logger.verbose = False

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


if __name__ == "__main__":
    cli()
