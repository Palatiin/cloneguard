# cli.py

import click

from src.selector.fixing_commits import get_fixing_commits
from src.schemas import CVE
from settings import logger
from clients import CVEClient, Git


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

    # read_cve(cve)  # NOTE: tags - stats
    repository: Git = Git("git@github.com:bitcoin/bitcoin.git")
    get_fixing_commits(repository, cve)


@cli.command()
@click.argument("url", required=True, type=str)
def clone(url):
    """Clone repository."""

    logger.info("Cloning target repository...")
    Git(url).clone()
    logger.info("Cloning done.")

if __name__ == '__main__':
    cli()
