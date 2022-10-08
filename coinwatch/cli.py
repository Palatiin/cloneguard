# cli.py

import click

from src.cve_reader import *
from src.schemas import CVE
from utils import logger
from clients import CVEClient, GitHubAPI


@click.group()
def cli():
    logger.verbose = True


@cli.command()
@click.argument("cve", required=True, type=str)
def run(cve: str):
    """Scrape information about CVE."""

    logger.info("Scrape CVE...")
    cve: CVE = CVEClient().cve_id(cve)
    print(cve.json)
    logger.info("Scrape CVE done.")

    read_cve(cve)  # NOTE: tags - stats


if __name__ == '__main__':
    cli()
