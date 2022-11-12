# cli.py

import click
from clients import CVEClient, Git
from settings import logger
from src.cve_reader import load_references
from src.schemas import CVE
from src.selector.fixing_commits import get_fixing_commits


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

    fix_commit = get_fixing_commits(repository, cve)  # List
    print(fix_commit)


@cli.command()
def test():
    def test_run(cve):
        cve: CVE = CVEClient().cve_id(cve)

        repository: Git = Git("git@github.com:bitcoin/bitcoin.git")
        load_references(repository, cve.references)

        return get_fixing_commits(repository, cve)

    from tests.test import test_cve_fix_commit_pairs

    logger.verbose = False

    for i, test_case in enumerate(test_cve_fix_commit_pairs):
        logger.info(f"================ Test {i:2} ================", v=True)

        try:
            test_result = test_run(test_case[0]) == test_case[1]
        except:
            test_result = False

        if test_result:
            logger.info("Passed.", v=True)
        else:
            logger.error("Failed.", v=True)


if __name__ == "__main__":
    cli()
