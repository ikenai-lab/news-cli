from ddgs import DDGS
import asyncio
import hashlib
import logging

logger = logging.getLogger(__name__)


def generate_id(url: str) -> str:
    """Generates a stable 4-char hash ID from the URL."""
    return hashlib.md5(url.encode()).hexdigest()[:4]


def _search_news_sync(
    query: str, max_results: int, timelimit: str | None
) -> list[dict]:
    query = f"{query} -site:msn.com"
    with DDGS() as ddgs:
        return list(ddgs.news(query, max_results=max_results, timelimit=timelimit))


def _search_text_sync(
    query: str, max_results: int, timelimit: str | None
) -> list[dict]:
    query = f"{query} -site:msn.com"
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results, timelimit=timelimit))


async def search_news(
    query: str, max_results: int = 5, timelimit: str | None = None
) -> list[dict]:
    """
    Searches for news articles using DuckDuckGo (Async wrapper).
    Returns a list of dictionaries with keys: id, title, href, body, date, source.
    """
    seen_urls = set()
    results = []
    try:
        # 1. Try news search
        news_results = await asyncio.to_thread(
            _search_news_sync, query, max_results * 2, timelimit
        )  # Fetch more to allow for filtering

        if news_results:
            for result in news_results:
                url = result.get("url", "")
                source = result.get("source", "").lower()

                # Strict Filters
                if "msn.com" in url.lower() or "msn" in source:
                    continue
                if url in seen_urls:
                    continue

                seen_urls.add(url)
                results.append(
                    {
                        "id": generate_id(url),
                        "title": result.get("title", ""),
                        "href": url,
                        "body": result.get("body", ""),
                        "date": result.get("date", ""),
                        "source": result.get("source", "Unknown"),
                    }
                )
    except Exception as e:
        logger.warning(f"News search error: {e}")

    # 2. Fill gaps with Text Search if needed
    if len(results) < max_results:
        remaining = max_results - len(results)
        try:
            # Fetch extra because of filtering
            text_results = await asyncio.to_thread(
                _search_text_sync, query, remaining * 2, timelimit
            )
            if text_results:
                for result in text_results:
                    url = result.get("href", "")

                    # Strict Filters
                    if "msn.com" in url.lower():
                        continue
                    if url in seen_urls:
                        continue

                    seen_urls.add(url)
                    results.append(
                        {
                            "id": generate_id(url),
                            "title": result.get("title", ""),
                            "href": url,
                            "body": result.get("body", ""),
                            "date": "Unknown",
                            "source": "Web",
                        }
                    )
        except Exception as e:
            logger.warning(f"Text search error: {e}")

    return results[:max_results]


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Performs a general web search for facts/context (not specifically news).
    Returns a list of dictionaries with keys: title, url, snippet.
    """
    results = []
    try:
        raw_results = await asyncio.to_thread(
            _search_text_sync, query, max_results, None
        )

        for result in raw_results:
            results.append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                }
            )

    except Exception as e:
        logger.warning(f"Web search error: {e}")

    return results[:max_results]
