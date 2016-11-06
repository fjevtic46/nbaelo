import os


basedir = os.path.abspath(os.path.dirname(__file__))

class Config:

    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hard*to!guess_string')
    NUMBER_NBA_TEAMS = 30

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'nba_games.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = True


    LOGO_URL_RESOURCE = 'https://d2p3bygnnzw9w3.cloudfront.net/req/201611021/tlogo/bbr/%s-2017.png'


    @classmethod
    def init_app(cls, app):
        pass



class HerokuConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


config = dict(
    development=Config(),
    heroku=HerokuConfig()
)