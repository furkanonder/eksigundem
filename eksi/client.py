from collections.abc import Iterator
import gzip
from textwrap import fill
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup as Soup

# CSS Selectors
ENTRY_LIST: Final = "ul#entry-item-list"
ENTRY_ITEM: Final = "li[data-id]"
ENTRY_CONTENT: Final = "div.content"
ENTRY_AUTHOR: Final = "a.entry-author"
ENTRY_DATE: Final = "a.entry-date"
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


class EksiClient:
    @staticmethod
    def get_soup(url: str) -> Soup:
        try:
            request = Request(url, headers=HEADERS)
            response = urlopen(request, timeout=10)
            data = response.read()
            # Decompress if the server returned a gzip-encoded response
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

    @staticmethod
    def get_entries(url: str) -> Iterator[tuple[str, str, str]]:
        soup = EksiClient.get_soup(url)
        entries = soup.select_one(ENTRY_LIST).select(ENTRY_ITEM)

        for entry in entries:
            content = entry.select_one(ENTRY_CONTENT)
            author = entry.select_one(ENTRY_AUTHOR).text.strip()
            date_time = entry.select_one(ENTRY_DATE).text.strip()
            # Add url to entry text
            for a in content.select("a[href]"):
                link = a["href"]
                if not link.startswith(("/?q", "/entry")):
                    a.string = f" {link} "
            for tag in content.select("*"):
                tag.unwrap()
            if text := fill(content.text, width=80, break_long_words=False, break_on_hyphens=False).strip():
                yield text, author, date_time

    @staticmethod
    def get_topics(url: str, count: int) -> list[tuple[str, str]]:
        soup = EksiClient.get_soup(url)
        return [(a.text.strip(), a["href"]) for a in soup.select(TOPIC_LIST)][:count]
