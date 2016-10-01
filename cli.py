# nbaelo scrape 2016
# nbaelo scrape 2015

# nbaelo delete 2015

# nbaelo createdb


import click
import nbaelo


@click.group()
def cli():
    pass


@cli.command()
@click.option('--drop', '-d', is_flag=True, help="Recreate database and soft reset using only teams data.")
def createdb(drop):
    Base = nbaelo.models.Base
    if drop:
        logger.info("Dropping all tables in %s", engine)
        Base.metadata.drop_all(engine)
    logger.info("Creating database tables %s", engine)
    Base.metadata.create_all(engine)


@cli.command()
@cli.argument('year')
def scrape(year):
    scraper = nbaelo.scraper.GameScraper()
    games = scraper.scrape(year)


if __name__ == '__main__':
    cli()