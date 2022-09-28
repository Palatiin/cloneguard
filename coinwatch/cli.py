# cli.py

import click

from utils import logger
from clients import CVE, CVEClient


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


if __name__ == '__main__':
    cli()
