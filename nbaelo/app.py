from datetime import timedelta
from flask import Blueprint, render_template

from . import models, db, elo


main = Blueprint('main', __name__)


@main.route('/')
def home():
    return 'hi'


@main.route('/standings/<int:year>')
def standings_page(year):
    season_id = models.Season.query.filter_by(year=year).first().id

    games = models.Game.query.filter_by(season=season_id).all()
    day_before_first_day_of_season = min(g.date for g in games) - timedelta(1)
    gs = elo.Game.from_list_of_games(games)
    teams = elo.Team.generate_teams_from_season_of_games(gs, day_before_first_day_of_season)

    season = elo.Season(year, teams, gs)
    season.play_through_season()
    return render_template('standings.html', teams=sorted(season.teams.values(), key=lambda x: -x.current_rating),
        point_differentials=elo.get_point_differentials(gs))
