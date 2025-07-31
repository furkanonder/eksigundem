from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from textwrap import fill
from typing import ClassVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup as Soup

from eksi.color import BLUE, CYAN, GREEN, MAGENTA, RED, YELLOW, set_color


class EksiError(Exception):
    pass


class Eksi:
    base_url: ClassVar[str] = "https://eksisozluk.com/"

    def __init__(self) -> None:
        self.topics: tuple[dict[str, str], ...] = ()
        self.topic_limit: int = 50
        self.page_num: int = 1
        self.topic_title: str = ""
        self.topic_url: str = ""

    @staticmethod
    def clear_screen() -> None:
        r"""If you are wondering how 'printf "\e[2J\e[3J\e[H"' works, you can
        read the link below.

        https://apple.stackexchange.com/questions/31872/how-do-i-reset-the-scrollback-in-the-terminal-via-a-shell-command

        """
        if os.name == "nt":
            os.system("cls")
        else:
            os.system(r'printf "\e[2J\e[3J\e[H"')

    @staticmethod
    def _print_navigation_help() -> None:
        print(set_color(GREEN, "Sonraki sayfa için: (s) | Önceki sayfa için: (o)"))
        print(set_color(GREEN, "Gündem başlıklarını görüntülemek için: (g)"))
        print(set_color(MAGENTA, "Programdan çıkmak için: (c)"))

    @staticmethod
    def get_soup(url: str) -> Soup:
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            response = urlopen(request, timeout=10)
            return Soup(response.read().decode("utf-8"), "html.parser")
        except HTTPError as e:
            error_messages = {404: "Sayfa bulunamadı!", 403: "Erişim engellendi!"}
            if e.code in error_messages:
                raise EksiError(error_messages[e.code]) from e
            elif 500 <= e.code <= 511:
                raise EksiError("Sunucu hatası! Lütfen daha sonra tekrar deneyin.") from e
            else:
                raise EksiError(f"HTTP hatası: {e.code}") from e
        except URLError as e:
            if "name resolution" in str(e.reason).lower():
                raise EksiError("Internet bağlantısı yok! Lütfen bağlantınızı kontrol edin.") from e
            else:
                raise EksiError(f"Bağlantı hatası: {e.reason}") from e

    def get_entries(self, url: str) -> Iterator[tuple[str, ...]]:
        soup = self.get_soup(url)
        entries = soup.find("ul", {"id": "entry-item-list"}).find_all("li")

        for entry in entries:
            content = entry.find("div", class_="content")
            author_date = entry.find("div", class_="footer-info").text.splitlines()
            # Add url to entry text
            for a in content.select("a[href]"):
                link = a["href"]
                if not link.startswith("/?q") or link.startswith("/entry"):
                    a.string = f" {link} "
            for tag in content.select("*"):
                tag.unwrap()
            formatted_text = fill(content.text, width=80, break_long_words=False, break_on_hyphens=False).strip()
            if formatted_text:  # Only yield non-empty entries
                yield tuple(filter(None, [formatted_text, *author_date]))

    def reader(self, page_num: int = 0) -> None:
        self.clear_screen()
        print(set_color(GREEN, self.topic_title))
        page_url = f"{self.base_url}{self.topic_url}"
        page_url += f"&p={page_num}" if page_num else ""

        for entry in self.get_entries(page_url):
            print(set_color(YELLOW, entry[0]))
            print(set_color(CYAN, " ".join(entry[1:])))

        self._print_navigation_help()

    def get_page(self) -> None:
        if self.page_num <= 0:
            print(set_color(RED, "Şu an ilk sayfadasınız!"))
            self.page_num = 1
        try:
            self.reader(self.page_num)
        except EksiError:
            # If page doesn't exist, go back one page
            if self.page_num > 1:
                self.page_num -= 1
                print(set_color(RED, "Şu an en son sayfadasınız!"))
                self.reader(self.page_num)

    def handle_topic_selection(self, cmd: str) -> None:
        try:
            topic_index = int(cmd) - 1
            if 0 <= topic_index < len(self.topics):
                topic = self.topics[topic_index]
                self.topic_title, self.topic_url = topic.popitem()
                self.reader()
            else:
                print(set_color(RED, f"Geçersiz girdi! 1-{len(self.topics)} arasında bir sayı girin."))
        except ValueError:
            print(set_color(RED, "Geçersiz girdi! Lütfen bir sayı girin."))

    def prompt(self) -> None:
        while True:
            try:
                cmd = input(">>> ").strip().lower()
                if cmd == "c":
                    sys.exit(0)
                elif cmd == "g":
                    self.main()
                elif self.topic_url:
                    if cmd == "s":
                        self.page_num += 1
                        self.get_page()
                    elif cmd == "o":
                        self.page_num = max(1, self.page_num - 1)
                        self.get_page()
                    else:
                        print(set_color(RED, "Geçersiz girdi! (s)onraki, (o)nceki, (g)ündem, (c)ıkış"))
                else:
                    self.handle_topic_selection(cmd)
            except (KeyboardInterrupt, EOFError):
                sys.exit(0)
            except Exception as e:
                print(set_color(RED, f"Beklenmeyen hata: {e}"))

    def load_topics(self, topic_count: int = 0) -> None:
        soup = self.get_soup(f"{self.base_url}basliklar/m/populer")
        topics = soup.find("ul", {"class": "topic-list partial mobile"}).find_all("li")
        if topic_count:
            self.topic_limit = min(topic_count, len(topics))
        self.topics = tuple(
            {li.text.strip(): li.find("a").get("href")}
            for li in topics[: self.topic_limit]
            if li.find("a") and li.find("a").get("href")
        )

    def display_topics(self) -> None:
        self.clear_screen()
        print(set_color(CYAN, "Gündem Başlıkları\n"))

        for index, topic in enumerate(self.topics, start=1):
            title, entry_count = list(topic)[0].rsplit(" ", 1)
            print(set_color(GREEN, str(index)), end=" - ")
            print(set_color(YELLOW, title), end=" ")
            print(set_color(BLUE, entry_count))

        print(f"\n{set_color(RED, 'Programdan çıkmak için: (c)')}")
        print(set_color(CYAN, "Okumak istediğiniz başlık numarası: "))

    def main(self, topic_count: int = 0) -> None:
        self.clear_screen()
        print(set_color(CYAN, "Gündem başlıkları yükleniyor..."))
        self.load_topics(topic_count)
        self.display_topics()
        self.prompt()
