from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from bs4 import BeautifulSoup as Soup

from eksi.eksi import BASE_URL, Eksi, EksiError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


class TestEksiClass(unittest.TestCase):
    def setUp(self):
        self.eksi = Eksi(topic_count=10)

    def test_init(self):
        eksi = Eksi(topic_count=5)
        # Verify instance attributes
        assert eksi.topic_count == 5
        assert eksi.page_num == 1
        assert eksi.topic_title == ""
        assert eksi.topic_url == ""
        assert eksi.topics == []
        # Verify module constant
        assert BASE_URL == "https://eksisozluk.com/"

    @patch("os.name", "nt")
    @patch("os.system")
    def test_clear_screen_windows(self, mock_system):
        Eksi.clear_screen()
        mock_system.assert_called_once_with("cls")

    @patch("os.name", "posix")
    @patch("os.system")
    def test_clear_screen_unix(self, mock_system):
        Eksi.clear_screen()
        mock_system.assert_called_once_with(r'printf "\e[2J\e[3J\e[H"')

    @patch("eksi.eksi.urlopen")
    @patch("eksi.eksi.Request")
    def test_get_soup_success(self, mock_request, mock_urlopen):
        """Should fetch URL and return BeautifulSoup object."""
        mock_response = Mock()
        mock_response.read.return_value = b"<html><body>Test</body></html>"
        mock_response.headers = {"Content-Encoding": ""}
        mock_urlopen.return_value = mock_response

        result = Eksi.get_soup("http://test.com")
        assert isinstance(result, Soup)

        # Verify Request called with browser-like headers
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "http://test.com"
        assert "User-Agent" in call_args[1]["headers"]
        assert "Firefox" in call_args[1]["headers"]["User-Agent"]

        mock_urlopen.assert_called_once()

    @patch("eksi.eksi.urlopen")
    def test_get_soup_404_error(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(None, 404, "Not Found", None, None)

        with self.assertRaises(EksiError) as context:
            Eksi.get_soup("http://test.com")

        assert f"{context.exception}" == "Sayfa bulunamadı!"

    @patch("eksi.eksi.urlopen")
    def test_get_soup_403_error(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(None, 403, "Forbidden", None, None)

        with self.assertRaises(EksiError) as context:
            Eksi.get_soup("http://test.com")

        assert f"{context.exception}" == "Erişim engellendi!"

    @patch("eksi.eksi.urlopen")
    def test_get_soup_500_error(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(None, 500, "Internal Server Error", None, None)

        with self.assertRaises(EksiError) as context:
            Eksi.get_soup("http://test.com")

        assert f"{context.exception}" == "Sunucu hatası! Lütfen daha sonra tekrar deneyin."

    @patch("eksi.eksi.urlopen")
    def test_get_soup_url_error(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("name resolution failed")

        with self.assertRaises(EksiError) as context:
            Eksi.get_soup("http://test.com")

        assert "Internet bağlantısı yok!" in f"{context.exception}"

    @patch("eksi.eksi.urlopen")
    def test_get_soup_generic_url_error(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Connection refused")

        with self.assertRaises(EksiError) as context:
            Eksi.get_soup("http://test.com")

        assert "Bağlantı hatası:" in f"{context.exception}"

    def test_get_entries(self):
        html = load_fixture("entry_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(self.eksi, "get_soup") as mock_get_soup:
            mock_get_soup.return_value = real_soup
            entries = list(self.eksi.get_entries("http://test.com"))

            # Verify entries parsed
            assert len(entries) == 2
            assert isinstance(entries[0], tuple)

            first_entry = entries[0]
            assert first_entry[0] == "Test entry content"
            assert first_entry[1] == "author1"
            assert first_entry[2] == "01.01.2026 10:00"

    @patch("builtins.print")
    @patch.object(Eksi, "clear_screen")
    def test_reader(self, mock_clear, mock_print):
        html = load_fixture("entry_list.html")
        self.eksi.topic_title = "Test Topic"
        self.eksi.topic_url = "test-topic"
        real_soup = Soup(html, "html.parser")

        with patch.object(self.eksi, "get_soup") as mock_get_soup:
            mock_get_soup.return_value = real_soup
            self.eksi.reader()
            # Verify screen cleared and entries printed
            mock_clear.assert_called_once()
            assert mock_print.called

    def test_handle_topic_selection_valid(self):
        self.eksi.topics = [("Topic 1", "topic-1"), ("Topic 2", "topic-2")]

        with patch.object(self.eksi, "reader") as mock_reader:
            self.eksi.handle_topic_selection("1")
            # Verify topic set correctly
            assert self.eksi.topic_title == "Topic 1"
            assert self.eksi.topic_url == "topic-1"
            mock_reader.assert_called_once()

    @patch("builtins.print")
    def test_handle_topic_selection_invalid_number(self, mock_print):
        self.eksi.topics = [("Topic 1", "topic-1")]
        self.eksi.handle_topic_selection("5")

        mock_print.assert_called()
        assert "Geçersiz girdi!" in mock_print.call_args[0][0]

    @patch("builtins.print")
    def test_handle_topic_selection_invalid_input(self, mock_print):
        self.eksi.topics = [("Topic 1", "topic-1")]
        self.eksi.handle_topic_selection("abc")

        mock_print.assert_called()
        assert "Geçersiz girdi!" in mock_print.call_args[0][0]

    @patch("builtins.print")
    @patch.object(Eksi, "clear_screen")
    def test_display_topics(self, mock_clear, mock_print):
        html = load_fixture("topic_list.html")
        real_soup = Soup(html, "html.parser")

        with patch.object(self.eksi, "get_soup") as mock_get_soup, patch.object(self.eksi, "prompt") as mock_prompt:
            mock_get_soup.return_value = real_soup
            self.eksi.display_topics()

            # Verify screen cleared and topics printed
            mock_clear.assert_called_once()
            assert mock_print.called
            mock_prompt.assert_called_once()
            # Verify topics parsed correctly
            assert len(self.eksi.topics) == 3
            assert self.eksi.topics[0] == ("Topic 1 5", "/topic1--123?a=popular")

    def test_get_page_first_page_warning(self):
        self.eksi.page_num = 0

        with patch.object(self.eksi, "reader") as mock_reader, patch("builtins.print") as mock_print:
            self.eksi.get_page()
            # Verify reader called with page 0
            mock_reader.assert_called_once_with(0)
            # Verify warning shown and page reset to 1
            mock_print.assert_called()
            assert "Şu an ilk sayfadasınız!" in mock_print.call_args[0][0]
            assert self.eksi.page_num == 1

    def test_get_page_last_page_warning(self):
        self.eksi.page_num = 5

        with patch.object(self.eksi, "reader") as mock_reader, patch("builtins.print") as mock_print:
            # First call fails, second succeeds
            mock_reader.side_effect = [EksiError("Sayfa bulunamadı"), None]
            self.eksi.get_page()
            # Verify reader called with page 5 (fail) then page 4 (success)
            assert mock_reader.call_count == 2
            mock_reader.assert_any_call(5)
            mock_reader.assert_any_call(4)
            # Verify warning shown and page decremented
            mock_print.assert_called()
            assert "en son sayfadasınız" in mock_print.call_args[0][0]
            assert self.eksi.page_num == 4
