import os


basedir = os.path.abspath(os.path.dirname(__file__))

class Config:

    NUMBER_NBA_TEAMS = 30

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'nba_games.db')

config = Config()