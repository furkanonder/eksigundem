from typing import Final

from eksi import client, terminal
from eksi.color import CYAN, set_color
from eksi.pager import Pager, TopicSelector

RETURNING_MSG: Final = f"{terminal.CLEAR_SCREEN}{set_color(CYAN, 'Gündem konularına dönülüyor...')}\n"


class Eksi:
    def __init__(self, topic_count: int) -> None:
        self.topics: list[tuple[str, str]] = []
        self.topic_count = topic_count

    def _fetch_topics(self) -> None:
        self.topics = client.get_topics(self.topic_count)

    def prompt(self) -> None:
        with terminal.cbreak_mode():
            while True:
                title, url = TopicSelector(self.topics).run()
                Pager.enter_topic(title, url)
                terminal.flush(RETURNING_MSG)
                self._fetch_topics()

    def main(self) -> None:
        terminal.check_size()
        terminal.flush(terminal.ALT_SCREEN_ON)
        try:
            self._fetch_topics()
            self.prompt()
        except KeyboardInterrupt:
            pass
        finally:
            terminal.flush(terminal.ALT_SCREEN_OFF)
