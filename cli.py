# nbaelo scrape 2016
# nbaelo scrape 2015

# nbaelo delete 2015

# nbaelo createdb
import logging
from datetime import datetime, date, timedelta

import click
from sqlalchemy import func

import nbaelo

from nbaelo import models, db, tasks
from nbaelo.scrape import GameScraper


logger = logging.getLogger(__name__)


def date_range(dt1, dt2):
    dt1 = date.strptime(dt1, '%Y%m%d') if not isinstance(dt1, date) else dt1
    dt2 = date.strptime(dt2, '%Y%m%d') if not isinstance(dt2, date) else dt2
    logger.debug("Generating date range between %s and %s", dt1, dt2)
    assert dt2 > dt1

    for i in range((dt2 - dt1).days + 1):
        dt = dt1 + timedelta(i)
        yield dt


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
@click.option('--sleep', '-s', type=int, default=1)
def scrape(year, sleep):
    _scrape(year, sleep)


def _scrape(year, sleep=1):
    scraper = GameScraper(sleep)
    games = scraper.scrape(year)

    nbaelo.models.Game.insert_schedule_of_games(year, games)


@cli.command()
@click.argument('year', type=int)
@click.option('--force', '-f', is_flag=True, default=False)
@click.option('--trials', '-t', type=int, default=1000)
def generate_probabilities(year, force, trials):
    _generate_probabilities(year, force, trials)


def _generate_probabilities(year, force=False, trials=None):
    season_id = models.Season.query.filter_by(year=year).first().id
    first_day_of_season = db.session.query(func.min(models.Game.date)).filter(models.Game.season == season_id).scalar().date()
    last_day_of_season = db.session.query(func.max(models.Game.date)).filter(models.Game.season == season_id).scalar().date()

    # if we're doing this for a historical season we want to use the last day of
    # season. if we're doing this for current season we only want to generate data
    # for up to today
    last_day = min(date.today(), last_day_of_season)

    for dt in date_range(first_day_of_season, last_day):
        if force:
            logger.info("Generating team probabilities as of %s" % dt)
            tasks.generate_daily_probabilities(dt, trials)
        else:
            if not exists_date(dt):
                logger.info("Generating team probabilities as of %s" % dt)
                tasks.generate_daily_probabilities(dt, trials)
            logger.info("Probabilities for %s already exists. Skipping", dt)


@cli.command()
def bootstrap():
    db.create_all()
    current_year = datetime.now().year

    for year in (current_year - 1, year):
        _scrape(year)
        _generate_probabilities(current_year)


@cli.command()
@click.option('--sleep', '-s', type=int, default=10)
def update(sleep):
    season_year = tasks.get_season_year_from_date(date.today())
    _scrape(season_year, sleep=sleep)
    _generate_probabilities(season_year, force=False, trials=1000)


if __name__ == '__main__':
    from manage import app
    # see http://stackoverflow.com/a/19438054
    # for why you need to do this
    app.app_context().push()
    cli()
