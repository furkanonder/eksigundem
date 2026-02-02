from collections.abc import Iterator
import gzip
import os
import sys
from textwrap import fill
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup as Soup

from eksi.color import BLUE, CYAN, GREEN, MAGENTA, RED, WHITE, YELLOW, set_color

BASE_URL: Final = "https://eksisozluk.com/"

# CSS Selectors
ENTRY_LIST: Final = "ul#entry-item-list"
ENTRY_ITEM: Final = "li[data-id]"
ENTRY_CONTENT: Final = "div.content"
ENTRY_AUTHOR: Final = "a.entry-author"
ENTRY_DATE: Final = "a.entry-date"
TOPIC_LIST: Final = "ul.topic-list.partial li a"

# HTTP Headers (mimic Firefox to avoid being blocked)
HEADERS: Final = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",  # Accept types
    "Accept-Language": "tr-TR,tr;q=0.9",  # Turkish locale
    "Accept-Encoding": "gzip",  # Enable compression
    "Alt-Used": "eksisozluk.com",  # Firefox HTTP/2 coalescing header
    "Connection": "keep-alive",  # Reuse TCP connection
    "Upgrade-Insecure-Requests": "1",  # Prefer HTTPS
    # Sec-Fetch headers: tell server this is a trusted user-initiated request
    "Sec-Fetch-Dest": "document",  # Fetching a web page
    "Sec-Fetch-Mode": "navigate",  # Top-level navigation (not fetch/XHR)
    "Sec-Fetch-Site": "none",  # Direct URL entry (not from another site)
    "Sec-Fetch-User": "?1",  # Triggered by user action (click/keypress)
}


class EksiError(Exception):
    pass


class Eksi:
    def __init__(self, topic_count: int) -> None:
        self.topics: list[tuple[str, str]] = []
        self.topic_count = topic_count
        self.page_num = 1
        self.topic_title = ""
        self.topic_url = ""
        self.nav_help = (
            f"{set_color(WHITE, '(s)onraki')}, "
            f"{set_color(YELLOW, '(o)nceki')}, "
            f"{set_color(BLUE, '(g)ündem')}, "
            f"{set_color(RED, '(c)ıkış')}"
        )

    @staticmethod
    def clear_screen() -> None:
        # \e[2J: clear screen, \e[3J: clear scrollback, \e[H: move cursor to top
        os.system("cls" if os.name == "nt" else r'printf "\e[2J\e[3J\e[H"')

    @staticmethod
    def get_soup(url: str) -> Soup:
        try:
            request = Request(url, headers=HEADERS)
            response = urlopen(request, timeout=10)
            data = response.read()
            # Decompress if server returned gzip-encoded response
            encoding = response.headers.get("Content-Encoding", "")
            if encoding == "gzip":
                data = gzip.decompress(data)
            return Soup(data.decode("utf-8"), "html.parser")
        except HTTPError as e:
            error_messages = {404: "Sayfa bulunamadı!", 403: "Erişim engellendi!"}
            if e.code in error_messages:
                raise EksiError(error_messages[e.code]) from e
            if 500 <= e.code <= 511:
                raise EksiError("Sunucu hatası! Lütfen daha sonra tekrar deneyin.") from e
            raise EksiError(f"HTTP hatası: {e.code}") from e
        except URLError as e:
            if "name resolution" in str(e.reason).lower():
                raise EksiError("Internet bağlantısı yok! Lütfen bağlantınızı kontrol edin.") from e
            raise EksiError(f"Bağlantı hatası: {e.reason}") from e

    def get_entries(self, url: str) -> Iterator[tuple[str, str, str]]:
        soup = self.get_soup(url)
        entries = soup.select_one(ENTRY_LIST).select(ENTRY_ITEM)

        for entry in entries:
            content = entry.select_one(ENTRY_CONTENT)
            author = entry.select_one(ENTRY_AUTHOR).text.strip()
            date_time = entry.select_one(ENTRY_DATE).text.strip()
            # Add url to entry text
            for a in content.select("a[href]"):
                link = a["href"]
                if not link.startswith("/?q") or link.startswith("/entry"):
                    a.string = f" {link} "
            for tag in content.select("*"):
                tag.unwrap()
            if text := fill(content.text, width=80, break_long_words=False, break_on_hyphens=False).strip():
                yield text, author, date_time

    def reader(self, page_num: int = 0) -> None:
        self.clear_screen()
        print(set_color(GREEN, self.topic_title))
        page_url = f"{BASE_URL}{self.topic_url}{f'&p={page_num}' if page_num else ''}"

        for content, author, date_time in self.get_entries(page_url):
            print(set_color(YELLOW, f"\n{content}"))
            print(set_color(GREEN, author), set_color(CYAN, date_time))

        print(f"\n{self.nav_help}")

    def get_page(self) -> None:
        try:
            self.reader(self.page_num)
            if self.page_num <= 0:
                print(set_color(RED, "Şu an ilk sayfadasınız!"))
                self.page_num = 1
        except EksiError:
            self.page_num -= 1
            self.reader(self.page_num)
            print(set_color(RED, "Şu an en son sayfadasınız!"))

    def handle_topic_selection(self, cmd: str) -> None:
        try:
            topic_index = int(cmd) - 1
            if 0 <= topic_index < len(self.topics):
                self.topic_title, self.topic_url = self.topics[topic_index]
                self.reader()
            else:
                print(set_color(RED, f"Geçersiz girdi! 1-{len(self.topics)} arasında bir sayı girin."))
        except ValueError:
            print(set_color(RED, "Geçersiz girdi! Lütfen bir sayı girin."))

    def prompt(self) -> None:
        while True:
            print(set_color(MAGENTA, ">>> "), end="")
            cmd = input().strip().lower()
            match cmd:
                case "c":
                    sys.exit(0)
                case "g":
                    self.display_topics()
                case "s" if self.topic_url:
                    self.page_num += 1
                    self.get_page()
                case "o" if self.topic_url:
                    self.page_num -= 1
                    self.get_page()
                case _ if self.topic_url:
                    print(set_color(RED, "Geçersiz girdi!"), self.nav_help)
                case _:
                    self.handle_topic_selection(cmd)

    def display_topics(self) -> None:
        self.topic_title, self.topic_url, self.page_num = "", "", 1
        soup = self.get_soup(f"{BASE_URL}basliklar/m/populer")
        self.topics = [(a.text.strip(), a["href"]) for a in soup.select(TOPIC_LIST)][: self.topic_count]

        self.clear_screen()
        for i, (title, _) in enumerate(self.topics, start=1):
            name, count = title.rsplit(" ", 1)
            print(f"{set_color(MAGENTA, f'{i} -')} {set_color(YELLOW, name)} {set_color(CYAN, count)}")
        print(set_color(RED, "\n(c)ıkış"))
        self.prompt()

    def main(self) -> None:
        self.display_topics()
