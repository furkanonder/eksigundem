import sys
import unittest

from eksi.color import (
    BLACK,
    RED,
    GREEN,
    YELLOW,
    BLUE,
    MAGENTA,
    CYAN,
    RESET,
    PRINT_COLORFUL,
    set_color,
)


class TestColor(unittest.TestCase):
    @unittest.skipIf(sys.platform != "win32", reason="Requires Windows")
    def test_terminal_support_color_on_win(self):
        from windows import enable_colors_for_windows

        try:
            enable_colors_for_windows()
        except OSError:
            assert PRINT_COLORFUL is False
        else:
            assert PRINT_COLORFUL is True

    @unittest.skipIf(sys.platform == "win32", reason="Does not run on Windows")
    def test_terminal_support_color(self):
        assert PRINT_COLORFUL is True

    def test_colors(self):
        text = "this is test text"

        colored_text = set_color(BLACK, text)
        assert BLACK + text + RESET == colored_text

        colored_text = set_color(RED, text)
        assert RED + text + RESET == colored_text

        colored_text = set_color(GREEN, text)
        assert GREEN + text + RESET == colored_text

        colored_text = set_color(YELLOW, text)
        assert YELLOW + text + RESET == colored_text

        colored_text = set_color(BLUE, text)
        assert BLUE + text + RESET == colored_text

        colored_text = set_color(MAGENTA, text)
        assert MAGENTA + text + RESET == colored_text

        colored_text = set_color(CYAN, text)
        assert CYAN + text + RESET == colored_text

    def test_false_color(self):
        text = "this is test text"
        colored_text = set_color(YELLOW, text)
        assert text != colored_text
