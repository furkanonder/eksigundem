import gzip
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from bs4 import BeautifulSoup as Soup

from eksi import client
from eksi import pager as pager_mod
from eksi.client import EksiError
from eksi.eksi import Eksi
from eksi.pager import Pager, TopicSelector

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


class TestClient(unittest.TestCase):
    @patch("eksi.client.urlopen")
    @patch("eksi.client.Request")
    def test_get_soup_success(self, mock_request, mock_urlopen):
        """Should fetch URL and return BeautifulSoup object."""
        mock_response = Mock()
        mock_response.read.return_value = b"<html><body>Test</body></html>"
        mock_response.headers = {"Content-Encoding": ""}
        mock_urlopen.return_value = mock_response

        result = client.get_soup("http://test.com")
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
            client.get_soup("http://test.com")
        assert f"{ctx.exception}" == "Sayfa bulunamadı!"

    @patch("eksi.client.urlopen")
    def test_get_soup_403_error(self, mock_urlopen):
        """Should raise EksiError with 'access denied' message on 403."""
        mock_urlopen.side_effect = HTTPError(None, 403, "Forbidden", None, None)
        with self.assertRaises(EksiError) as ctx:
            client.get_soup("http://test.com")
        assert f"{ctx.exception}" == "Erişim engellendi!"

    @patch("eksi.client.urlopen")
    def test_get_soup_500_error(self, mock_urlopen):
        """Should raise EksiError with a 'server error' message on 5xx."""
        mock_urlopen.side_effect = HTTPError(None, 500, "Internal Server Error", None, None)
        with self.assertRaises(EksiError) as ctx:
            client.get_soup("http://test.com")
        assert f"{ctx.exception}" == "Sunucu hatası! Lütfen daha sonra tekrar deneyin."

    @patch("eksi.client.urlopen")
    def test_get_soup_url_error(self, mock_urlopen):
        """Should raise EksiError with 'no internet' message on DNS failure."""
        mock_urlopen.side_effect = URLError("name resolution failed")
        with self.assertRaises(EksiError) as ctx:
            client.get_soup("http://test.com")
        assert "Internet bağlantısı yok!" in f"{ctx.exception}"

    @patch("eksi.client.urlopen")
    def test_get_soup_generic_url_error(self, mock_urlopen):
        """Should raise EksiError with 'connection error' message on other URLError."""
        mock_urlopen.side_effect = URLError("Connection refused")
        with self.assertRaises(EksiError) as ctx:
            client.get_soup("http://test.com")
        assert "Bağlantı hatası:" in f"{ctx.exception}"

    def test_get_topic_page(self):
        """Should parse HTML fixture into (content, author, date) tuples."""
        html = load_fixture("entry_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(client, "get_soup", return_value=real_soup):
            entries_iter, more_data_href, more_data_count, current_page, page_count = client.get_topic_page(
                "/test-topic--1",
            )
            entries = list(entries_iter)
            assert len(entries) == 2
            assert isinstance(entries[0], tuple)
            assert entries[0] == ("Test entry content", "author1", "01.01.2026 10:00")
            assert more_data_href == ""
            assert more_data_count == 0
            assert current_page == 1
            assert page_count == 5

    def test_get_topics(self):
        """Should parse topic list HTML into (title, href) tuples."""
        html = load_fixture("topic_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(client, "get_soup", return_value=real_soup):
            topics = client.get_topics(3)
            assert len(topics) == 3
            assert topics[0] == ("Topic 1 5", "/topic1--123?a=popular")

    def test_get_topics_paginates(self):
        """Should fetch multiple pages when count exceeds a single page."""
        page1 = Soup(load_fixture("topic_list_page1.html"), "html.parser")
        page2 = Soup(load_fixture("topic_list_page2.html"), "html.parser")

        with patch.object(client, "get_soup", side_effect=[page1, page2]) as mock_soup:
            topics = client.get_topics(5)
            assert len(topics) == 5
            assert topics[0] == ("Topic 1 10", "/topic1--1?a=popular")
            assert topics[4] == ("Topic 5 50", "/topic5--5?a=popular")
            assert mock_soup.call_count == 2

    def test_get_topics_stops_at_requested_count(self):
        """Should stop paginating once count is reached even if more pages exist."""
        page1 = Soup(load_fixture("topic_list_page1.html"), "html.parser")

        with patch.object(client, "get_soup", return_value=page1) as mock_soup:
            topics = client.get_topics(2)
            assert len(topics) == 2
            assert mock_soup.call_count == 1

    def test_get_topics_returns_less_when_site_has_fewer(self):
        """Should return all available topics when site has fewer than requested."""
        html = load_fixture("topic_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(client, "get_soup", return_value=real_soup):
            topics = client.get_topics(100)
            assert len(topics) == 3

    def test_preserves_query_on_initial_load(self):
        """Default page (0) should use the original URL (preserving ?a=popular)."""
        html = load_fixture("entry_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(client, "get_soup", return_value=real_soup) as mock_soup:
            client.get_topic_page("/topic--123?a=popular")
            fetched_url = mock_soup.call_args[0][0]
            assert "?a=popular" in fetched_url

    def test_strips_query_on_explicit_page(self):
        """Explicit page number should strip query params and use ?p=N."""
        html = load_fixture("entry_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(client, "get_soup", return_value=real_soup) as mock_soup:
            client.get_topic_page("/topic--123?a=popular", page=1)
            fetched_url = mock_soup.call_args[0][0]
            assert "?a=popular" not in fetched_url
            assert "?p=1" in fetched_url

    def test_detects_more_data_link(self):
        """When a 'more-data' link precedes the entry list, return the count and href."""
        html = load_fixture("entry_more_data.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(client, "get_soup", return_value=real_soup):
            entries_iter, more_data_href, more_data_count, current, total = client.get_topic_page(
                "/test--1?a=popular",
            )
            entries = list(entries_iter)
            assert more_data_count == 2
            assert "focusto" in more_data_href
            assert current == 1
            assert total == 32
            # Only visible entries returned (more-data not fetched yet)
            assert len(entries) == 1
            assert entries[0][1] == "author3"

    def test_url_links_replaced_with_href(self):
        """External URL links (a.url) should be replaced with their href text."""
        html = load_fixture("entry_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(client, "get_soup", return_value=real_soup):
            entries_iter, *_ = client.get_topic_page("/test-topic--1")
            entries = list(entries_iter)
            # The second entry has a.url link - should show the URL in text
            assert "https://example.com/test" in entries[1][0]
            # bkz link text should remain as-is (not replaced with href)
            assert "/?q=link" not in entries[1][0]

    @patch("eksi.client.urlopen")
    @patch("eksi.client.Request")
    def test_get_soup_gzip(self, _mock_request, mock_urlopen):
        """Should decompress gzip-encoded responses."""
        body = gzip.compress(b"<html><body>Compressed</body></html>")
        mock_response = Mock()
        mock_response.read.return_value = body
        mock_response.headers = {"Content-Encoding": "gzip"}
        mock_urlopen.return_value = mock_response

        result = client.get_soup("http://test.com")
        assert "Compressed" in result.text

    @patch("eksi.client.urlopen")
    def test_get_soup_generic_http_error(self, mock_urlopen):
        """Should raise EksiError with HTTP code on unhandled status codes."""
        mock_urlopen.side_effect = HTTPError(None, 429, "Too Many Requests", None, None)
        with self.assertRaises(EksiError) as ctx:
            client.get_soup("http://test.com")
        assert "429" in f"{ctx.exception}"

    def test_parse_entry_empty_content(self):
        """Should skip entries with whitespace-only content."""
        html = """<li data-id="1"><div class="content">   </div>
            <a class="entry-author">a</a><a class="entry-date">d</a></li>"""
        entry = Soup(html, "html.parser").select_one("li")
        assert list(client._parse_entry(entry)) == []

    def test_pager_info_from_fixture(self):
        """Pager div should provide current_page and page_count."""
        html = load_fixture("entry_more_data.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(client, "get_soup", return_value=real_soup):
            _, _, _, current_page, page_count = client.get_topic_page("/test--1?a=popular")
            assert current_page == 1
            assert page_count == 32


@patch("sys.stdout")
class TestPager(unittest.TestCase):
    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 50)))
    @patch("eksi.pager.terminal.getchar", return_value="g")
    def test_short_content(self, mock_getchar, _mock_size, _mock_stdout):
        """Short content still enters the pager, any key exits."""
        pager = Pager(lines=[f"line {i}" for i in range(10)])
        pager.run()
        mock_getchar.assert_called_once()

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 6)))
    @patch("eksi.pager.terminal.getchar", side_effect=[" ", " ", "g"])
    def test_with_pause(self, mock_getchar, _mock_size, _mock_stdout):
        """Content exceeds terminal - Space scrolls, non-scroll key exits."""
        pager = Pager(lines=[f"line {i}" for i in range(12)])
        result = pager.run()
        assert mock_getchar.call_count == 3
        assert result == "g"

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 6)))
    @patch("eksi.pager.terminal.getchar", side_effect=[" ", "s"])
    def test_returns_exit_key(self, mock_getchar, _mock_size, _mock_stdout):
        """Pager returns the key that caused exit."""
        pager = Pager(lines=[f"line {i}" for i in range(12)])
        result = pager.run()
        assert mock_getchar.call_count == 2
        assert result == "s"

    def test_load_entries(self, _mock_stdout):
        """Should fetch entries and return formatted lines."""
        html = load_fixture("entry_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(client, "get_soup", return_value=real_soup):
            lines, current_page, page_count = pager_mod._load_entries("Test Topic", "test-topic")
            assert isinstance(lines, list)
            assert len(lines) > 0
            assert current_page == 1
            assert page_count == 5

    @patch("eksi.pager.client.get_topic_page", return_value=([], "", 0, 1, 1))
    def test_load_entries_delegates_to_client(self, mock_page, _mock_stdout):
        """Should pass topic URL and page number to client.get_topic_page."""
        pager_mod._load_entries("Test", "/topic--123?a=popular", page_num=2)
        mock_page.assert_called_once_with("/topic--123?a=popular", 2)

    def test_get_page_first_page_warning(self, _mock_stdout):
        """Page num 0 clamps to 1 and sets a warning."""
        with (
            patch.object(pager_mod, "_load_entries", return_value=(["line"], 1, 10)) as mock_load,
            patch.object(Pager, "run", return_value="g"),
        ):
            cmd, page_num, page_count = Pager._get_page("title", "/url", 0, 10)
            mock_load.assert_called_once_with("title", "/url", 1)
            assert page_num == 1
            assert page_count == 10
            assert cmd == "g"

    def test_get_page_last_page_warning(self, _mock_stdout):
        """Past last page clamps to page_count and sets warning."""
        with (
            patch.object(pager_mod, "_load_entries", return_value=(["line"], 4, 4)) as mock_load,
            patch.object(Pager, "run", return_value="g"),
        ):
            cmd, page_num, page_count = Pager._get_page("title", "/url", 5, 4)
            mock_load.assert_called_once_with("title", "/url", 4)
            assert page_num == 4
            assert page_count == 4
            assert cmd == "g"

    @patch("eksi.pager.terminal.getchar", return_value="e")
    @patch("eksi.pager.client.get_topic_page")
    def test_load_entries_more_data_yes(self, mock_page, _mock_getchar, _mock_stdout):
        """When more-data entries exist and the user presses 'e', reload from focusto URL."""
        mock_page.side_effect = [
            ([("visible", "a1", "d1")], "/t--1?focusto=100", 5, 1, 10),
            ([("more", "a2", "d2")], "", 0, 3, 30),
        ]
        _lines, current_page, page_count = pager_mod._load_entries("T", "/t--1?a=popular")
        assert mock_page.call_count == 2
        mock_page.assert_any_call("/t--1?a=popular", 0)
        mock_page.assert_any_call("/t--1?focusto=100")
        assert current_page == 3
        assert page_count == 30

    @patch("eksi.pager.terminal.getchar", return_value="h")
    @patch("eksi.pager.client.get_topic_page", return_value=([("visible", "a1", "d1")], "/t?focusto=1", 5, 1, 10))
    def test_load_entries_more_data_no(self, mock_page, _mock_getchar, _mock_stdout):
        """When more-data entries exist and the user presses 'h', keep visible entries."""
        _lines, current_page, page_count = pager_mod._load_entries("T", "/t?a=popular")
        assert mock_page.call_count == 1
        assert current_page == 1
        assert page_count == 10

    def test_enter_topic_first_page(self, _mock_stdout):
        """Pressing 'i' should navigate to page 1."""
        with (
            patch.object(pager_mod, "_load_entries", return_value=(["line"], 5, 10)) as mock_load,
            patch.object(Pager, "run", side_effect=["i", "g"]),
        ):
            Pager.enter_topic("title", "/url")
            assert mock_load.call_count == 2
            mock_load.assert_any_call("title", "/url", 1)

    def test_enter_topic_last_page(self, _mock_stdout):
        """Pressing 'e' should navigate to the last page."""
        with (
            patch.object(pager_mod, "_load_entries", return_value=(["line"], 5, 10)) as mock_load,
            patch.object(Pager, "run", side_effect=["e", "g"]),
        ):
            Pager.enter_topic("title", "/url")
            assert mock_load.call_count == 2
            mock_load.assert_any_call("title", "/url", 10)

    @patch("eksi.pager.terminal.getchar", return_value="h")
    @patch("eksi.pager.client.get_topic_page", return_value=([("v", "a", "d")], "/t?focusto=1", 5, 1, 10))
    def test_more_data_prompt_only_on_initial_load(self, mock_page, _mock_getchar, _mock_stdout):
        """More-data prompt should only appear on an initial load (page_num=0), not on pagination."""
        # page_num=2 simulates pagination — should NOT prompt even though more_data_count > 0
        _lines, current_page, _page_count = pager_mod._load_entries("T", "/t?a=popular", page_num=2)
        assert mock_page.call_count == 1
        assert current_page == 1

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 10)))
    def test_scroll_arrow_up(self, _mock_size, _mock_stdout):
        """Arrow up should scroll up by one line."""
        pager = Pager(lines=[f"line {i}" for i in range(20)])
        pager.scroll_pos = 5
        with patch("eksi.pager.terminal.getchar", side_effect=["[", "A"]):
            pager._compute_scroll("\x1b")
        assert pager.scroll_pos == 4

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 10)))
    def test_scroll_home_end(self, _mock_size, _mock_stdout):
        """Home should go to start, End to max scroll."""
        pager = Pager(lines=[f"line {i}" for i in range(30)])
        pager.scroll_pos = 10
        with patch("eksi.pager.terminal.getchar", side_effect=["[", "H"]):
            pager._compute_scroll("\x1b")
        assert pager.scroll_pos == 0
        with patch("eksi.pager.terminal.getchar", side_effect=["[", "F"]):
            pager._compute_scroll("\x1b")
        assert pager.scroll_pos == pager.max_scroll

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 10)))
    def test_scroll_pgup_pgdn(self, _mock_size, _mock_stdout):
        """PgUp/PgDn should scroll by page_size."""
        pager = Pager(lines=[f"line {i}" for i in range(50)])
        with patch("eksi.pager.terminal.getchar", side_effect=["[", "6", "~"]):
            pager._compute_scroll("\x1b")
        assert pager.scroll_pos == pager.page_size
        with patch("eksi.pager.terminal.getchar", side_effect=["[", "5", "~"]):
            pager._compute_scroll("\x1b")
        assert pager.scroll_pos == 0


@patch("sys.stdout")
class TestTopicSelector(unittest.TestCase):
    TOPICS = [("Topic 5", "/topic")] * 5

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 50)))
    @patch("eksi.pager.terminal.getchar", side_effect=["1", "\x7f", "2", "\n"])
    def test_backspace(self, _mock_getchar, _mock_size, _mock_stdout):
        """Backspace should delete the last digit from the buffer."""
        title, url = TopicSelector(self.TOPICS).run()
        assert title == "Topic 5"
        assert url == "/topic"

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 50)))
    def test_single_word_title(self, _mock_size, _mock_stdout):
        """Single-word titles without a count should not crash."""
        selector = TopicSelector([("test", "/t")])
        assert len(selector.lines) == 1
        assert "test" in selector.lines[0]

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 50)))
    @patch("eksi.pager.terminal.getchar", side_effect=["1", "\n"])
    def test_select(self, _mock_getchar, _mock_size, _mock_stdout):
        """Digit + enter selects a topic."""
        title, url = TopicSelector(self.TOPICS).run()
        assert title == "Topic 5"
        assert url == "/topic"

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 50)))
    @patch("eksi.pager.terminal.getchar", side_effect=["9", "\n", "1", "\n"])
    def test_invalid_then_valid(self, _mock_getchar, _mock_size, _mock_stdout):
        """Invalid index clears the buffer, user can then enter a valid one."""
        title, url = TopicSelector(self.TOPICS).run()
        assert title == "Topic 5"
        assert url == "/topic"

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 50)))
    @patch("eksi.pager.terminal.getchar", side_effect=["\x1b", "[", "B", "1", "\n"])
    def test_scroll_then_select(self, _mock_getchar, _mock_size, _mock_stdout):
        """Arrow down scrolls a topic list, then digit+enter selects a topic."""
        title, url = TopicSelector(self.TOPICS).run()
        assert title == "Topic 5"
        assert url == "/topic"

    @patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 50)))
    def test_build_lines(self, _mock_size, _mock_stdout):
        """Should format topics into colored lines."""
        selector = TopicSelector([("Topic 1 5", "/topic1"), ("Topic 2 10", "/topic2")])
        assert len(selector.lines) == 2
        assert "Topic 1" in selector.lines[0]
        assert "Topic 2" in selector.lines[1]


@patch("sys.stdout")
class TestEksi(unittest.TestCase):
    def setUp(self):
        self.eksi = Eksi(topic_count=10)

    @patch("eksi.eksi.client.get_topics")
    def test_fetch_topics(self, mock_topics, _mock_stdout):
        """Should fetch topics and populate self.topics."""
        topics = [("Topic 1 5", "/topic1--123?a=popular"), ("Topic 2 10", "/topic2")]
        mock_topics.return_value = topics
        self.eksi._fetch_topics()
        assert self.eksi.topics == topics

    @patch("eksi.eksi.TopicSelector")
    @patch("eksi.eksi.Pager.enter_topic")
    def test_prompt_select(self, mock_enter, mock_selector_cls, _mock_stdout):
        """Prompt selects a topic and enters the topic view."""
        mock_selector_cls.return_value.run.return_value = ("Topic 5", "/topic")
        self.eksi.topics = [("Topic 5", "/topic")] * 5
        mock_enter.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.eksi.prompt()
        mock_enter.assert_called_once_with("Topic 5", "/topic")

    @patch("eksi.eksi.TopicSelector")
    def test_prompt_exit(self, mock_selector_cls, _mock_stdout):
        """Prompt exits on Ctrl+C."""
        mock_selector_cls.return_value.run.side_effect = KeyboardInterrupt
        self.eksi.topics = [("t 1", "/t")] * 5
        with self.assertRaises(KeyboardInterrupt):
            self.eksi.prompt()

    @patch("eksi.eksi.TopicSelector")
    @patch("eksi.eksi.Pager.enter_topic")
    @patch.object(Eksi, "_fetch_topics")
    def test_prompt_returns_to_topic_list(self, _mock_fetch, mock_enter, mock_selector_cls, _mock_stdout):
        """After entering a topic and returning, the user can select another topic."""
        mock_selector_cls.return_value.run.side_effect = [
            ("Topic A 5", "/a"),
            ("Topic B 10", "/b"),
            KeyboardInterrupt,
        ]
        self.eksi.topics = [("Topic A 5", "/a"), ("Topic B 10", "/b")]
        with self.assertRaises(KeyboardInterrupt):
            self.eksi.prompt()
        assert mock_enter.call_count == 2
        mock_enter.assert_any_call("Topic A 5", "/a")
        mock_enter.assert_any_call("Topic B 10", "/b")
