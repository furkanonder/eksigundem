from collections.abc import Iterator
from contextlib import contextmanager
import shutil
import sys
import termios
import tty
from typing import Final

from eksi.client import EksiClient, EksiError
from eksi.color import BLUE, CYAN, GREEN, MAGENTA, RED, WHITE, YELLOW, set_color

BASE_URL: Final = "https://eksisozluk.com/"

# Minimum terminal size for proper rendering
MIN_COLS: Final = 80
MIN_LINES: Final = 20

VALID_KEYS: Final = {"s", "o", "g", "c"}

PAGER_PROMPT: Final = (
    f"{set_color(WHITE, '(s)onraki')} {set_color(YELLOW, '(o)nceki')} {set_color(BLUE, '(g)ündem')} "
    f"{set_color(RED, '(c)ıkış')}"
)

# ANSI escape sequences
ALT_SCREEN_ON: Final = "\033[?1049h\033[?25l"  # Enter an alternate screen buffer, hide the cursor
ALT_SCREEN_OFF: Final = "\033[?25h\033[?1049l"  # Show cursor, exit alternate screen buffer
CLEAR_SCREEN: Final = "\033[2J\033[3J\033[H"  # Clear the screen, scrollback, and cursor home


def getchar() -> str:
    return sys.stdin.read(1)


class Terminal:
    @staticmethod
    def flush(*parts: str) -> None:
        sys.stdout.write("".join(parts))
        sys.stdout.flush()

    @staticmethod
    @contextmanager
    def cbreak_mode() -> Iterator[None]:
        fd = old = None
        try:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except termios.error:
            pass
        try:
            yield
        finally:
            if fd is not None and old is not None:
                termios.tcsetattr(fd, termios.TCSAFLUSH, old)

    @staticmethod
    def check_size() -> None:
        term = shutil.get_terminal_size()
        if term.columns < MIN_COLS or term.lines < MIN_LINES:
            Terminal.flush(set_color(RED, f"Terminal boyutu çok küçük! En az {MIN_COLS}x{MIN_LINES} olmalıdır.\n"))
            sys.exit(1)


class Pager:
    def __init__(self, lines: list[str], title: str = "", warning: str = "") -> None:
        self.lines = lines
        self.title = title
        self.warning = warning

    @staticmethod
    def compute_scroll(c: str, scroll_pos: int, page_size: int, max_scroll: int) -> int:  # noqa: PLR0911
        if c in ("\r", "\n"):
            return min(scroll_pos + 1, max_scroll)
        if c == " ":
            return min(scroll_pos + page_size, max_scroll)
        if c != "\x1b" or getchar() != "[":
            return scroll_pos
        match getchar():
            case "A":  # Arrow up
                return max(scroll_pos - 1, 0)
            case "B":  # Arrow down
                return min(scroll_pos + 1, max_scroll)
            case "H":  # Home
                return 0
            case "F":  # End
                return max_scroll
            case "5":  # PgUp
                getchar()  # consume trailing ~
                return max(scroll_pos - page_size, 0)
            case "6":  # PgDn
                getchar()  # consume trailing ~
                return min(scroll_pos + page_size, max_scroll)
            case _:
                return scroll_pos

    def _render(self, scroll_pos: int, page_size: int, max_scroll: int) -> None:
        visible_lines = "\n".join(self.lines[scroll_pos : scroll_pos + page_size])
        scroll_hint = set_color(CYAN, "-- Devamını oku --\n") if scroll_pos < max_scroll else "\n"
        Terminal.flush(
            CLEAR_SCREEN,
            f"{set_color(GREEN, self.title)}\n",
            f"{visible_lines}\n",
            f"\n{set_color(RED, self.warning)}\n" if self.warning else scroll_hint,
            PAGER_PROMPT,
        )

    def run(self) -> str:
        # 2 = prompt line + scroll hint/warning line; +1 each if title or warning present
        reserved = 2 + bool(self.title) + bool(self.warning)
        page_size = max(shutil.get_terminal_size().lines - reserved, 1)
        max_scroll = max(len(self.lines) - page_size, 0)
        scroll_pos = 0

        while True:
            self._render(scroll_pos, page_size, max_scroll)
            c = getchar()
            if not c or c in VALID_KEYS:
                return c or "g"
            scroll_pos = self.compute_scroll(c, scroll_pos, page_size, max_scroll)


class Eksi:
    def __init__(self, topic_count: int) -> None:
        self.topics: list[tuple[str, str]] = []
        self.topic_count = topic_count
        self.page_num = 1
        self.topic_title = ""
        self.topic_url = ""

    def _load_entries(self, page_num: int = 0) -> list[str]:
        Terminal.flush(
            CLEAR_SCREEN,
            f"{set_color(GREEN, self.topic_title)}\n",
            f"{set_color(CYAN, 'Yükleniyor...')}\n",
        )
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
        with Terminal.cbreak_mode():
            Terminal.flush(ALT_SCREEN_ON)
            try:
                lines = self._load_entries()
                cmd = Pager(lines, self.topic_title).run()
                while cmd in ("s", "o"):
                    self.page_num += 1 if cmd == "s" else -1
                    cmd = self._get_page()
            finally:
                Terminal.flush(ALT_SCREEN_OFF)
        if cmd == "c":
            sys.exit(0)
        if cmd == "g":
            self.display_topics()

    def prompt(self) -> None:
        Terminal.flush(f"{set_color(RED, '(c)ıkış')}\n")
        while True:
            cmd = input(">>> ").strip().lower()
            match cmd:
                case "c":
                    sys.exit(0)
                case "g":
                    self.display_topics()
                case num if num.isdigit() and 1 <= (index := int(num)) <= len(self.topics):
                    self.topic_title, self.topic_url = self.topics[index - 1]
                    self._enter_topic()
                case _:
                    Terminal.flush(set_color(RED, f"Geçersiz giriş! 1-{len(self.topics)} arası bir sayı girin.\n"))

    def display_topics(self) -> None:
        self.topic_title, self.topic_url, self.page_num = "", "", 1
        self.topics = EksiClient.get_topics(f"{BASE_URL}basliklar/m/populer", self.topic_count)

        parts = [CLEAR_SCREEN]
        for i, (title, _) in enumerate(self.topics, start=1):
            name, count = title.rsplit(" ", 1)
            parts.append(f"{set_color(MAGENTA, f'{i} -')} {set_color(YELLOW, name)} {set_color(CYAN, count)}\n")
        Terminal.flush(*parts)

    def main(self) -> None:
        Terminal.check_size()
        self.display_topics()
        self.prompt()
