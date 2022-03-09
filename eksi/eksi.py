from __future__ import annotations

import os
import sys
from textwrap import fill
from typing import ClassVar, Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup as Soup
from colorama import init as init_colors

from eksi.color import cprint


class Eksi:
    base_url: ClassVar[str] = "https://eksisozluk.com/"

    def __init__(self) -> None:
        self.topics: tuple[dict[str, str], ...]
        self.topic_limit: int = 50
        self.page_num: int = 1
        self.topic_title: str
        self.topic_url: str
        init_colors()

    @staticmethod
    def clear_screen() -> None:
        """
        If you are wondering how 'printf "\e[2J\e[3J\e[H"' works, you can read to the link below.
        https://apple.stackexchange.com/questions/31872/how-do-i-reset-the-scrollback-in-the-terminal-via-a-shell-command
        """
        if os.name == "nt":
            os.system("cls")
        else:
            os.system('printf "\e[2J\e[3J\e[H"')

    @staticmethod
    def get_soup(url: str) -> Soup:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = Soup(urlopen(request).read(), "html.parser")
        return soup

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

            # Format the entry text
            output = tuple(
                filter(
                    lambda val: val,
                    (
                        fill(
                            content.text,
                            width=80,
                            break_long_words=False,
                            break_on_hyphens=False,
                        ).strip(),
                        *author_date,
                    ),
                )
            )

            yield output

    def reader(self, page_num: int = 0) -> None:
        self.clear_screen()
        cprint("green", self.topic_title)
        page_url = self.base_url + self.topic_url
        page_url += f"&p={page_num}" if page_num else ""

        for entry in self.get_entries(page_url):
            cprint("white", entry[0])
            cprint("cyan", " ".join(entry[1:]))

        cprint("green", "Sonraki sayfa için: (s) | Önceki sayfa için: (o)")
        cprint("green", "Gündem başlıklarını görüntülemek için: (g)")
        cprint("magenta", "Programdan çıkmak için: (c)")

    def get_page(self) -> None:
        try:
            self.reader(self.page_num)
            if self.page_num <= 0:
                cprint("red", "Şu an ilk sayfadasınız!")
                self.page_num = 1
        except HTTPError:
            self.page_num -= 1
            self.reader(self.page_num)
            cprint("red", "Şu an en son sayfadasınız!")

    def prompt(self) -> None:
        while True:
            try:
                cmd = input(">>> ")
                if cmd == "c":
                    sys.exit(0)
                elif cmd == "g":
                    self.main()
                elif self.topic_url:
                    if cmd == "s":
                        self.page_num += 1
                    elif cmd == "o":
                        self.page_num -= 1
                    self.get_page()
                else:
                    topic = self.topics[int(cmd) - 1]
                    self.topic_title, self.topic_url = topic.popitem()
                    self.reader()
            except (ValueError, IndexError):
                cprint("red", "Hata!Geçersiz bir değer girdiniz.")
            except (KeyboardInterrupt, EOFError):
                sys.exit(1)

    def main(self, topic_count: int = 0) -> None:
        self.clear_screen()
        self.topic_title, self.topic_url, self.page_num = "", "", 1

        soup = self.get_soup(self.base_url + "basliklar/m/populer")
        topics = soup.find("ul", {"class": "topic-list partial mobile"}).find_all("li")

        if topic_count:
            self.topic_limit = topic_count

        self.topics = tuple(
            {li.text.strip(): li.find("a").get("href")} for li in topics
        )[: self.topic_limit]

        for index, topic in enumerate(self.topics, start=1):
            title, entry_count = list(topic)[0].rsplit(" ", 1)
            cprint("green", index, end=" - ")
            cprint("white", title, end=" ")
            cprint("blue", entry_count)

        cprint("red", "Programdan çıkmak için: (c)")
        cprint("cyan", "Okumak istediğiniz başlık numarası: ")
        self.prompt()
