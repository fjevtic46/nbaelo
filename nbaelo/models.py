from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


from config import config

Base = declarative_base()


engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
sessionmkr = sessionmaker()
sessionmkr.configure(bind=engine)
session = sessionmkr()


class Season(Base):
    __tablename__ = 'seasons'
    id = Column(Integer, primary_key=True)
    year = Column(Integer)


class Team(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    team_name = Column(String(32))
    city = Column(String(32))
    symbol = Column(String(3))

    def __repr__(self):
            return '<%s %s %s>' % (self.__class__.__name__, self.city, self.team_name)


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

    def __repr__(self):
        class_name = self.__class__.__name__
        home_team = self.home_team.symbol
        away_team = self.away_team.symbol
        home_points = self.home_points
        away_points = self.away_points
        date = self.date.strftime('%m-%d-%Y')
        return '<{class_name} {date} {away_team} ({away_points}) vs. {home_team} ({home_points})>'.format(class_name=class_name, home_team=home_team, away_team=away_team, home_points=home_points, away_score=away_points, date=date)