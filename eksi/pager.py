import shutil
from typing import Final

from eksi.color import BLUE, CYAN, GREEN, RED, WHITE, YELLOW, set_color
from eksi.terminal import CLEAR_SCREEN, Terminal, getchar

VALID_KEYS: Final = {"s", "o", "g"}

PAGER_PROMPT: Final = (
    f"{set_color(WHITE, '(s)onraki')} {set_color(YELLOW, '(o)nceki')} {set_color(BLUE, '(g)ündem')} "
    f"{set_color(RED, 'ctrl + (C)ıkış')}"
)


class Pager:
    def __init__(self, lines: list[str], title: str = "", warning: str = "") -> None:
        self.lines = lines
        self.title = title
        self.warning = warning

    @staticmethod
    def compute_scroll(c: str, scroll_pos: int, page_size: int, max_scroll: int) -> int:
        if c == "\n":
            delta = 1
        elif c == " ":
            delta = page_size
        elif c == "\x1b" and getchar() == "[":
            seq = getchar()
            if seq in ("5", "6"):  # for PgUp/PgDn consume trailing ~
                getchar()
            delta = {
                "A": -1,  # Arrow up
                "B": 1,  # Arrow down
                "H": -scroll_pos,  # Home
                "F": max_scroll - scroll_pos,  # End
                "5": -page_size,  # PgUp
                "6": page_size,  # PgDn
            }.get(seq, 0)
        else:
            return scroll_pos
        return max(0, min(scroll_pos + delta, max_scroll))

    def _render(self, scroll_pos: int, page_size: int, max_scroll: int) -> None:
        visible_lines = "\n".join(self.lines[scroll_pos : scroll_pos + page_size])
        if self.warning:
            footer = f"\n{set_color(RED, self.warning)}\n"
        elif scroll_pos < max_scroll:
            footer = set_color(CYAN, "-- Devamını oku --\n")
        else:
            footer = "\n"
        Terminal.flush(f"{CLEAR_SCREEN}{set_color(GREEN, self.title)}\n{visible_lines}\n{footer}{PAGER_PROMPT}")

    def run(self) -> str:
        # Reserved lines (not available for content):
        #   1 - pager prompt | 1 - scroll hint or warning text = 2
        #  +1 - title, if present | +1 - blank line before warning, if present
        reserved = 2 + bool(self.title) + bool(self.warning)
        page_size = max(shutil.get_terminal_size().lines - reserved, 1)
        max_scroll = max(len(self.lines) - page_size, 0)
        scroll_pos = 0

        while True:
            self._render(scroll_pos, page_size, max_scroll)
            if (c := getchar()) in VALID_KEYS:
                return c
            scroll_pos = self.compute_scroll(c, scroll_pos, page_size, max_scroll)
