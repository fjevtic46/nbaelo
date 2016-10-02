import os
from flask_script import Manager

from nbaelo import create_app

app = create_app(os.getenv('NBAELO_CONFIG', 'development'))

manager = Manager(app)


if __name__ == '__main__':
    manager.run()