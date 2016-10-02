from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


from . import scrape
from config import config

Base = declarative_base()


engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
sessionmkr = sessionmaker()
sessionmkr.configure(bind=engine)
session = sessionmkr()


# def scrape_and_insert_season(year):
#     scraper = scrape.GameScraper()
#     teams = scraper.scrape(year)
#     Game.insert_schedule_of_games(teams)


class Season(Base):
    __tablename__ = 'seasons'
    id = Column(Integer, primary_key=True)
    year = Column(Integer)


class Team(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    team_name = Column(String(32))
    # city = Column(String(32))
    symbol = Column(String(3))

    def __repr__(self):
            return '<%s %s>' % (self.__class__.__name__, self.team_name)


class Game(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True))
    home_id = Column(Integer, ForeignKey('teams.id'))
    away_id = Column(Integer, ForeignKey('teams.id'))
    home_points = Column(Integer)
    away_points = Column(Integer)
    season = Column(Integer, ForeignKey('seasons.id'))

    home_team = relationship('Team', foreign_keys='Game.home_id')
    away_team = relationship('Team', foreign_keys='Game.away_id')

    @classmethod
    def insert_schedule_of_games(cls, year, games):
        if session.query(Season).filter_by(year=year).count() == 0:
            season = Season(year=year)
            session.add(season)
            session.commit()
        else:
            season = session.query(Season).filter_by(year=year).first()

        team_symbols = {game.opponent_symbol: game.opponent for game in list(games.values())[0] + list(games.values())[1]}

        for symbol, team in team_symbols.items():
            if session.query(Team).filter_by(symbol=symbol).count() == 0:
                session.add(Team(team_name=team, symbol=symbol))
        session.commit()


        team_to_id = {team.symbol: team.id for team in session.query(Team).all()}
        for team, game_schedule in games.items():
            team_id = team_to_id[team]
            for game in game_schedule:
                opponent_id = team_to_id[game.opponent_symbol]
                date = game.date
                home_id = team_id
                away_id = opponent_id
                home_points = game.points
                away_points = game.opponent_points
                if not game.is_home_game:
                    home_id, away_id = away_id, home_id
                    home_points, away_points = away_points, home_points

                game_already_inserted = bool(session.query(cls)
                                            .filter_by(home_id=home_id, away_id=away_id, date=date)
                                            .count())
                if game_already_inserted:
                    continue
                session.add(cls(date=date, home_id=home_id, away_id=away_id,
                    home_points=home_points, away_points=away_points, season=season.id))
        session.commit()

    def __repr__(self):
        class_name = self.__class__.__name__
        home_team = self.home_team.symbol
        away_team = self.away_team.symbol
        home_points = self.home_points
        away_points = self.away_points
        date = self.date.strftime('%m-%d-%Y')
        return '<{class_name} {date} {away_team} ({away_points}) vs. {home_team} ({home_points})>'.format(class_name=class_name, home_team=home_team, away_team=away_team, home_points=home_points, away_points=away_points, date=date)