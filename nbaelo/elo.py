import collections
import datetime
import itertools
import random

from config import Config


WESTERN_CONFERENCE = 'West'
EASTERN_CONFERENCE = 'East'

# standings -> seed into playoffs
# and then simulate playoffs 10k times: PlayoffSimulator

def get_expected_outcome(rating1, rating2):
    """is the expected result (win expectancy), http://www.eloratings.net/system.html

    #TODO: simple test: same ratings == 0.5, check if r1 > r2 => x > 0.5
    """
    x = 1 + 10**((rating2 - rating1)/400.)
    return 1. / x


def uncomplete_games(games, after_date):
    for game in games:
        if game.date > after_date:
            game.home_points = None
            game.away_points = None


def create_conferences(games_schedule):
    """
    from single season game schedule -> return list of temas by conference
    NBA SCHEDULING FORMULA
Each team have to play:
4 games against the other 4 division opponents, [4x4=16 games]
4 games against 6 (out-of-division) conference opponents, [4x6=24 games]
3 games against the remaining 4 conference teams, [3x4=12 games]
2 games against teams in the opposing conference. [2x15=30 games]

http://www.nbastuffer.com/component/option,com_glossary/Itemid,0/catid,44/func,view/term,How%20the%20NBA%20Schedule%20is%20Made/
"""
    team_count = collections.defaultdict(int)
    for game in games_schedule:
        team_count[game.home_team] += 1
        team_count[game.away_team] += 1

    western_conference = set([team for team, count in team_count.items() if count > 2])
    eastern_conference = set([team for team, count in team_count.items() if count <= 2])

    # this is pretty hacky but i dont know how else to know which of the two
    # conferences is the western conference
    if 'LAL' not in western_conference and 'LAL' in eastern_conference:
        western_conference, eastern_confernece = eastern_conference, western_conference
    return western_conference, eastern_conference


def map_teams_to_their_games(season_of_games):
    """List of all games in a season -> return dictionary of teams with game schedule
    """
    teams = {}

    for game in season_of_games:
        assert isinstance(game, Game)
        home_team = game.home_team
        away_team = game.away_team
        if home_team not in teams:
            teams[home_team] = []
        if away_team not in teams:
            teams[away_team] = []

        teams[home_team].append(game)
        teams[away_team].append(game)
    return teams


def is_game_complete(game):
    return game.home_points is not None or game.away_points is not None


def get_point_differentials(games):
    teams = {}

    for game in games:
        if game.away_team not in teams:
            teams[game.away_team] = {'points_scored': 0, 'points_allowed': 0, 'games_played': 0, 'points_differential': 0}
        if game.home_team not in teams:
            teams[game.home_team] = {'points_scored': 0, 'points_allowed': 0, 'games_played': 0, 'points_differential': 0}
        if not game.is_complete:
            continue

        teams[game.away_team]['points_scored'] += game.away_points
        teams[game.away_team]['points_allowed'] += game.home_points
        teams[game.away_team]['games_played'] += 1
        teams[game.away_team]['points_differential'] = \
            (teams[game.away_team]['points_scored'] - teams[game.away_team]['points_allowed']) / teams[game.away_team]['games_played']
        teams[game.home_team]['points_scored'] += game.home_points
        teams[game.home_team]['points_allowed'] += game.away_points
        teams[game.home_team]['games_played'] += 1
        teams[game.home_team]['points_differential'] = \
            (teams[game.home_team]['points_scored'] - teams[game.home_team]['points_allowed']) / teams[game.home_team]['games_played']

    return teams


class Team:

    def __init__(self, symbol, start_date, conference, start_rating=1500):
        self.symbol = symbol
        self.start_date = start_date
        self.start_rating = start_rating
        self.rating_changes = {}
        self.rating_changes[start_date] = 0
        self.wins = 0
        self.losses = 0
        self.conference = conference

    def update_rating(self, date, rating_change, is_win):
        self.rating_changes[date] = rating_change
        if is_win:
            self.wins += 1
        else:
            self.losses += 1

    def change_past_games(self, num_games):
        assert num_games > 0
        reverse_ordered_changes = list(reversed(sorted(self.rating_changes.items(), key=lambda x: x[0])))

        total_games_played = len(reverse_ordered_changes)
        return sum([reverse_ordered_changes[i][1] for i in range(num_games) if i < total_games_played])

    @property
    def logo_url(self):
        return Config.LOGO_URL_RESOURCE % (self.symbol)

    @property
    def current_rating(self):
        return self.start_rating + sum(self.rating_changes.values())

    @property
    def current_record(self):
        return (self.wins, self.losses)

    @property
    def rating_history(self):
        first_date = min(self.rating_changes.keys())
        last_date = max(self.rating_changes.keys())

        total_change_each_date = collections.OrderedDict()

        for i in range((last_date - first_date).days + 2):
            dt = first_date.date() + datetime.timedelta(days=i)
            total_change_each_date[dt] = 0

        for gamedate, rating_change in self.rating_changes.items():
            total_change_each_date[gamedate.date()] += rating_change

        cumulative_changes = list(itertools.accumulate(total_change_each_date.values()))

        return [(dt, change + self.start_rating) for dt, change in\
            zip(total_change_each_date.keys(), cumulative_changes)]

    @classmethod
    def generate_teams_from_season_of_games(cls, games, start_date):
        team_games = map_teams_to_their_games(games)

        western, eastern = create_conferences(next(iter(team_games.values())))

        teams = []
        for team in team_games.keys():
            conference = WESTERN_CONFERENCE if team in western else EASTERN_CONFERENCE
            teams.append(cls(team, start_date, conference))
        return teams


class Game:

    """Wrapper class for models.Game to be used in Season."""

    def __init__(self, home_team, away_team, date, home_points=None, away_points=None):
        self.home_team = home_team
        self.away_team = away_team
        self.date = date
        self.home_points = home_points
        self.away_points = away_points
        self.is_simulated = False

    def simulate(self, home_elo_rating, away_elo_rating):
        #TODO: test raises error here
        if self.is_complete:
            raise ValueError("Can not simulate a game already completed.")
        # random
        home_team_win_probability = get_expected_outcome(home_elo_rating, away_elo_rating)
        if random.random() < home_team_win_probability:
            self.home_points = -1
            self.away_points = -2
        else:
            self.home_points = -2
            self.away_points = -1
        self.is_simulated = True

    @property
    def is_complete(self):
        return self.home_points is not None and self.away_points is not None

    @property
    def winner(self):
        return self.home_team if self.home_points > self.away_points else self.away_team

    @property
    def loser(self):
        return self.away_team if self.winner == self.home_team else self.home_team

    @classmethod
    def from_list_of_games(cls, games):
        """Creates a copy of list of games"""
        gs = []
        for g in games:
            home_team = g.home_team if isinstance(g.home_team, str) else g.home_team.symbol
            away_team = g.away_team if isinstance(g.away_team, str) else g.away_team.symbol
            gs.append(cls(home_team, away_team, g.date, g.home_points, g.away_points))
        return gs

    def to_dict(self):
        return dict(home_team=self.home_team, away_team=self.away_team, date=self.date,
                home_points=self.home_points, away_points=self.away_points, is_simulated=self.is_simulated)


class Season:

    k_factor = 20

    def __init__(self, year, teams, games):
        self.year = year
        self.teams = {team.symbol: team for team in teams}
        # we need to guarantee the list of games is in order of date played
        # especially as we compute rating changes:
        self.games = list(sorted(games, key=lambda x: x.date))

    # def __getitem__(self, key):
        # return self.games[key]

    def update_ratings(self, game, k_factor=None):
        if k_factor is None:
            k_factor = self.k_factor
        home_team = self.teams[game.home_team]
        away_team = self.teams[game.away_team]
        margin = game.home_points - game.away_points
        home_team_won = margin > 0

        numerator = (abs(margin) + 3)**0.8

        denom = 7.5 + .0006 * (home_team.current_rating - away_team.current_rating)

        expected_outcome = get_expected_outcome(home_team.current_rating, away_team.current_rating)
        if game.home_points > game.away_points:
            outcome = (1 - expected_outcome)
        else:
            outcome = -expected_outcome
        home_change = k_factor * (numerator / denom) * outcome
        away_change = -home_change
        home_team.update_rating(game.date, home_change, home_team_won)
        away_team.update_rating(game.date, away_change, not home_team_won)

    def play_through_season(self, stop_date=None):
        for game in self.games:
            if not game.is_complete:
                continue

            if stop_date is not None and stop_date > game.date:
                continue

            self.update_ratings(game)

    def simulate_remaining(self):
        for game in self.games:
            if game.is_complete:
                continue
            home_team = self.teams[game.home_team]
            away_team = self.teams[game.away_team]
            game.simulate(home_team.current_rating, away_team.current_rating)

    @property
    def first_day(self):
        return min(g.date for g in self.games)

    @property
    def last_day(self):
        return max(g.date for g in self.games)


    @property
    def current_season_date(self):
        for game in self.games:
            if not game.is_complete:
                return game.date.date()
        return game.date.date()


    @property
    def is_season_complete(self):
        # check if all teh games have non null points values
        return all(g.is_complete for g in self.games)

    @property
    def current_standings(self):
        team_records = {}
        for game in self.games:
            if not game.is_complete:
                continue
            home = game.home_team
            away = game.away_team
            if home not in team_records:
                team_records[home] = [0, 0]
            if away not in team_records:
                team_records[away] = [0, 0]

            assert game.home_points != game.away_points
            if game.home_points > game.away_points:
                team_records[home][0] += 1
                team_records[away][1] += 1
            else:
                team_records[home][1] += 1
                team_records[away][0] += 1
        team_records = {k: tuple(v) for k, v in team_records.items()}

        western = [(team, record, self.teams[team]) for team, record in team_records.items() if self.teams[team].conference == WESTERN_CONFERENCE]
        eastern = [(team, record, self.teams[team]) for team, record in team_records.items() if self.teams[team].conference == EASTERN_CONFERENCE]

        def sort_standings(standings):
            return list(reversed(sorted(standings, key=lambda x: x[1])))

        return sort_standings(western), sort_standings(eastern)

    def __iter__(self):
        for game in self.games:
            yield game


class PlayoffSimulator:

    def __init__(self, year, teams, standings, games=None):
        self.year = year
        self.teams = teams
        self.standings = standings

    def simulate_conference_brackets(self, standings):
        # round1: 1 vs 8
        # round2: 2 vs 7
        # round3: 3 vs 6
        # round4: 4 vs 5

        # round1 plays round4
        # round2 plays round3

        w1w8 = PlayoffRound(standings[0][2], standings[7][2]).simulate_winner()
        w2w7 = PlayoffRound(standings[1][2], standings[6][2]).simulate_winner()
        w3w6 = PlayoffRound(standings[2][2], standings[5][2]).simulate_winner()
        w4w5 = PlayoffRound(standings[3][2], standings[4][2]).simulate_winner()

        x1 = PlayoffRound(w1w8, w4w5).simulate_winner()
        x2 = PlayoffRound(w2w7, w3w6).simulate_winner()
        return PlayoffRound(x1, x2).simulate_winner()

    def simulate_playoffs(self):
        #  treat each conference separately genrate brackets for each bracket
        #  create round from winner of each bracket

        west, east = self.standings

        west_winner = self.simulate_conference_brackets(west)
        east_winner = self.simulate_conference_brackets(east)

        championship = PlayoffRound(west_winner, east_winner)
        champion = championship.simulate_winner()
        return champion


class PlayoffRound:

    def __init__(self, team1, team2):
        # assume team1 is the higher seeded team
        self.team1 = team1
        self.team2 = team2

    def simulate_winner(self):
        team1_wins = 0
        team2_wins = 0
        team1_win_probability = get_expected_outcome(self.team1.current_rating, self.team2.current_rating)

        while (team1_wins < 4 or team2_wins < 4):
            if random.random() < team1_win_probability:
                team1_wins += 1
            else:
                team2_wins += 1

        return self.team1 if team1_wins > team2_wins else self.team2


class Simulator:

    def __init__(self, year, teams, games):
        self.year = year
        self.teams = teams
        self.games = games

        self.simulated_seasons = []

    def create_season(self):
        # need to create a new copy of games because as we simulate the games
        # we are overriding the attributes
        games = Game.from_list_of_games(self.games)
        return Season(self.year, self.teams, games)


    def simulate_many_seasons(self, trials=1000):
        for _ in range(trials):
            season = self.create_season()
            season.play_through_season()
            season.simulate_remaining()

            self.simulated_seasons.append(season)

    @property
    def playoff_probabilities(self):
        teams = {team.symbol: 0 for team in self.teams}
        for season in self.simulated_seasons:
            west, east = season.current_standings
            for row in itertools.chain(west[:8], east[:8]):
                team = row[0]
                teams[team] += 1
        return {team: counts / len(self.simulated_seasons) for team, counts in teams.items()}

    @property
    def top_seed_probabilities(self):
        teams = {team.symbol: 0 for team in self.teams}
        for season in self.simulated_seasons:
            west, east = season.current_standings
            for row in (west[0], east[0]):
                team = row[0]
                teams[team] += 1
        return {team: counts / len(self.simulated_seasons) for team, counts in teams.items()}

    def get_championship_probabilities(self):
        teams = {team.symbol: 0 for team in self.teams}
        for season in self.simulated_seasons:
            playoffs = PlayoffSimulator(self.year, self.teams, season.current_standings)
            champion = playoffs.simulate_playoffs()
            teams[champion.symbol] += 1

        return {team: counts / len(self.simulated_seasons) for team, counts in teams.items()}






