from __future__ import annotations

import sys

BLACK = "\x1b[30m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
BLUE = "\x1b[34m"
MAGENTA = "\x1b[35m"
CYAN = "\x1b[36m"
WHITE = "\x1b[37m"
RESET = "\x1b[0m"

PRINT_COLORFUL = True

if sys.platform == "win32":
    from windows import enable_colors_for_windows

    try:
        enable_colors_for_windows()
    except OSError:
        PRINT_COLORFUL = False


def set_color(color: str, text: str) -> str:
    return f"{color}{text}{RESET}" if PRINT_COLORFUL else text
