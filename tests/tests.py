import os
import sys
import unittest
from unittest import mock
import datetime

basedir = os.path.dirname(__file__)
sys.path.append(os.path.dirname(basedir))

import pytz
import bs4

from nbaelo import scrape


class TestScraping(unittest.TestCase):

    def setUp(self):
        self.scraper = scrape.GameScraper(seconds_between_requests=0)
        with open(os.path.join(basedir, 'cle_2016_schedule.html')) as f:
            self.html = f.read()

    def test_parse_url(self):
        self.assertEqual(scrape.parse_url("http://www.basketball-reference.com/teams/CLE/2016.html"),
            ('CLE', 2016))
        self.assertEqual(scrape.parse_url("http://www.basketball-reference.com/teams/GSW/2015.html"),
            ('GSW', 2015))

    def test_parse_row_from_table(self):
        raw_html = """<tr data-row="1"><th scope="row" class="right " data-stat="g">2</th><td class="left " data-stat="date_game" csk="2015-10-28"><a href="/boxscores/index.cgi?month=10&amp;day=28&amp;year=2015">Wed, Oct 28, 2015</a></td><td class=" " data-stat="game_start_time">8:00p <span style="font-size:7px;vertical-align:baseline;">EST</span></td><td class=" " data-stat="network"></td><td class="center " data-stat="box_score_text"><a href="/boxscores/201510280MEM.html">Box Score</a></td><td class="center " data-stat="game_location">@</td><td class="left " data-stat="opp_name" csk="MEM2015-10-28"><a href="/teams/MEM/2016.html">Memphis Grizzlies</a></td><td class="center " data-stat="game_result">W</td><td class="center " data-stat="overtimes"></td><td class="right " data-stat="pts">106</td><td class="right " data-stat="opp_pts">76</td><td class="right " data-stat="wins">1</td><td class="right " data-stat="losses">1</td><td class="left " data-stat="game_streak">W 1</td><td class="left " data-stat="game_remarks"></td></tr>"""
        game = scrape.parse_game(bs4.BeautifulSoup(raw_html, 'lxml'))
        dt = datetime.datetime(2015, 10, 28, 20, 0,tzinfo=pytz.timezone('US/Eastern'))

        self.assertEqual(game.date, dt)
        self.assertEqual(game.is_home_game, False)
        self.assertEqual(game.opponent, 'Memphis Grizzlies')
        self.assertEqual(game.points, 106)
        self.assertEqual(game.opponent_points, 76)
        self.assertEqual(game.opponent_symbol, 'MEM')

    def test_get_additional_links_to_crawl(self):
        links = scrape.get_additional_links(self.html)

        self.assertEqual(len(links), 29)
        self.assertIn('/teams/ATL/2016.html', links)
        self.assertIn('/teams/GSW/2016.html', links)
        self.assertIn('/teams/WAS/2016.html', links)

    def test_parse_schedule(self):
        games = scrape.parse_schedule(self.html)
        # verify 82 games in the Cavs schedule, 41 of those are home games,
        # and that 57 are those are wins
        self.assertEqual(len(games), 82)
        self.assertEqual(len([g for g in games if g.is_home_game]), 41)
        self.assertEqual(len([g for g in games if g.points > g.opponent_points]), 57)

    @mock.patch('nbaelo.scrape.requests')
    def test_fetch_schedule_called_with_correct_url(self, mock_requests):
        self.scraper.fetch_schedule(2016, 'CLE')
        mock_requests.get.assert_called_with("http://www.basketball-reference.com/teams/CLE/2016_games.html")

    @mock.patch('nbaelo.scrape.parse_schedule')
    @mock.patch('nbaelo.scrape.get_additional_links')
    @mock.patch.object(scrape.GameScraper, 'fetch_schedule')
    def test_scrape_crawls_all_links(self,  mock_fetch_schedule, mock_get_additional_links,
        mock_parse_schedule):
        mock_get_additional_links.return_value = ['/teams/ATL/2016.html', '/teams/GSW/2016.html']

        teams = self.scraper.scrape(2016, 'LAL')

        expected_calls = [
            mock.call(2016, 'LAL'),
            mock.call(2016, 'ATL'),
            mock.call(2016, 'GSW')
        ]

        mock_fetch_schedule.assert_has_calls(expected_calls, any_order=False)

        self.assertEqual(set(teams.keys()), set(['GSW', 'LAL', 'ATL']))


if __name__ == '__main__':
    unittest.main()