from datetime import timedelta, date
from flask import Blueprint, render_template, abort, jsonify, request, redirect, url_for

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
    return render_template('standings.html', teams=sorted(season.teams.values(), key=lambda x: -x.current_rating),
        point_differentials=elo.get_point_differentials(games))


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





