from typing import Final

from eksi.client import EksiClient, EksiError
from eksi.color import CYAN, GREEN, MAGENTA, RED, YELLOW, set_color
from eksi.pager import Pager
from eksi.terminal import ALT_SCREEN_OFF, ALT_SCREEN_ON, CLEAR_SCREEN, HIDE_CURSOR, SHOW_CURSOR, Terminal

BASE_URL: Final = "https://eksisozluk.com/"


class Eksi:
    def __init__(self, topic_count: int) -> None:
        self.topics: list[tuple[str, str]] = []
        self.topic_count = topic_count
        self.page_num = 1
        self.topic_title = ""
        self.topic_url = ""

    def _load_entries(self, page_num: int = 0) -> list[str]:
        Terminal.flush(f"{CLEAR_SCREEN}{set_color(GREEN, self.topic_title)}\n{set_color(CYAN, 'Yükleniyor...')}\n")
        page_url = f"{BASE_URL}{self.topic_url}{f'&p={page_num}' if page_num else ''}"
        lines: list[str] = []

        for content, author, date_time in EksiClient.get_entries(page_url):
            lines.extend(
                (
                    "",
                    *(set_color(YELLOW, text_line) for text_line in content.splitlines()),
                    f"{set_color(GREEN, author)} {set_color(CYAN, date_time)}",
                ),
            )
        return lines

    def _get_page(self) -> str:
        warning = ""
        if self.page_num <= 0:
            self.page_num = 1
            warning = "Şu an ilk sayfadasınız!"
        try:
            lines = self._load_entries(self.page_num)
        except EksiError:
            self.page_num -= 1
            warning = "Şu an en son sayfadasınız!"
            lines = self._load_entries(self.page_num)
        return Pager(lines, self.topic_title, warning).run()

    def _enter_topic(self) -> None:
        lines = self._load_entries()
        cmd = Pager(lines, self.topic_title).run()
        while cmd in ("s", "o"):
            self.page_num += 1 if cmd == "s" else -1
            cmd = self._get_page()

    def prompt(self) -> None:
        with Terminal.cbreak_mode():
            while True:
                Terminal.flush(f"{SHOW_CURSOR}>>> ")
                index = Terminal.read_filtered()
                if 1 <= index <= len(self.topics):
                    Terminal.flush(HIDE_CURSOR)
                    self.topic_title, self.topic_url = self.topics[index - 1]
                    self._enter_topic()
                    Terminal.flush(f"{CLEAR_SCREEN}{set_color(CYAN, 'Gündem konularına dönülüyor...')}\n")
                    self.display_topics()
                else:
                    Terminal.flush(set_color(RED, f"Geçersiz giriş! 1-{len(self.topics)} arası bir sayı girin.\n"))

    def display_topics(self) -> None:
        self.topic_title, self.topic_url, self.page_num = "", "", 1
        self.topics = EksiClient.get_topics(f"{BASE_URL}basliklar/m/populer", self.topic_count)
        parts = [CLEAR_SCREEN]

        for i, (title, _) in enumerate(self.topics, start=1):
            name, count = title.rsplit(" ", 1)
            parts.append(f"{set_color(MAGENTA, f'{i} -')} {set_color(YELLOW, name)} {set_color(CYAN, count)}\n")
        hint = f"1-{len(self.topics)} arasında bir başlık seçin"
        parts.append(f"{set_color(RED, 'ctrl + (C)ıkış')}\n{set_color(CYAN, hint)}\n")
        Terminal.flush(*parts)

    def main(self) -> None:
        Terminal.check_size()
        Terminal.flush(ALT_SCREEN_ON)
        try:
            self.display_topics()
            self.prompt()
        except KeyboardInterrupt:
            pass
        finally:
            Terminal.flush(ALT_SCREEN_OFF)
