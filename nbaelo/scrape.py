import collections
import logging
import time

import bs4
import pytz
import requests

from dateutil.parser import parse

logger = logging.getLogger(__name__)

Game = collections.namedtuple('Game', ['date', 'is_home_game', 'opponent',
    'points', 'opponent_points', 'opponent_symbol'])


def parse_url(url):
    url = url[url.find('teams/'):]
    _, team, year = url.split('/')
    year = int(year.split('.')[0])
    return team, year


def parse_game(row_soup):
    raw_data = {td.attrs['data-stat']: td.get_text() for td in row_soup.find_all('td')}

    raw_game_date = raw_data['date_game'] + ' ' + raw_data['game_start_time']
    # im making the assumption here that bball reference will always report game
    # start times in eastern time
    game_date = parse(raw_game_date).replace(tzinfo=pytz.timezone('US/Eastern'))
    is_home_game = bool(raw_data['game_location'].strip() != '@')
    opponent = raw_data['opp_name']
    opponent_symbol = [a.get('href') for a in row_soup.find_all('a') if '/teams/' in a.get('href')][0].split('/')[2]
    points = int(raw_data['pts']) if raw_data['pts'] else None
    opponent_points = int(raw_data['opp_pts']) if raw_data['opp_pts'] else None

    return Game(date=game_date, is_home_game=is_home_game, opponent=opponent,
        points=points, opponent_points=opponent_points, opponent_symbol=opponent_symbol)


def parse_schedule(raw_html):
    soup = bs4.BeautifulSoup(raw_html, 'lxml')
    table = soup.find('table', id='games')

    games = [parse_game(row) for row in table.find_all('tr') if row.find_all('td')]
    return games


def get_additional_links(raw_html):
    soup = bs4.BeautifulSoup(raw_html, 'lxml')

    links = []
    table = soup.find('table', id='games')
    for td in table.find_all('td', attrs={'data-stat': 'opp_name'}):
        links.append(td.find('a').get('href'))
    return list(set(links))


class GameScraper:

    DOMAIN = "http://www.basketball-reference.com"

    def __init__(self, seconds_between_requests=1):
        self.seconds_between_requests = seconds_between_requests

    def scrape(self, year, seed_team='LAL'):
        raw_html = self.fetch_schedule(year, seed_team)

        games = parse_schedule(raw_html)
        teams = {seed_team: games}

        team_links = get_additional_links(raw_html)

        for link in team_links:
            team, yr = parse_url(link)
            assert yr == year, 'Fetched schedule for %s, but found link for %s' % (year, yr)
            teams[team] = parse_schedule(self.fetch_schedule(year, team))

            time.sleep(self.seconds_between_requests)

        return teams

    def fetch_schedule(self, year, team):
        url = '/'.join([self.DOMAIN, 'teams', team.upper(), str(year) + '_games.html'])
        logger.info("Fetching game schedule for %s-%s at %s", year, team, url)
        response = requests.get(url)
        return response.text
