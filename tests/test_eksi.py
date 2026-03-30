import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from bs4 import BeautifulSoup as Soup

from eksi.client import EksiClient, EksiError
from eksi.eksi import Eksi, Pager

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


class TestEksiClient(unittest.TestCase):
    @patch("eksi.client.urlopen")
    @patch("eksi.client.Request")
    def test_get_soup_success(self, mock_request, mock_urlopen):
        """Should fetch URL and return BeautifulSoup object."""
        mock_response = Mock()
        mock_response.read.return_value = b"<html><body>Test</body></html>"
        mock_response.headers = {"Content-Encoding": ""}
        mock_urlopen.return_value = mock_response

        result = EksiClient.get_soup("http://test.com")
        assert isinstance(result, Soup)

        # Verify Request called with browser-like headers
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "http://test.com"
        assert "User-Agent" in call_args[1]["headers"]
        assert "Firefox" in call_args[1]["headers"]["User-Agent"]

        mock_urlopen.assert_called_once()

    @patch("eksi.client.urlopen")
    def test_get_soup_404_error(self, mock_urlopen):
        """Should raise EksiError with 'page not found' message on 404."""
        mock_urlopen.side_effect = HTTPError(None, 404, "Not Found", None, None)
        with self.assertRaises(EksiError) as ctx:
            EksiClient.get_soup("http://test.com")
        assert f"{ctx.exception}" == "Sayfa bulunamadı!"

    @patch("eksi.client.urlopen")
    def test_get_soup_403_error(self, mock_urlopen):
        """Should raise EksiError with 'access denied' message on 403."""
        mock_urlopen.side_effect = HTTPError(None, 403, "Forbidden", None, None)
        with self.assertRaises(EksiError) as ctx:
            EksiClient.get_soup("http://test.com")
        assert f"{ctx.exception}" == "Erişim engellendi!"

    @patch("eksi.client.urlopen")
    def test_get_soup_500_error(self, mock_urlopen):
        """Should raise EksiError with a 'server error' message on 5xx."""
        mock_urlopen.side_effect = HTTPError(None, 500, "Internal Server Error", None, None)
        with self.assertRaises(EksiError) as ctx:
            EksiClient.get_soup("http://test.com")
        assert f"{ctx.exception}" == "Sunucu hatası! Lütfen daha sonra tekrar deneyin."

    @patch("eksi.client.urlopen")
    def test_get_soup_url_error(self, mock_urlopen):
        """Should raise EksiError with 'no internet' message on DNS failure."""
        mock_urlopen.side_effect = URLError("name resolution failed")
        with self.assertRaises(EksiError) as ctx:
            EksiClient.get_soup("http://test.com")
        assert "Internet bağlantısı yok!" in f"{ctx.exception}"

    @patch("eksi.client.urlopen")
    def test_get_soup_generic_url_error(self, mock_urlopen):
        """Should raise EksiError with 'connection error' message on other URLError."""
        mock_urlopen.side_effect = URLError("Connection refused")
        with self.assertRaises(EksiError) as ctx:
            EksiClient.get_soup("http://test.com")
        assert "Bağlantı hatası:" in f"{ctx.exception}"

    def test_get_entries(self):
        """Should parse HTML fixture into (content, author, date) tuples."""
        html = load_fixture("entry_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(EksiClient, "get_soup", return_value=real_soup):
            entries = list(EksiClient.get_entries("http://test.com"))
            assert len(entries) == 2
            assert isinstance(entries[0], tuple)
            assert entries[0] == ("Test entry content", "author1", "01.01.2026 10:00")

    def test_get_topics(self):
        """Should parse topic list HTML into (title, href) tuples."""
        html = load_fixture("topic_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(EksiClient, "get_soup", return_value=real_soup):
            topics = EksiClient.get_topics("http://test.com", 3)
            assert len(topics) == 3
            assert topics[0] == ("Topic 1 5", "/topic1--123?a=popular")


class TestPager(unittest.TestCase):
    @patch("sys.stdout")
    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 50)))
    @patch("eksi.eksi.getchar", return_value="g")
    def test_short_content(self, mock_getchar, _mock_size, _mock_stdout):
        """Short content still enters the pager, any key exits."""
        pager = Pager(lines=[f"line {i}" for i in range(10)])
        pager.run()
        mock_getchar.assert_called_once()

    @patch("sys.stdout")
    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 6)))
    @patch("eksi.eksi.getchar", side_effect=[" ", " ", "g"])
    def test_with_pause(self, mock_getchar, _mock_size, _mock_stdout):
        """Content exceeds terminal - Space scrolls, non-scroll key exits."""
        pager = Pager(lines=[f"line {i}" for i in range(12)])
        result = pager.run()
        assert mock_getchar.call_count == 3
        assert result == "g"

    @patch("sys.stdout")
    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 6)))
    @patch("eksi.eksi.getchar", side_effect=[" ", "s"])
    def test_returns_exit_key(self, mock_getchar, _mock_size, _mock_stdout):
        """Pager returns the key that caused exit."""
        pager = Pager(lines=[f"line {i}" for i in range(12)])
        result = pager.run()
        assert mock_getchar.call_count == 2
        assert result == "s"


class TestEksi(unittest.TestCase):
    def setUp(self):
        self.eksi = Eksi(topic_count=10)

    @patch("sys.stdout")
    def test_load_entries(self, _mock_stdout):
        """Should fetch entries and return formatted lines."""
        html = load_fixture("entry_list.html")
        real_soup = Soup(html, "html.parser")
        self.eksi.topic_title = "Test Topic"
        self.eksi.topic_url = "test-topic"

        with patch.object(EksiClient, "get_soup", return_value=real_soup):
            lines = self.eksi._load_entries()
            assert isinstance(lines, list)
            assert len(lines) > 0

    def test_get_page_first_page_warning(self):
        """Page num 0 clamps to 1 and sets a warning."""
        self.eksi.page_num = 0
        with (
            patch.object(self.eksi, "_load_entries", return_value=["line"]) as mock_load,
            patch.object(Pager, "run", return_value="g"),
        ):
            result = self.eksi._get_page()
            mock_load.assert_called_once_with(1)
            assert self.eksi.page_num == 1
            assert result == "g"

    def test_get_page_last_page_warning(self):
        """Past last page falls back to previous page and sets warning."""
        self.eksi.page_num = 5
        with (
            patch.object(self.eksi, "_load_entries") as mock_load,
            patch.object(Pager, "run", return_value="g"),
        ):
            mock_load.side_effect = [EksiError("Sayfa bulunamadı"), ["line"]]
            result = self.eksi._get_page()
            assert mock_load.call_count == 2
            mock_load.assert_any_call(5)
            mock_load.assert_any_call(4)
            assert self.eksi.page_num == 4
            assert result == "g"

    @patch("sys.stdout")
    def test_display_topics(self, _mock_stdout):
        """Should fetch topics and populate self.topics."""
        topics = [("Topic 1 5", "/topic1--123?a=popular"), ("Topic 2 10", "/topic2")]
        with patch.object(EksiClient, "get_topics", return_value=topics):
            self.eksi.display_topics()
            assert self.eksi.topics == topics

    @patch("builtins.input", side_effect=["1", EOFError])
    @patch.object(Eksi, "_enter_topic")
    def test_prompt_select(self, mock_enter, _mock_input):
        """Prompt selects a topic and enters the topic view."""
        self.eksi.topics = [("Topic", "/topic")] * 5
        with self.assertRaises(EOFError):
            self.eksi.prompt()
        assert self.eksi.topic_title == "Topic"
        mock_enter.assert_called_once()

    @patch("builtins.input", return_value="c")
    def test_prompt_exit(self, _mock_input):
        """Prompt exits on 'c'."""
        self.eksi.topics = [("t", "/t")] * 5
        with self.assertRaises(SystemExit):
            self.eksi.prompt()
