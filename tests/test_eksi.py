import unittest
from typing import Generator

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
        chunk = self.eksi.get_entries(url)

        self.assertIsInstance(chunk, Generator)
        self.assertIsInstance(next(chunk), tuple)

        entry = next(chunk)
        for val in entry:
            self.assertIsInstance(val, str)
