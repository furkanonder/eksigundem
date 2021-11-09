import unittest
from typing import Generator, List

from bs4 import BeautifulSoup as Soup

from eksi.eksi import Eksi


class TestEksi(unittest.TestCase):
    def setUp(self):
        self.base_url = "https://eksisozluk.com/"
        self.eksi = Eksi()

    def test_get_soup(self):
        soup_obj = self.eksi.get_soup(self.base_url)
        self.assertIsInstance(soup_obj, Soup)

    def test_parser(self):
        url = self.base_url + "eksi"
        chunk = self.eksi.parser(url)

        self.assertIsInstance(chunk, Generator)
        self.assertIsInstance(next(chunk), List)
