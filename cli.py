# nbaelo scrape 2016
# nbaelo scrape 2015

# nbaelo delete 2015

# nbaelo createdb
import logging
from datetime import datetime, date, timedelta

import click
import nbaelo

from nbaelo import models, db, tasks
from nbaelo.scrape import GameScraper


logger = logging.getLogger(__name__)


def date_range(dt1, dt2):
    dt1 = datetime.strptime(dt1, '%Y%m%d') if not isinstance(dt1, (date, datetime)) else dt1
    dt2 = datetime.strptime(dt2, '%Y%m%d') if not isinstance(dt2, (date, datetime)) else dt2

    assert dt2 > dt1

    for i in range((dt2 - dt1).days + 1):
        yield dt1 + timedelta(i)


def exists_date(dt):
    return bool(models.SimulatedProbabilities.query.filter_by(date=dt).first())


@click.group()
@click.option('--verbose', is_flag=True, help="Increase logging output")
def cli(verbose):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if verbose:
        logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


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


@cli.command()
@click.argument('year', type=int)
@click.option('--force', '-f', is_flag=True, default=False)
def generate_probabilities(year, force):
    season_id = models.Season.query.filter_by(year=year).first().id
    first_day_of_season = db.session.query(func.min(models.Game.date)).filter(models.Game.season == season_id).scalar()
    last_day_of_season = db.session.query(func.max(models.Game.date)).filter(models.Game.season == season_id).scalar()

    for dt in date_range(first_day_of_season, last_day_of_season):
        if force:
            logger.info("Generating team probabilities as of %s" % dt)
            tasks.generate_daily_probabilities(dt)
        else:
            if not exists_date(dt):
                logger.info("Generating team probabilities as of %s" % dt)
                tasks.generate_daily_probabilities
            logger.info("Probabilities for %s already exists. Skipping")



if __name__ == '__main__':
    from manage import app
    # see http://stackoverflow.com/a/19438054
    # for why you need to do this
    app.app_context().push()
    cli()
