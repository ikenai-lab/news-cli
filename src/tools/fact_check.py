"""
Fact-checking tool for verifying claims in news articles.
"""
from ddgs import DDGS
from rich.console import Console

console = Console()


def verify_claim(claim: str, max_sources: int = 5) -> dict:
    """
    Searches fact-checking sites and general web to verify a claim.
    
    Args:
        claim: The claim to verify
        max_sources: Maximum number of sources to return
        
    Returns:
        dict with 'sources' list and 'summary'
    """
    ddgs = DDGS()
    
    # Search fact-checking sites specifically
    fact_check_sites = "site:snopes.com OR site:factcheck.org OR site:politifact.com OR site:reuters.com/fact-check"
    
    sources = []
    
    # Search 1: Fact-checking sites
    try:
        query = f"{claim} {fact_check_sites}"
        results = ddgs.text(query, max_results=max_sources)
        for res in results:
            sources.append({
                "title": res.get("title", ""),
                "url": res.get("href", ""),
                "snippet": res.get("body", ""),
                "type": "fact-check"
            })
    except Exception as e:
        console.print(f"[dim]Fact-check search error: {e}[/dim]")
    
    # Search 2: General verification (if not enough fact-check results)
    if len(sources) < max_sources:
        try:
            results = ddgs.text(f'"{claim}" verify OR fact OR true OR false', max_results=max_sources - len(sources))
            for res in results:
                sources.append({
                    "title": res.get("title", ""),
                    "url": res.get("href", ""),
                    "snippet": res.get("body", ""),
                    "type": "general"
                })
        except:
            pass
    
    return {
        "claim": claim,
        "sources": sources,
        "source_count": len(sources)
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
If no verifiable claims exist, return "NO_CLAIMS".

Article:
{article_content[:4000]}

Claims:"""
