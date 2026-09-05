from typing import Final

import httpx

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


class _SessionHolder:
    client: httpx.AsyncClient | None = None


_holder = _SessionHolder()


def open_session() -> None:
    """
    One long-lived client for the whole app: its connection pool keeps the TCP+TLS connection to eksisozluk.com alive
    between requests: so we pay the handshake once instead of per request.
    """
    _holder.client = httpx.AsyncClient(
        headers=HEADERS,
        timeout=10.0,
        follow_redirects=True,
    )


async def close_session() -> None:
    assert _holder.client is not None, "close_session() called before open_session()"
    await _holder.client.aclose()


def get_client() -> httpx.AsyncClient:
    assert _holder.client is not None, "session accessed before open_session()"
    return _holder.client
