# NBA-ELO

This app is a ranking of all 30 NBA teams based on the [Elo rating system](https://en.wikipedia.org/wiki/Elo_rating_system)
commonly used in chess.

Live application: [nbaelo.herokuapp.com](http://nbaelo.herokuapp.com/)

## Setup Locally


```bash
$ pip install -r requirements.txt
$ python cli.py update # this will scrape data from basketball-reference.com
$ python manage.py runserver # start the server listening on port 5000
```


All data is scraped from [basketball-reference.com](http://www.basketball-reference.com/) and stored in a sqlite database
locally. You can change the database location in `config.py`

