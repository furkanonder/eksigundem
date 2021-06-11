import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from bs4 import BeautifulSoup

from eksi.color import cprint, init_colors


class Eksi:
    home_page = "https://eksisozluk.com/"

    def __init__(self):
        self.page_num = 1
        self.searchable = True
        self.topic_url = ""
        self.topics = []
        self.topic_limit = 50
        init_colors()

    def chunk(self, l):
        for i in range(0, len(l), 3):
            yield l[i : i + 3]

    def parser(self, url):
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        page = urlopen(req).read()
        soup = BeautifulSoup(page, "html.parser")
        entries = soup.find_all("ul", {"id": "entry-item-list"})
        soup = BeautifulSoup(str(*entries), "lxml")
        lines = [line.strip() for line in soup.get_text().splitlines()]
        entry_list = list(filter(lambda line: line != "", lines))
        return self.chunk(entry_list)

    def reader(self, url):
        chunk = self.parser(self.home_page + url)
        for c in chunk:
            cprint("white", c[0])
            cprint("cyan", c[1], c[2])
        cprint("green", "Gündem başlıklarını görüntülemek için: (g)")
        cprint("red", "Programdan çıkmak için: (c)")
        cprint("cyan", "Sonraki sayfa için: (s)\n Önceki sayfa için: (o)")

    @staticmethod
    def clear_screen():
        os.system("cls" if os.name == "nt" else "clear")

    def get_page(self, url, page_num):
        self.clear_screen()
        try:
            if page_num <= 0:
                cprint("green", self.topic_title)
                self.reader(url + "&p=" + str(1))
                cprint("red", "Şu an ilk sayfadasınız!")
                self.page_num = 1
                return
            cprint("green", self.topic_title)
            self.reader(url + "&p=" + str(self.page_num))
        except HTTPError:
            self.reader(url + "&p=" + str(self.page_num - 1))
            cprint("red", "Şu an en son sayfadasınız!")
            self.page_num -= 1

    def prompt(self):
        while True:
            try:
                cmd = input(">>> ")
                if cmd == "c":
                    sys.exit(0)
                elif cmd == "g":
                    self.searchable = True
                    self.clear_screen()
                    self.main()
                elif cmd == "s" and self.topic_url:
                    self.page_num += 1
                    self.get_page(self.topic_url, self.page_num)
                elif cmd == "o" and self.topic_url:
                    self.page_num -= 1
                    self.get_page(self.topic_url, self.page_num)
                elif self.searchable and int(cmd) <= self.topic_limit and int(cmd) > 0:
                    self.searchable = False
                    self.clear_screen()
                    self.topic_url = self.topics[int(cmd) - 1].get("href")
                    self.topic_title = self.topics[int(cmd) - 1].text
                    cprint("green", self.topic_title)
                    self.reader(self.topic_url)
                else:
                    cprint("red", "Hata!Geçersiz bir değer girdiniz.")
            except (ValueError, IndexError) as error:
                cprint("red", "Hata!Geçersiz bir değer girdiniz.")
            except (KeyboardInterrupt, EOFError) as error:
                break

    def main(self, topic_count=None):
        req = Request(self.home_page, headers={"User-Agent": "Mozilla/5.0"})
        page = urlopen(req).read()
        soup = BeautifulSoup(page, "html.parser")
        agenda = soup.find_all("ul", {"class": "topic-list partial"})
        self.topic_title, self.topic_url = "", ""
        self.topics, self.page_num = [], 1

        for ul in agenda:
            for li in ul.find_all("li"):
                for topic in li.find_all("a"):
                    self.topics.append(topic)

        if topic_count:
            self.topic_limit = int(topic_count)
        else:
            self.topic_limit = len(self.topics)

        for topic_id, topic in enumerate(self.topics):
            if self.topic_limit > topic_id:
                cprint("green", topic_id + 1, "-", end="")
                cprint("white", topic.text)
            else:
                break

        cprint("red", "Programdan çıkmak için: (c)")
        cprint("cyan", "Okumak istediğiniz başlık numarası: ")
        self.prompt()
