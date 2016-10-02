# nbaelo scrape 2016
# nbaelo scrape 2015

# nbaelo delete 2015

# nbaelo createdb
import logging

import click
import nbaelo

from nbaelo import models, db
from nbaelo.scrape import GameScraper


logger = logging.getLogger(__name__)

@click.group()
def cli():
    pass


@cli.command()
@click.option('--drop', '-d', is_flag=True, help="Recreate database and soft reset using only teams data.")
def createdb(drop):
    if drop:
        db.drop_all()
    logger.info("Creating database tables %s", db)
    db.create_all()


@cli.command()
@click.argument('year', type=int)
def scrape(year):
    scraper = GameScraper()
    games = scraper.scrape(year)

    nbaelo.models.Game.insert_schedule_of_games(year, games)


if __name__ == '__main__':
    from manage import app
    # see http://stackoverflow.com/a/19438054
    # for why you need to do this
    app.app_context().push()
    cli()