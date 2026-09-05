from collections.abc import Iterator
from typing import Final, cast

from bs4 import BeautifulSoup as Soup
from bs4 import Tag
import httpx

from eksi import session

BASE_URL: Final = "https://eksisozluk.com"

# CSS Selectors
ENTRY_LIST: Final = "ul#entry-item-list"
ENTRY_ITEM: Final = "li[data-id]"
ENTRY_CONTENT: Final = "div.content"
ENTRY_AUTHOR: Final = "a.entry-author"
ENTRY_DATE: Final = "a.entry-date"
PAGER_DIV: Final = "div.pager"
TOPIC_LIST: Final = "ul.topic-list.partial li a"
TOPIC_CONTINUE_LINK: Final = ".quick-index-continue-link-container a"

ERROR_MESSAGES: Final = {404: "Sayfa bulunamadı!", 403: "Erişim engellendi!"}


class EksiError(Exception):
    pass


async def get_soup(url: str) -> Soup:
    try:
        response = await session.get_client().get(url)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code in ERROR_MESSAGES:
            raise EksiError(ERROR_MESSAGES[code]) from e
        if 500 <= code <= 511:
            raise EksiError("Sunucu hatası! Lütfen daha sonra tekrar deneyin.") from e
        raise EksiError(f"HTTP hatası: {code}") from e
    except httpx.TransportError as e:
        reason = str(e).lower()
        if "name resolution" in reason:
            raise EksiError("Internet bağlantısı yok! Lütfen bağlantınızı kontrol edin.") from e
        raise EksiError(f"Bağlantı hatası: {reason}") from e
    return Soup(response.text, "html.parser")


def _clean_content(content: Tag) -> str:
    """Strip HTML from content, replacing external URL links with their href text."""
    for a in content.select("a.url"):
        a.string = f" {a['href']} "
    for tag in content.select("*"):
        tag.unwrap()
    return str(content.text).strip()


def _parse_entry(entry: Tag) -> Iterator[tuple[str, str, str]]:
    content = cast("Tag", entry.select_one(ENTRY_CONTENT))
    author_tag = cast("Tag", entry.select_one(ENTRY_AUTHOR))
    date_tag = cast("Tag", entry.select_one(ENTRY_DATE))
    if text := _clean_content(content):
        yield text, author_tag.text.strip(), date_tag.text.strip()


def _yield_entries(entry_list: Tag) -> Iterator[tuple[str, str, str]]:
    for entry in entry_list.select(ENTRY_ITEM):
        yield from _parse_entry(entry)


def _find_more_data(entry_list: Tag) -> tuple[str, int]:
    """Find the 'X entry daha' link preceding the entry list. Returns (href, count)."""
    if link := entry_list.find_previous_sibling("a", class_="more-data"):
        return cast("str", link["href"]), int(link.text.strip().split()[0])
    return "", 0


def _get_pager_info(soup: Soup) -> tuple[int, int]:
    if pager := soup.select_one(PAGER_DIV):
        return int(cast("str", pager["data-currentpage"])), int(cast("str", pager["data-pagecount"]))
    return 1, 1


def _build_topic_url(topic_path: str, page: int) -> str:
    # Preserve the existing query (e.g. ?a=popular) and append &p=N only for pages 2+, since eksisozluk drops the
    # ?a=popular filter when &p=1 is present - keeping page 1 bare ensures the 'i' (first page) key returns to the
    # initial view instead of falling back to the chronological first page.
    if page <= 1:
        return f"{BASE_URL}{topic_path}"
    separator = "&" if "?" in topic_path else "?"
    return f"{BASE_URL}{topic_path}{separator}p={page}"


async def get_topic_page(
    topic_path: str,
    page: int = 0,
) -> tuple[Iterator[tuple[str, str, str]], str, int, int, int]:
    soup = await get_soup(_build_topic_url(topic_path, page))
    current_page, page_count = _get_pager_info(soup)

    if entry_list := soup.select_one(ENTRY_LIST):
        more_data_href, more_data_count = _find_more_data(entry_list)
        return _yield_entries(entry_list), more_data_href, more_data_count, current_page, page_count

    return iter(()), "", 0, current_page, page_count


def _parse_topics(soup: Soup) -> list[tuple[str, str]]:
    return [(a.text.strip(), str(a["href"])) for a in soup.select(TOPIC_LIST)]


async def get_topics(count: int) -> list[tuple[str, str]]:
    topics: list[tuple[str, str]] = []
    page = 1

    while len(topics) < count:
        soup = await get_soup(f"{BASE_URL}/basliklar/gundem?p={page}")
        topics.extend(_parse_topics(soup))
        if soup.select_one(TOPIC_CONTINUE_LINK) is None:
            break
        page += 1

    return topics[:count]
