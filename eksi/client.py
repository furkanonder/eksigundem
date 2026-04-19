from collections.abc import Iterator
import gzip
from textwrap import fill
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup as Soup
from bs4 import Tag

BASE_URL: Final = "https://eksisozluk.com"

# CSS Selectors
ENTRY_LIST: Final = "ul#entry-item-list"
ENTRY_ITEM: Final = "li[data-id]"
ENTRY_CONTENT: Final = "div.content"
ENTRY_AUTHOR: Final = "a.entry-author"
ENTRY_DATE: Final = "a.entry-date"
PAGER_DIV: Final = "div.pager"
TOPIC_LIST: Final = "ul.topic-list.partial li a"

# HTTP Headers (mimic Firefox to avoid being blocked)
HEADERS: Final = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",  # Accept types
    "Accept-Language": "tr-TR,tr;q=0.9",  # Turkish locale
    "Accept-Encoding": "gzip",  # Enable compression
    "Alt-Used": "eksisozluk.com",  # Firefox HTTP/2 coalescing header
    "Connection": "keep-alive",  # Reuse TCP connection
    "Upgrade-Insecure-Requests": "1",  # Prefer HTTPS
    # Sec-Fetch headers: tell the server this is a trusted user-initiated request
    "Sec-Fetch-Dest": "document",  # Fetching a web page
    "Sec-Fetch-Mode": "navigate",  # Top-level navigation (not fetch/XHR)
    "Sec-Fetch-Site": "none",  # Direct URL entry (not from another site)
    "Sec-Fetch-User": "?1",  # Triggered by user action (click/keypress)
}


class EksiError(Exception):
    pass


def get_soup(url: str) -> Soup:
    try:
        request = Request(url, headers=HEADERS)
        response = urlopen(request, timeout=10)
        data = response.read()
        if response.headers.get("Content-Encoding", "") == "gzip":
            data = gzip.decompress(data)
        return Soup(data.decode("utf-8"), "html.parser")
    except HTTPError as e:
        error_messages = {404: "Sayfa bulunamadı!", 403: "Erişim engellendi!"}
        if e.code in error_messages:
            raise EksiError(error_messages[e.code]) from e
        if 500 <= e.code <= 511:
            raise EksiError("Sunucu hatası! Lütfen daha sonra tekrar deneyin.") from e
        raise EksiError(f"HTTP hatası: {e.code}") from e
    except URLError as e:
        if "name resolution" in str(e.reason).lower():
            raise EksiError("Internet bağlantısı yok! Lütfen bağlantınızı kontrol edin.") from e
        raise EksiError(f"Bağlantı hatası: {e.reason}") from e


def _clean_content(content: Tag) -> str:
    """Strip HTML from content, replacing external URL links with their href text."""
    for a in content.select("a.url"):
        a.string = f" {a['href']} "
    for tag in content.select("*"):
        tag.unwrap()
    return fill(content.text, width=80, break_long_words=False, break_on_hyphens=False).strip()


def _parse_entry(entry: Tag) -> Iterator[tuple[str, str, str]]:
    content = entry.select_one(ENTRY_CONTENT)
    author = entry.select_one(ENTRY_AUTHOR).text.strip()
    date_time = entry.select_one(ENTRY_DATE).text.strip()
    if text := _clean_content(content):
        yield text, author, date_time


def _yield_entries(entry_list: Tag) -> Iterator[tuple[str, str, str]]:
    for entry in entry_list.select(ENTRY_ITEM):
        yield from _parse_entry(entry)


def _find_more_data(entry_list: Tag) -> tuple[str, int]:
    """Find the 'X entry daha' link preceding the entry list. Returns (href, count)."""
    if link := entry_list.find_previous_sibling("a", class_="more-data"):
        return link["href"], int(link.text.strip().split()[0])
    return "", 0


def _get_pager_info(soup: Soup) -> tuple[int, int]:
    if pager := soup.select_one(PAGER_DIV):
        return int(pager["data-currentpage"]), int(pager["data-pagecount"])
    return 1, 1


def _build_topic_url(topic_path: str, page: int) -> str:
    """Preserve the original query on an initial load (page=0), strip it for explicit pagination."""
    if page == 0:
        return f"{BASE_URL}{topic_path}"
    base_path = topic_path.split("?", maxsplit=1)[0]
    return f"{BASE_URL}{base_path}?p={page}"


def get_topic_page(topic_path: str, page: int = 0) -> tuple[Iterator[tuple[str, str, str]], str, int, int, int]:
    soup = get_soup(_build_topic_url(topic_path, page))
    entry_list = soup.select_one(ENTRY_LIST)
    current_page, page_count = _get_pager_info(soup)
    more_data_href, more_data_count = _find_more_data(entry_list)
    return _yield_entries(entry_list), more_data_href, more_data_count, current_page, page_count


def get_topics(count: int) -> list[tuple[str, str]]:
    soup = get_soup(BASE_URL)
    return [(a.text.strip(), a["href"]) for a in soup.select(TOPIC_LIST)][:count]
