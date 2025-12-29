"""
Robust article scraper using Crawl4AI (stealth mode), Cloudscraper, 
Jina Reader, Archive.org, and other fallbacks.
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

def scrape_with_crawl4ai(url: str) -> str:
    """
    Primary Method: Uses Crawl4AI with stealth mode.
    Uses fit_markdown with PruningContentFilter for clean, article-only content.
    """
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        
        async def _crawl():
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
            )
            
            # Use PruningContentFilter to remove navigation, ads, boilerplate
            md_generator = DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(
                    threshold=0.45,  # Filter aggressiveness (0-1)
                    threshold_type="fixed",
                    min_word_threshold=30,  # Minimum words per block
                )
            )
            
            run_config = CrawlerRunConfig(
                wait_until="domcontentloaded",
                page_timeout=30000,
                markdown_generator=md_generator,
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                if result.success:
                    # Prefer fit_markdown (filtered) over raw markdown
                    content = None
                    if hasattr(result.markdown, 'fit_markdown') and result.markdown.fit_markdown:
                        content = result.markdown.fit_markdown
                    elif isinstance(result.markdown, str) and len(result.markdown) > 100:
                        content = result.markdown
                    
                    if content and len(content) > 100:
                        if "error" not in content.lower()[:200]:
                            return content
            return None
        
        result = asyncio.run(_crawl())
        if result:
            return result
    except Exception as e:
        console.print(f"[dim]Crawl4AI failed: {type(e).__name__}[/dim]")
    return None

def scrape_with_cloudscraper(url: str) -> str:
    """
    Secondary Method: Uses Cloudscraper for Cloudflare-protected sites.
    This is a drop-in requests replacement that bypasses Cloudflare.
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

def scrape_with_jina(url: str) -> str:
    """
    Tertiary Method: Uses Jina Reader (r.jina.ai) as a proxy.
    This bypasses local IP blocks and returns clean markdown.
    """
    jina_url = f"https://r.jina.ai/{url}"
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(jina_url)
            text = response.text
            
            if response.status_code == 200 and len(text) > 100:
                lower_text = text.lower()
                invalid_markers = [
                    "access denied",
                    "cloudflare",
                    "shadow dom that are currently hidden",
                    "enable javascript"
                ]
                
                if any(marker in lower_text for marker in invalid_markers):
                    console.print("[dim]Jina returned low-quality/blocked content[/dim]")
                    return None
                    
                return text
    except Exception as e:
        console.print(f"[dim]Jina proxy failed: {e}[/dim]")
    return None

def scrape_with_archive(url: str) -> str:
    """
    Fallback Method: Uses Archive.org (Wayback Machine).
    """
    archive_url = f"https://web.archive.org/web/{url}"
    try:
        with httpx.Client(headers=HEADERS, timeout=20.0, follow_redirects=True) as client:
            response = client.get(archive_url)
            if response.status_code == 200:
                return _extract_content(response.text)
    except Exception as e:
        console.print(f"[dim]Archive.org fallback failed: {e}[/dim]")
    return None

def scrape_with_google_cache(url: str) -> str:
    """
    Fallback Method: Uses Google Cache.
    """
    cache_url = f"http://webcache.googleusercontent.com/search?q=cache:{url}"
    try:
        with httpx.Client(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
            response = client.get(cache_url)
            if response.status_code == 200:
                content = _extract_content(response.text)
                if content:
                    if "redirected within a few seconds" in content.lower():
                        console.print("[dim]Google Cache returned redirect stub[/dim]")
                        return None
                    return content
    except Exception as e:
        console.print(f"[dim]Google Cache fallback failed: {e}[/dim]")
    return None

def _extract_content(html_content: str) -> str:
    """Helper to extract markdown from HTML using Trafilatura or Readability."""
    try:
        result = trafilatura.extract(html_content, output_format="markdown", include_tables=True)
        if result and len(result) > 100:
            return result
            
        doc = Document(html_content)
        summary = doc.summary()
        text = re.sub(r'<[^>]+>', '\n', summary)
        text = re.sub(r'\n\s*\n', '\n\n', text).strip()
        if len(text) > 100:
            return text
    except Exception:
        pass
    return None

def scrape_article(url: str) -> str:
    """
    Main scaffolding for robust scraping.
    Strategy: Crawl4AI -> Cloudscraper -> Jina -> Archive -> Direct
    """
    console.print(f"[dim]Scraping: {url}[/dim]")
    
    # 1. Try Crawl4AI (Best stealth browser)
    content = scrape_with_crawl4ai(url)
    if content:
        console.print("[dim]✓ Fetched via Crawl4AI[/dim]")
        return content
    
    # 2. Try Cloudscraper (Cloudflare bypass)
    content = scrape_with_cloudscraper(url)
    if content:
        console.print("[dim]✓ Fetched via Cloudscraper[/dim]")
        return content
        
    # 3. Try Jina Reader (Proxy)
    content = scrape_with_jina(url)
    if content:
        console.print("[dim]✓ Fetched via Jina Reader[/dim]")
        return content
        
    # 4. Try Archive.org
    content = scrape_with_archive(url)
    if content:
        console.print("[dim]✓ Fetched via Archive.org[/dim]")
        return content
        
    # 5. Try Direct Fetch
    try:
        with httpx.Client(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
            response = client.get(url)
            if response.status_code == 200:
                content = _extract_content(response.text)
                if content:
                    console.print("[dim]✓ Fetched via Direct[/dim]")
                    return content
    except Exception as e:
        console.print(f"[dim]Direct fetch failed: {e}[/dim]")
        
    # 6. Try Google Cache
    content = scrape_with_google_cache(url)
    if content:
        console.print("[dim]✓ Fetched via Google Cache[/dim]")
        return content
        
    return f"Error: Unable to scrape content. Try `/open` to view in browser.\nURL: {url}"

