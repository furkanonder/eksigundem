from typing import Final

from eksi import client, session, terminal
from eksi.color import CYAN, set_color
from eksi.pager import Pager, TopicSelector

RETURNING_MSG: Final = f"{terminal.CLEAR_SCREEN}{set_color(CYAN, 'Gündem konularına dönülüyor...')}\n"


class Eksi:
    def __init__(self, topic_count: int) -> None:
        self.topics: list[tuple[str, str]] = []
        self.topic_count = topic_count

    async def _fetch_topics(self) -> None:
        self.topics = await client.get_topics(self.topic_count)

    async def prompt(self) -> None:
        with terminal.cbreak_mode():
            while True:
                title, url = TopicSelector(self.topics).run()
                await Pager.enter_topic(title, url)
                terminal.flush(RETURNING_MSG)
                await self._fetch_topics()

    async def main(self) -> None:
        terminal.flush(terminal.ALT_SCREEN_ON)
        session.open_session()
        try:
            await self._fetch_topics()
            await self.prompt()
        except KeyboardInterrupt:
            pass
        finally:
            await session.close_session()
            terminal.flush(terminal.ALT_SCREEN_OFF)
