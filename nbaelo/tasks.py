from datetime import timedelta, datetime, date
import math
import logging

from . import models, elo, db


logger = logging.getLogger(__name__)


def get_season_year_from_date(date):
    assert date.month not in (7, 8, 9), 'NBA schedule is from October-June'

    return date.year + 1 if date.month > 9 else date.year


def uncomplete_games(games, after_date):
    if isinstance(after_date, date):
        after_date = datetime(after_date.year, after_date.month, after_date.day)

    count = 0
    for game in games:
        if game.date.date() >= after_date:
            game.home_points = None
            game.away_points = None
            count += 1
    logger.info("Set %s games to be incomplete by setting home_points=away_points=None after %s", count, after_date)


def generate_daily_probabilities(date, trials=1000):
    season_year = get_season_year_from_date(date)
    season_id = models.Season.query.filter_by(year=season_year).first().id

    logger.info("Given date %s, found season_year=%s with primary_key=%s", date, season_year, season_id)

    games = models.Game.query.filter_by(season=season_id).all()
    logger.info("Retrieved %s games for season=%s", len(games), season_year)
    gs = elo.Game.from_list_of_games(games)

    uncomplete_games(gs, date)

    day_before_first_day_of_season = (min(g.date for g in gs) - timedelta(1)).date()
    logger.info("Day before first day of season for season=%s determined to be %s",
        season_year, day_before_first_day_of_season)
    teams = elo.Team.generate_teams_from_season_of_games(gs, day_before_first_day_of_season)

    logger.info("Loading data complete; beginning season simulations...")
    simulator = elo.Simulator(season_year, teams, gs)
    simulator.simulate_many_seasons(trials)

    outcomes = (simulator.playoff_probabilities, simulator.top_seed_probabilities, simulator.get_championship_probabilities())

    data = {}
    for team in outcomes[0].keys():
        data[team] = dict(playoff=outcomes[0][team], top_seed=outcomes[1][team],
            champion=outcomes[2][team])

    logger.info("Completed simulation for %s. Inserting data into database.", date)
    for team, probabilities in data.items():
        team_id = models.Team.query.filter_by(symbol=team).first().id
        logger.debug("Trying to insert probabilities for %s(team_id=%s, season_id=%s, date=%s)",
            team, team_id, season_id, date)

        preexisting = models.SimulatedProbabilities.query.filter_by(season_id=season_id, team_id=team_id, date=date).first()
        if preexisting is not None:
            logger.debug("Found existing entry for %s(team_id=%s) %s(season_id=%s) on %s. Proceeding to delete row.",
                team, team_id, season_year, season_id, date)
            db.session.delete(preexisting)
            db.session.commit()

        simulated_probalities = models.SimulatedProbabilities(season_id=season_id,
            team_id=team_id, date=date, playoff=probabilities['playoff'],
            top_seed=probabilities['top_seed'], champion=probabilities['champion'])
        db.session.add(simulated_probalities)
        db.session.commit()
    logger.info("Completed generating probabilities for all teams for %s", date)

# def generate_elo_history(year):
#     season_id = models.Season.query.filter_by(year=year).first().id

#     games = models.Game.query.filter_by(season=season_id).all()
#     day_before_first_day_of_season = min(g.date for g in games) - timedelta(1)
#     gs = elo.Game.from_list_of_games(games)
#     teams = elo.Team.generate_teams_from_season_of_games(gs, day_before_first_day_of_season)

#     season = elo.Season(year, teams, gs)
#     season.play_through_season()

#     total_change = 0
#     for symbol, team in season.teams.items():
#         team_id = models.Team.query.filter_by(symbol=symbol).first().id
#         preexisting_changes = models.EloHistory.query.filter_by(season_id=season_id, team_id=team_id)
#         preexisting_changes.delete()
#         for dt, change in team.rating_changes.items():
#             if change == 0:
#                 continue
#             elo_change = models.EloHistory(season_id=season_id, team_id=team_id, date=dt, rating_change=change)
#             db.session.add(elo_change)
#             total_change += change
#     assert math.isclose(0, total_change, abs_tol=0.00001)
#     db.session.commit()
