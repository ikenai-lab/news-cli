from ddgs import DDGS
from rich.console import Console
import asyncio
from src.tools.scraper import scrape_article

console = Console()

TRUSTED_DOMAINS = [
    "snopes.com", "politifact.com", "factcheck.org", "reuters.com", "apnews.com",
    "usatoday.com", "bbc.com", "npr.org", "checkyourfact.com"
]

def _search_sync(query: str, max_results: int) -> list:
    try:
        ddgs = DDGS()
        return list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []

async def verify_claim(claim: str, max_sources: int = 5) -> dict:
    """
    Verifies a claim by searching for fact-checks and scraping trusted sources.
    Returns a dict with 'sources' and optional 'best_evidence' content.
    """
    # 1. Generate adversarial queries
    site_query = " OR ".join([f"site:{d}" for d in TRUSTED_DOMAINS])
    queries = [
        f"{claim} ({site_query})",
        f"{claim} fact check -site:msn.com",
        f"{claim} fake debunked -site:msn.com",
        f"{claim} true or false -site:msn.com"
    ]
    
    all_results = []
    seen_urls = set()
    
    # Run searches (could be parallel, but rate limits might be an issue, so sequential is safer for ddgs)
    for q in queries:
        results = await asyncio.to_thread(_search_sync, q, 3)
        for res in results:
            if res['href'] not in seen_urls:
                seen_urls.add(res['href'])
                all_results.append(res)
                
    # 2. Filter and Prioritize
    trusted_results = []
    other_results = []
    
    for res in all_results:
        is_trusted = any(d in res['href'] for d in TRUSTED_DOMAINS)
        normalized = {
            "title": res.get("title", ""),
            "url": res.get("href", ""),
            "snippet": res.get("body", ""),
            "is_trusted": is_trusted
        }
        if is_trusted:
            trusted_results.append(normalized)
        else:
            other_results.append(normalized)
            
    # Combine (Trusted first)
    final_sources = trusted_results + other_results
    final_sources = final_sources[:max_sources] # Top N
    
    best_evidence = None
    
    # 3. Deep Verification (Scrape top trusted result)
    if trusted_results:
        top_url = trusted_results[0]['url']
        # console.print(f"[dim]Found trusted source: {top_url}. Reading...[/dim]")
        try:
            content = await scrape_article(top_url)
            if not content.startswith("Error"):
                best_evidence = content[:6000] # Limit context
        except Exception as e:
            console.print(f"[dim]Error scraping verification: {e}[/dim]")
            
    return {
        "claim": claim,
        "sources": final_sources,
        "source_count": len(final_sources),
        "best_evidence": best_evidence
    }


def extract_claims_prompt(article_content: str) -> str:
    """
    Returns a prompt for the LLM to extract verifiable claims from an article.
    """
    return f"""Extract the key factual claims from this article that can be verified.
Focus on:
- Statistics and numbers
- Quotes attributed to people
- Historical facts
- Scientific claims
- Predictions with specific details

Return ONLY a numbered list of claims, one per line. Maximum 5 claims.
If no verifiable claims exist, or if the content looks like a technical error (e.g. "Access Denied", "Security Service", "Cloudflare"), return "NO_CLAIMS".

Article:
{article_content[:4000]}

Claims:"""
