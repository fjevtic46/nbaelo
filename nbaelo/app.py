from datetime import timedelta, date, datetime
from flask import Blueprint, render_template, abort, jsonify, request, redirect, url_for

import sqlalchemy

from . import models, db, elo, utils, tasks


main = Blueprint('main', __name__)


def probabilities_to_json():
    pass

@utils.memoized
def get_season_or_404(year):
    season = models.Season.query.filter_by(year=year).first()
    if season is None:
        abort(404)
    return season

@utils.memoized
def get_team_or_404(team_symbol):
    team = models.Team.query.filter_by(symbol=team_symbol).first()
    if team is None:
        abort(404)
    return team


@utils.memoized
def get_played_through_season(year):
    season = get_season_or_404(year)
    games = models.Game.query.filter_by(season=season.id).all()
    day_before_first_day_of_season = min(g.date for g in games) - timedelta(1)
    gs = elo.Game.from_list_of_games(games)
    teams = elo.Team.generate_teams_from_season_of_games(gs, day_before_first_day_of_season)

    season = elo.Season(year, teams, gs)
    season.play_through_season()
    return season

@utils.memoized
def get_upcoming_games(date):
    # this is really ugly how come this simpler version wasn't working for me:
    # games = models.Game.query.filter(sqlalchemy.cast(models.Game.date, sqlalchemy.DATE) == date).all()

    year = tasks.get_season_year_from_date(date)
    season = get_played_through_season(year)
    games = [game for game in season if game.date.date() == date]

    upcoming_games = []
    for game in games:
        game_data = game.to_dict()
        away_elo = season.teams[game.away_team].current_rating
        home_elo = season.teams[game.home_team].current_rating
        game_data['away_elo'] = away_elo
        game_data['home_elo'] = home_elo
        game_data['away_win_prob'] = elo.get_expected_outcome(away_elo, home_elo)
        game_data['home_win_prob'] = elo.get_expected_outcome(home_elo, away_elo)
        upcoming_games.append(game_data)
    return dict(date=date.strftime('%Y-%m-%d'), games=upcoming_games)


@utils.memoized
def get_date_probabilities(date):
    probs = models.SimulatedProbabilities.query.filter(models.SimulatedProbabilities.date == date)
    return {p.team.symbol: p for p in probs}


def get_latest_date_available():
    return db.session.query(sqlalchemy.func.max(models.SimulatedProbabilities.date)).scalar()


@main.context_processor
def provide_season():
    if request.view_args is not None and "year" in request.view_args:
        year = request.view_args["year"]
        season = get_played_through_season(year)
        return dict(year=year, season=season)
    return dict()


@main.route('/')
def home():
    current_year = tasks.get_season_year_from_date(date.today())
    return redirect(url_for('main.standings_page', year=current_year))


@main.route('/standings/<int:year>')
def standings_page(year):
    season = get_played_through_season(year)
    games = season.games
    # upcoming_games = get_upcoming_games(utils.now_pst().date())
    latest_probabilities = get_date_probabilities(get_latest_date_available())
    return render_template('standings.html', teams=sorted(season.teams.values(), key=lambda x: -x.current_rating),
        point_differentials=elo.get_point_differentials(games),
        latest_probabilities=latest_probabilities)


@main.route('/team/<team_symbol>/<int:year>')
def team_page(team_symbol, year):
    team = get_team_or_404(team_symbol)
    return render_template('team.html', team=team)


@main.route('/api/probabilities/<int:year>/<int:team_id>/data.json')
def get_probabilities_timeseries(year, team_id):
    season = get_season_or_404(year)
    probabilities = models.SimulatedProbabilities.query.filter_by(season_id=season.id, team_id=team_id)\
        .order_by(models.SimulatedProbabilities.date).all()

    json_data = []
    for attr in ('playoff', 'top_seed', 'champion'):
        x = [{'date': p.date.strftime('%Y-%m-%d'), 'value': getattr(p, attr)} for p in probabilities]
        json_data.append(x)
    return jsonify(json_data)


@main.route('/api/elo/ratings/<int:year>/<int:team_id>/data.json')
def get_elo_rating_timeseries(year, team_id):
    season = get_played_through_season(year)

    team = models.Team.query.get(team_id)
    json_data = []
    for t in season.teams.values():
        if team.symbol != t.symbol:
            continue
        ratings = [{'date': dt.strftime('%Y-%m-%d'), 'value': rating} for dt, rating in t.rating_history]
        json_data.append(ratings)
    return jsonify(json_data)


@main.route('/api/games/<date_string>')
def foo(date_string):
    try:
        dt = datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        abort(404)

    return jsonify(get_upcoming_games(dt))





