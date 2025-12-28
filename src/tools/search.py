from ddgs import DDGS

def search_news(query: str, max_results: int = 5, timelimit: str | None = None) -> list[dict]:
    """
    Searches for news articles using DuckDuckGo.
    Returns a list of dictionaries with keys: title, href, body, date.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        timelimit: Time filter - 'd' (day), 'w' (week), 'm' (month), 'y' (year), or None
    """
    results = []
    import time
    
    ddgs = DDGS()
    
    # Try news search first with retries
    for attempt in range(3):
        try:
            news_results = ddgs.news(query, max_results=max_results, timelimit=timelimit)
            if news_results:
                for result in news_results:
                    results.append({
                        "title": result.get("title", ""),
                        "href": result.get("url", ""),
                        "body": result.get("body", ""),
                        "date": result.get("date", "")
                    })
                return results
        except Exception as e:
            print(f"News search failed (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(1) # Simple backoff
    
    # Fallback to text search if news search failed or returned nothing
    print("Falling back to text search...")
    try:
        text_results = ddgs.text(query, max_results=max_results)
        if text_results:
            for result in text_results:
                results.append({
                    "title": result.get("title", ""),
                    "href": result.get("href", ""),
                    "body": result.get("body", ""),
                    "date": "Unknown" 
                })
    except Exception as e:
        print(f"Text search failed: {e}")
        
    return results
