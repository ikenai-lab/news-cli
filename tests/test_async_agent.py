import pytest
from unittest.mock import MagicMock, AsyncMock, patch

@pytest.fixture
def mock_agent():
    with patch('ollama.AsyncClient') as mock_client_cls:
        # Prevent actual API calls
        mock_client = AsyncMock()
        mock_client.chat.return_value = {'message': {'content': 'Mock Response'}}
        mock_client_cls.return_value = mock_client
        
        from src.agent import NewsAgent
        agent = NewsAgent()
        return agent

@pytest.mark.asyncio
async def test_prune_history(mock_agent):
    """Should keep system prompt + last 6 messages."""
    agent = mock_agent
    # Fill history > 7
    agent.history = [{"role": "system"}] + [{"role": "user", "content": f"msg {i}"} for i in range(10)]
    
    agent._prune_history()
    
    assert len(agent.history) == 7
    assert agent.history[0]["role"] == "system"
    assert agent.history[-1]["content"] == "msg 9"

@pytest.mark.asyncio
async def test_intent_classification_regex(mock_agent):
    """Should detect intent via regex without LLM."""
    # Test READ regex
    # We need to populate cache first for read to match
    mock_agent.search_cache = {"a1b2": {"url": "http://example.com"}}
    
    # We mock _scrape_and_summarize to avoid side effects
    mock_agent._scrape_and_summarize = AsyncMock(return_value="Scraped")
    
    await mock_agent.process_user_input("read a1b2")
    
    mock_agent._scrape_and_summarize.assert_called_with("a1b2")

@pytest.mark.asyncio
async def test_intent_classification_search_fallback(mock_agent):
    """Should detect search intent via keywords."""
    mock_agent._handle_search_intent = AsyncMock(return_value="Searched")
    
    await mock_agent.process_user_input("latest tech news")
    
    mock_agent._handle_search_intent.assert_called()

@pytest.mark.asyncio
async def test_full_search_flow(mock_agent):
    """Test full search flow with mocked tools."""
    # Mock search_news, print_search_results, _chat_with_llm
    with patch('src.agent.search_news', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [{"id": "a1b2", "title": "Test News", "href": "http://test.com", "body": "...", "date": "2024"}]
        
        with patch('src.agent.print_search_results') as mock_print:
            mock_agent._extract_date_context = AsyncMock(return_value=("query", None))
            mock_agent._chat_with_llm = AsyncMock(return_value="Summary")
            
            await mock_agent._handle_search_intent("test query")
            
            assert "a1b2" in mock_agent.search_cache
            mock_print.assert_called() 
