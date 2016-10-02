# nbaelo scrape 2016
# nbaelo scrape 2015

# nbaelo delete 2015

# nbaelo createdb
import logging

import click
import nbaelo

from nbaelo import models
from nbaelo.scrape import GameScraper


logger = logging.getLogger(__name__)

@click.group()
def cli():
    pass


@cli.command()
@click.option('--drop', '-d', is_flag=True, help="Recreate database and soft reset using only teams data.")
def createdb(drop):
    Base = models.Base
    engine = models.engine
    if drop:
        logger.info("Dropping all tables in %s", engine)
        Base.metadata.drop_all(engine)
    logger.info("Creating database tables %s", engine)
    Base.metadata.create_all(engine)


@cli.command()
@click.argument('year', type=int)
def scrape(year):
    scraper = GameScraper()
    games = scraper.scrape(year)

    nbaelo.models.Game.insert_schedule_of_games(year, games)


if __name__ == '__main__':
    cli()