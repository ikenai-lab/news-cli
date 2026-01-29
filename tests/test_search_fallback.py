import pytest
from unittest.mock import AsyncMock, patch
from src.agent import NewsAgent

@pytest.fixture
def mock_agent():
    with patch('ollama.AsyncClient') as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        agent = NewsAgent()
        return agent

@pytest.mark.asyncio
async def test_proactive_search_rag(mock_agent):
    """
    Test that _gather_context correctly searches, filters, and scrapes.
    """
    agent = mock_agent
    
    # Mock search results including a generic homepage to filter
    mock_results = [
        {"title": "Generic", "url": "https://www.msn.com/", "snippet": "Home"},
        {"title": "Real News", "url": "https://techcrunch.com/article", "snippet": "Useful info"}
    ]
    
    with patch('src.agent.search_web', new_callable=AsyncMock) as mock_search_web, \
         patch('src.agent.scrape_article', new_callable=AsyncMock) as mock_scrape:
        
        mock_search_web.return_value = mock_results
        mock_scrape.return_value = "Scraped content from TechCrunch"
        
        context_msg = await agent._gather_context("Who is CEO?")
        
        # Verify search was called
        mock_search_web.assert_called_once()
        
        # Verify scraping called on the VALID result (TechCrunch), not MSN
        mock_scrape.assert_called_with("https://techcrunch.com/article")
        
        # Verify context message construction
        assert "External Context" in context_msg
        assert "Scraped content from TechCrunch" in context_msg