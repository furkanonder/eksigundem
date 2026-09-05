from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
import shutil
import signal
from textwrap import fill
from typing import Final

from eksi import client, terminal
from eksi.color import CYAN, GREEN, MAGENTA, RED, WHITE, YELLOW, set_color

VALID_KEYS: Final = {"i", "o", "s", "e", "g"}
MAX_WRAP_WIDTH: Final = 80

QUIT_LABEL: Final = set_color(RED, "ctrl + (C)ıkış")
SCROLL_HINT: Final = set_color(CYAN, "-- Devamını oku --\n")
LOADING_LABEL: Final = set_color(CYAN, "Yükleniyor...")
PAGER_NAV_LEFT: Final = f"{set_color(WHITE, '◂◂ (i)lk ◂ (o)nceki')}"
PAGER_NAV_RIGHT: Final = f"{set_color(WHITE, '(s)onraki ▸ (e)n son ▸▸')}"
PAGER_EXIT: Final = f"{set_color(MAGENTA, '(g)ündem')} {QUIT_LABEL}"
MORE_DATA_PROMPT: Final = f"{set_color(WHITE, '(e)vet')} {set_color(YELLOW, '(h)ayır')}"


def _format_entries(entries: Iterable[tuple[str, str, str]], width: int) -> list[str]:
    lines: list[str] = []
    for content, author, date_time in entries:
        wrapped = fill(content, width=width, break_long_words=False, break_on_hyphens=False)
        lines.extend(
            (
                "",
                *(set_color(YELLOW, text_line) for text_line in wrapped.splitlines()),
                f"{set_color(GREEN, author)} {set_color(CYAN, date_time)}",
            ),
        )

    return lines


def _loading_msg(title: str) -> str:
    return f"{terminal.CLEAR_SCREEN}{set_color(GREEN, title)}\n{LOADING_LABEL}\n"


async def _prompt_more_data(
    title: str,
    href: str,
    count: int,
) -> tuple[Iterator[tuple[str, str, str]], int, int] | None:
    terminal.flush(f"{set_color(CYAN, f'{count} entry daha yüklensin mi?')} {MORE_DATA_PROMPT}\n")
    if terminal.getchar() != "e":
        return None
    terminal.flush(_loading_msg(title))
    visible, _, _, current_page, page_count = await client.get_topic_page(href)
    return visible, current_page, page_count


async def _load_entries(
    title: str,
    url: str,
    page_num: int = 0,
) -> tuple[list[tuple[str, str, str]], int, int, str]:
    terminal.flush(_loading_msg(title))
    visible, more_data_href, more_data_count, current_page, page_count = await client.get_topic_page(url, page_num)

    if (
        more_data_count > 0
        and page_num == 0
        and (result := await _prompt_more_data(title, more_data_href, more_data_count))
    ):
        visible, current_page, page_count = result
        # Strip ?a=popular so subsequent pagination uses the chronological view.
        url = url.split("?", maxsplit=1)[0]

    return list(visible), current_page, page_count, url


class ScrollView(ABC):
    def __init__(self, reserved: int) -> None:
        self._reserved = reserved
        self.lines: list[str] = []
        self.scroll_pos = 0
        self.page_size = 1
        self.max_scroll = 0

    def _relayout(self) -> None:
        self.page_size = max(shutil.get_terminal_size().lines - self._reserved, 1)
        self.max_scroll = max(len(self.lines) - self.page_size, 0)
        self.scroll_pos = min(self.scroll_pos, self.max_scroll)

    def _render(self) -> None:
        if terminal.is_too_small():
            terminal.flush(terminal.too_small_msg())
            return
        self._render_content()

    @abstractmethod
    def _render_content(self) -> None: ...

    def _on_resize(self, *_args: object) -> None:
        self._relayout()
        self._render()

    @contextmanager
    def _sigwinch_installed(self) -> Iterator[None]:
        # getchar()'s blocked read() is retried automatically after the handler runs (PEP 475).
        previous = signal.signal(signal.SIGWINCH, self._on_resize)
        try:
            yield
        finally:
            signal.signal(signal.SIGWINCH, previous)

    def _compute_scroll(self, c: str) -> None:
        if c == "\n":
            delta = 1
        elif c == " ":
            delta = self.page_size
        elif c == "\x1b" and terminal.getchar() == "[":
            seq = terminal.getchar()
            if seq in ("5", "6"):  # for PgUp/PgDn consume trailing ~
                terminal.getchar()
            delta = {
                "A": -1,  # Arrow up
                "B": 1,  # Arrow down
                "H": -self.scroll_pos,  # Home
                "F": self.max_scroll - self.scroll_pos,  # End
                "5": -self.page_size,  # PgUp
                "6": self.page_size,  # PgDn
            }.get(seq, 0)
        else:
            return
        self.scroll_pos = max(0, min(self.scroll_pos + delta, self.max_scroll))


class Pager(ScrollView):
    def __init__(
        self,
        entries: list[tuple[str, str, str]],
        title: str = "",
        warning: str = "",
        page_num: int = 0,
        page_count: int = 0,
    ) -> None:
        # Reserved lines (not available for content):
        #   2 - pager prompt (nav + exit) | 1 - scroll hint or warning text = 3
        #  +1 - title, if present | +1 - blank line before warning, if present
        super().__init__(reserved=3 + bool(title) + bool(warning))
        self._entries = entries
        self.title = title
        self.warning = warning
        self.page_num = page_num
        self.page_count = page_count
        self._relayout()

    def _relayout(self) -> None:
        wrap_width = max(min(shutil.get_terminal_size().columns - 1, MAX_WRAP_WIDTH), 1)
        self.lines = _format_entries(self._entries, wrap_width)
        super()._relayout()

    def _render_content(self) -> None:
        visible_lines = "\n".join(self.lines[self.scroll_pos : self.scroll_pos + self.page_size])
        if self.warning:
            footer = f"\n{set_color(RED, self.warning)}\n"
        elif self.scroll_pos < self.max_scroll:
            footer = SCROLL_HINT
        else:
            footer = "\n"
        page_info = f" - {set_color(CYAN, f'{self.page_num}/{self.page_count}')} - " if self.page_count else "  "
        prompt = f"{PAGER_EXIT}\n{PAGER_NAV_LEFT}{page_info}{PAGER_NAV_RIGHT}"
        terminal.flush(f"{terminal.CLEAR_SCREEN}{set_color(GREEN, self.title)}\n{visible_lines}\n{footer}{prompt}")

    def run(self) -> str:
        with self._sigwinch_installed():
            while True:
                self._render()
                if (c := terminal.getchar()) in VALID_KEYS:
                    return c
                self._compute_scroll(c)

    @staticmethod
    def _clamp_page(page_num: int, page_count: int) -> tuple[int, str]:
        if page_num <= 0:
            return 1, "Şu an ilk sayfadasınız!"
        if page_num > page_count:
            return page_count, "Şu an en son sayfadasınız!"
        return page_num, ""

    @classmethod
    async def _get_page(
        cls,
        title: str,
        url: str,
        page_num: int,
        page_count: int,
    ) -> tuple[str, int, int]:
        page_num, warning = cls._clamp_page(page_num, page_count)
        entries, current_page, page_count, _ = await _load_entries(title, url, page_num)
        cmd = cls(entries, title, warning, current_page, page_count).run()
        return cmd, current_page, page_count

    @classmethod
    async def enter_topic(cls, title: str, url: str) -> None:
        entries, current_page, page_count, url = await _load_entries(title, url)
        cmd = cls(entries, title, page_num=current_page, page_count=page_count).run()
        page_num = current_page

        while cmd != "g":
            if cmd == "i":
                page_num = 1
            elif cmd == "e":
                page_num = page_count
            elif cmd == "s":
                page_num += 1
            elif cmd == "o":
                page_num -= 1
            cmd, page_num, page_count = await cls._get_page(title, url, page_num, page_count)


class TopicSelector(ScrollView):
    def __init__(self, topics: list[tuple[str, str]]) -> None:
        # Reserved: 1 scroll hint + 1 status bar + 1 prompt
        super().__init__(reserved=3)
        self.topics = topics
        self.lines = self._build_lines()
        self.buf = ""
        self.hint = set_color(WHITE, f"1-{len(topics)} arası bir başlık seçin")
        self.error = set_color(RED, f"Geçersiz giriş! 1-{len(topics)} arası bir sayı girin.")
        self.status = self.hint
        self._relayout()

    def _build_lines(self) -> list[str]:
        lines: list[str] = []
        for i, (title, _) in enumerate(self.topics, start=1):
            parts = title.rsplit(" ", 1)
            name = parts[0] if len(parts) > 1 else title
            count = parts[1] if len(parts) > 1 else ""
            lines.append(f"{set_color(MAGENTA, f'{i} -')} {set_color(YELLOW, name)} {set_color(CYAN, count)}")
        return lines

    def _render_content(self) -> None:
        footer = SCROLL_HINT if self.scroll_pos < self.max_scroll else "\n"
        visible = "\n".join(self.lines[self.scroll_pos : self.scroll_pos + self.page_size])
        prompt = f"{QUIT_LABEL} | {self.status}\n{terminal.SHOW_CURSOR}>>> {self.buf}"
        terminal.flush(f"{terminal.CLEAR_SCREEN}{visible}\n{footer}{prompt}")

    def _handle_input(self, c: str) -> None:
        if c == terminal.BACKSPACE and self.buf:
            self.buf = self.buf[:-1]
        elif c.isdigit():
            self.buf += c
        else:
            self._compute_scroll(c)

    def _try_select(self) -> tuple[str, str] | None:
        if self.buf.isdigit() and 1 <= (index := int(self.buf)) <= len(self.topics):
            terminal.flush(terminal.HIDE_CURSOR)
            return self.topics[index - 1]
        return None

    def run(self) -> tuple[str, str]:
        with self._sigwinch_installed():
            while True:
                self._render()
                c = terminal.getchar()
                if c == "\n" and self.buf:
                    if selected := self._try_select():
                        return selected
                    self.buf, self.status = "", self.error
                else:
                    self._handle_input(c)
                    self.status = self.hint
