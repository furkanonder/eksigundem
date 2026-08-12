from collections.abc import Iterator
from contextlib import contextmanager
import shutil
import sys
import termios
import tty
from typing import Final

from eksi.color import GREEN, RED, set_color

# Minimum terminal size for proper rendering
MIN_COLS: Final = 60
MIN_LINES: Final = 18

# ANSI escape sequences
SHOW_CURSOR: Final = "\033[?25h"
HIDE_CURSOR: Final = "\033[?25l"
BACKSPACE: Final = "\x7f"

ALT_SCREEN_ON: Final = f"\033[?1049h{HIDE_CURSOR}"  # Enter an alternate screen buffer, hide the cursor
ALT_SCREEN_OFF: Final = f"{SHOW_CURSOR}\033[?1049l"  # Show cursor, exit alternate screen buffer
CLEAR_SCREEN: Final = "\033[2J\033[3J\033[H"  # Clear the screen, scrollback, and cursor home


def getchar() -> str:
    return sys.stdin.read(1)


def flush(*parts: str) -> None:
    sys.stdout.write("".join(parts))
    sys.stdout.flush()


@contextmanager
def cbreak_mode() -> Iterator[None]:
    fd = old = None
    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    except (OSError, termios.error):
        pass
    try:
        yield
    finally:
        if fd is not None and old is not None:
            termios.tcsetattr(fd, termios.TCSAFLUSH, old)


def is_too_small() -> bool:
    term = shutil.get_terminal_size()
    return term.columns < MIN_COLS or term.lines < MIN_LINES


def too_small_msg() -> str:
    term = shutil.get_terminal_size()
    cols, rows = term.columns, term.lines

    cur_w = set_color(RED if cols < MIN_COLS else GREEN, str(cols))
    cur_h = set_color(RED if rows < MIN_LINES else GREEN, str(rows))

    current_colored = f"Genişlik = {cur_w} Yükseklik = {cur_h}"
    current_visible_len = len(f"Genişlik = {cols} Yükseklik = {rows}")

    def pad(visible_len: int) -> str:
        return " " * max((cols - visible_len) // 2, 0)

    top_padding = "\n" * max((rows - 5) // 2, 0)
    label1 = "Terminal boyutu çok küçük:"
    label2 = "Gerekli boyut:"
    needed = f"Genişlik = {MIN_COLS} Yükseklik = {MIN_LINES}"

    return (
        f"{CLEAR_SCREEN}{top_padding}"
        f"{pad(len(label1))}{label1}\n"
        f"{pad(current_visible_len)}{current_colored}\n"
        f"\n"
        f"{pad(len(label2))}{label2}\n"
        f"{pad(len(needed))}{needed}"
    )
