from ddgs import DDGS
import asyncio
import hashlib

def generate_id(url: str) -> str:
    """Generates a stable 4-char hash ID from the URL."""
    return hashlib.md5(url.encode()).hexdigest()[:4]

def _search_news_sync(query: str, max_results: int, timelimit: str | None) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.news(query, max_results=max_results, timelimit=timelimit))

def _search_text_sync(query: str, max_results: int, timelimit: str | None) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results, timelimit=timelimit))

async def search_news(query: str, max_results: int = 5, timelimit: str | None = None) -> list[dict]:
    """
    Searches for news articles using DuckDuckGo (Async wrapper).
    Returns a list of dictionaries with keys: id, title, href, body, date, source.
    """
    results = []
    
    try:
        # Try news search
        news_results = await asyncio.to_thread(_search_news_sync, query, max_results, timelimit)
        
        if news_results:
            for result in news_results:
                url = result.get("url", "")
                results.append({
                    "id": generate_id(url),
                    "title": result.get("title", ""),
                    "href": url,
                    "body": result.get("body", ""),
                    "date": result.get("date", ""),
                    "source": result.get("source", "Unknown")
                })
            return results
    except Exception as e:
        print(f"News search error: {e}")
    
    # Fallback to text search
    if not results:
        try:
            text_results = await asyncio.to_thread(_search_text_sync, query, max_results, timelimit)
            if text_results:
                for result in text_results:
                    url = result.get("href", "")
                    results.append({
                        "id": generate_id(url),
                        "title": result.get("title", ""),
                        "href": url,
                        "body": result.get("body", ""),
                        "date": "Unknown",
                        "source": "Web"
                    })
        except Exception as e:
            print(f"Text search error: {e}")
            
    return results
