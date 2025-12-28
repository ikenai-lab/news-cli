"""
Robust article scraper with multiple fallback methods.
"""
import httpx
import trafilatura
from readability import Document
from rich.console import Console

console = Console()

# Browser-like headers to avoid being blocked
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def scrape_article(url: str) -> str:
    """
    Fetches and extracts the main text content from a URL.
    Uses multiple methods with fallbacks for robustness.
    Returns the content in Markdown format, or an error message.
    """
    html_content = None
    
    # Step 1: Try fetching with httpx (custom headers)
    try:
        with httpx.Client(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            html_content = response.text
    except Exception as e:
        console.print(f"[dim]httpx fetch failed: {e}, trying trafilatura...[/dim]")
    
    # Step 2: Fallback to trafilatura's fetch (handles some edge cases)
    if not html_content:
        try:
            html_content = trafilatura.fetch_url(url)
        except Exception as e:
            console.print(f"[dim]trafilatura fetch failed: {e}[/dim]")
    
    if not html_content:
        return f"Error: Failed to fetch URL: {url}"
    
    # Step 3: Try extraction with trafilatura (primary)
    try:
        result = trafilatura.extract(
            html_content, 
            output_format="markdown",
            include_comments=False,
            include_tables=True,
            no_fallback=False  # Enable fallback heuristics
        )
        if result and len(result) > 100:  # Minimum viable content
            return result
    except Exception as e:
        console.print(f"[dim]trafilatura extract failed: {e}[/dim]")
    
    # Step 4: Fallback to readability-lxml
    try:
        doc = Document(html_content)
        content = doc.summary()
        
        # Convert HTML to plain text (basic cleanup)
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '\n', content)
        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        if text and len(text) > 100:
            return text
    except Exception as e:
        console.print(f"[dim]readability fallback failed: {e}[/dim]")
    
    # Step 5: Use playwright for JavaScript-rendered content (MSN, etc.)
    console.print("[dim]Trying browser-based extraction...[/dim]")
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=20000)
            
            # Wait a bit for content to load
            page.wait_for_timeout(2000)
            
            # Get the rendered HTML
            rendered_html = page.content()
            browser.close()
            
            # Try extraction again with rendered content
            if rendered_html:
                result = trafilatura.extract(rendered_html, output_format="markdown")
                if result and len(result) > 100:
                    return result
                
                # Try readability on rendered content
                doc = Document(rendered_html)
                content = doc.summary()
                text = re.sub(r'<[^>]+>', '\n', content)
                text = re.sub(r'\n\s*\n', '\n\n', text)
                text = text.strip()
                if text and len(text) > 100:
                    return text
    except Exception as e:
        console.print(f"[dim]playwright fallback failed: {e}[/dim]")
    
    # Step 6: Last resort - extract any text from body
    try:
        import re
        # Find body content
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            body = body_match.group(1)
            # Remove scripts and styles
            body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL | re.IGNORECASE)
            body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL | re.IGNORECASE)
            # Remove tags
            text = re.sub(r'<[^>]+>', ' ', body)
            # Clean whitespace
            text = ' '.join(text.split())
            if text and len(text) > 200:
                return text[:10000]  # Limit to prevent huge outputs
    except:
        pass
    
    return f"Error: This site blocks automated scraping. Try `/open` to view in browser.\nURL: {url}"
