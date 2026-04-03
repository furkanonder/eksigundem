from collections.abc import Iterator
from contextlib import contextmanager
import shutil
import sys
import termios
import tty
from typing import Final

from eksi.color import RED, set_color

# Minimum terminal size for proper rendering
MIN_COLS: Final = 80
MIN_LINES: Final = 20

# ANSI escape sequences
SHOW_CURSOR: Final = "\033[?25h"
HIDE_CURSOR: Final = "\033[?25l"
BACKSPACE: Final = "\x7f"

ALT_SCREEN_ON: Final = f"\033[?1049h{HIDE_CURSOR}"  # Enter an alternate screen buffer, hide the cursor
ALT_SCREEN_OFF: Final = f"{SHOW_CURSOR}\033[?1049l"  # Show cursor, exit alternate screen buffer
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
        except (OSError, termios.error):
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

    @staticmethod
    def read_filtered() -> int:
        buf = ""
        while True:
            c = getchar()
            if c == "\n" and buf:
                Terminal.flush("\n")
                return int(buf)
            if c == BACKSPACE and buf:
                buf = buf[:-1]
                Terminal.flush("\b \b")  # move left, overwrite with space, move left
            elif c.isdigit():
                buf += c
                Terminal.flush(c)
