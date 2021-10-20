import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup as Soup

from eksi.color import cprint, init_colors


class Eksi:
    base_url = "https://eksisozluk.com/"

    def __init__(self):
        self.searchable = True
        self.topic_limit = 50
        self.topic_title = ""
        self.topic_url = ""
        self.page_num = 1
        self.topics = []
        init_colors()

    @staticmethod
    def chunk(l):
        for i in range(0, len(l), 3):
            yield l[i : i + 3]

    @staticmethod
    def clear_screen():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def get_soup(url):
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = Soup(urlopen(req).read(), "html.parser")
        return soup

    def parser(self, url):
        soup = self.get_soup(url)
        entries = soup.find_all("ul", {"id": "entry-item-list"})
        lines = [
            line.strip() for line in Soup(str(*entries), "lxml").get_text().splitlines()
        ]
        entry_list = list(filter(lambda line: line != "", lines))
        chunk = self.chunk(entry_list)
        return chunk

    def reader(self, page_num=None):
        page = self.base_url + self.topic_url
        if page_num:
            page += "&p=" + str(page_num)

        chunk = self.parser(page)
        cprint("green", self.topic_title)
        for text in chunk:
            cprint("white", text[0]), cprint("cyan", text[1], text[2])

        cprint("green", "Gündem başlıklarını görüntülemek için: (g)")
        cprint("red", "Programdan çıkmak için: (c)")
        cprint("cyan", "Sonraki sayfa için: (s)\n Önceki sayfa için: (o)")

    def get_page(self):
        try:
            self.clear_screen()
            self.reader(self.page_num)
            if self.page_num <= 0:
                cprint("red", "Şu an ilk sayfadasınız!")
                self.page_num = 1
                return
        except HTTPError:
            self.page_num -= 1
            self.reader(self.page_num)
            cprint("red", "Şu an en son sayfadasınız!")

    def prompt(self):
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
                    self.topic_url = topic.get("href")
                    self.topic_title = topic.text
                    self.reader()
            except (ValueError, IndexError):
                cprint("red", "Hata!Geçersiz bir değer girdiniz.")
            except (KeyboardInterrupt, EOFError):
                sys.exit(1)

    def main(self, topic_count=None):
        self.topic_title, self.topic_url = "", ""
        self.topics.clear()
        self.clear_screen()
        self.page_num = 1

        soup = self.get_soup(self.base_url + "basliklar/m/populer")
        agenda = soup.find_all("ul", {"class": "topic-list partial mobile"})

        if topic_count:
            self.topic_limit = int(topic_count)

        for ul in agenda:
            for li in ul.find_all("li"):
                for topic in li.find_all("a"):
                    if len(self.topics) < self.topic_limit:
                        self.topics.append(topic)
                    else:
                        break

        for topic_id, topic in enumerate(self.topics):
            cprint("green", topic_id + 1, "-", end="")
            cprint("white", topic.text)

        cprint("red", "Programdan çıkmak için: (c)")
        cprint("cyan", "Okumak istediğiniz başlık numarası: ")
        self.prompt()
