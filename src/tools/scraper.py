"""
Robust article scraper using Cloudscraper, Nodriver (stealth), 
Archive.org, and other fallbacks. Fully Async.
"""
import httpx
import trafilatura
from readability import Document
from rich.console import Console
import re
import asyncio

console = Console()

# Browser-like headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

async def scrape_with_nodriver(url: str) -> str:
    """
    Stealth Method: Uses Nodriver (no-driver based automation) to bypass bot detection.
    Lighter and more stealthy than Selenium/Playwright.
    """
    try:
        import nodriver as n
        
        browser = await n.start(headless=True)
        try:
            tab = await browser.get(url)
            # Wait for content to load
            await tab.sleep(2) 
            
            content_html = await tab.get_content()
            
            if content_html:
                return _extract_content(content_html)
                
        finally:
            browser.stop()
            
    except ImportError:
        console.print("[dim]Nodriver not installed. Skipping.[/dim]")
    except Exception as e:
        console.print(f"[dim]Nodriver failed: {e}[/dim]")
    return None

def scrape_with_cloudscraper_sync(url: str) -> str:
    """
    Secondary Method: Uses Cloudscraper for Cloudflare-protected sites.
    Sync method to be run in executor.
    """
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=20)
        if response.status_code == 200:
            content = _extract_content(response.text)
            if content:
                return content
    except Exception as e:
        console.print(f"[dim]Cloudscraper failed: {e}[/dim]")
    return None

async def scrape_with_archive(url: str) -> str:
    """
    Fallback Method: Uses Archive.org (Wayback Machine).
    """
    archive_url = f"https://web.archive.org/web/{url}"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=20.0, follow_redirects=True) as client:
            response = await client.get(archive_url)
            if response.status_code == 200:
                return _extract_content(response.text)
    except Exception as e:
        console.print(f"[dim]Archive.org fallback failed: {e}[/dim]")
    return None

async def fetch_direct(url: str) -> str:
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                content = _extract_content(response.text)
                if content:
                    return content
    except Exception as e:
        console.print(f"[dim]Direct fetch failed: {e}[/dim]")
    return None

def _is_blocked(text: str) -> bool:
    """Checks for common anti-bot blocking messages."""
    text_lower = text.lower()
    block_phrases = [
        "cloudflare", "attention required", "access denied", 
        "security service", "challenge-platform", "enable cookies",
        "captcha", "human verification", "ray id"
    ]
    if len(text) < 500: # Short content + block phrase = likely block
         if any(p in text_lower for p in block_phrases):
             return True
             
    # Sometimes trafilatura extracts JUST the error message
    if "security service to protect itself from online attacks" in text_lower:
        return True
        
    return False

def _extract_content(html_content: str) -> str:
    """Helper to extract markdown from HTML using Trafilatura or Readability."""
    if not html_content: return None
    
    # Pre-check HTML for obvious blocks before extraction (optimization)
    if "cf-challenge" in html_content or "Cloudflare Ray ID" in html_content:
        # Check if it's main content or just footer? 
        # Usually blocking page is small.
        if len(html_content) < 5000: # arbitrary small-ish size for full HTML
             pass # Let's be careful, might be false positive. 
             # Safe to rely on extracted text check?
    
    try:
        result = trafilatura.extract(html_content, output_format="markdown", include_tables=True)
        if result and len(result) > 100:
            if not _is_blocked(result):
                return result
            else:
                pass # Console log? console.print("[dim]Detected anti-bot block in content.[/dim]")
            
        doc = Document(html_content)
        summary = doc.summary()
        text = re.sub(r'<[^>]+>', '\n', summary)
        text = re.sub(r'\n\s*\n', '\n\n', text).strip()
        if len(text) > 100:
            if not _is_blocked(text):
                return text
    except Exception:
        pass
    return None

async def scrape_article(url: str) -> str:
    """
    Main scaffolding for robust scraping.
    Strategy: Cloudscraper -> Nodriver -> Archive -> Direct
    """
    console.print(f"[dim]Scraping: {url}[/dim]")
    
    # 1. Try Cloudscraper (Fast, Cloudflare bypass) - Run in executor
    content = await asyncio.to_thread(scrape_with_cloudscraper_sync, url)
    if content:
        console.print("[dim]✓ Fetched via Cloudscraper[/dim]")
        return content
    
    # 2. Try Nodriver (Async Stealth Browser)
    console.print("[dim]Attempting stealth scrape with Nodriver...[/dim]")
    content = await scrape_with_nodriver(url)
    if content:
        console.print("[dim]✓ Fetched via Nodriver[/dim]")
        return content

    # 3. Try Archive.org (Fallback for hard blocks)
    content = await scrape_with_archive(url)
    if content:
        console.print("[dim]✓ Fetched via Archive.org[/dim]")
        return content
        
    # 4. Try Direct Fetch (Last resort, might fail if protected)
    content = await fetch_direct(url)
    if content:
        console.print("[dim]✓ Fetched via Direct[/dim]")
        return content
        
    return f"Error: Unable to scrape content. Try `/open` to view in browser.\nURL: {url}"
