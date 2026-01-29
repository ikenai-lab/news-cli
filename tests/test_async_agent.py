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
async def test_intent_classification_factual(mock_agent):
    """Should classify factual questions as FACTUAL and trigger context gathering."""
    mock_agent._classify_intent = AsyncMock(return_value="FACTUAL")
    mock_agent._gather_context = AsyncMock(return_value="Context found")
    mock_agent._chat_with_llm = AsyncMock(return_value="Answer")
    
    await mock_agent.process_user_input("Who is CEO of Tesla?")
    
    mock_agent._gather_context.assert_called()
    # History: [System, Context] (since chat_with_llm is mocked and doesn't append)
    # So the LAST element [-1] should be the context.
    assert mock_agent.history[-1]['content'] == "Context found"

@pytest.mark.asyncio
async def test_intent_classification_search_fallback(mock_agent):
    """Should detect search intent via keywords."""
    mock_agent._handle_search_intent = AsyncMock(return_value="Searched")
    mock_agent._classify_intent = AsyncMock(return_value="SEARCH_NEWS")
    
    await mock_agent.process_user_input("latest tech news")
    
    mock_agent._handle_search_intent.assert_called()

@pytest.mark.asyncio
async def test_broad_news_query_bypasses_refinement(mock_agent):
    """Broad queries like 'latest news' should skip LLM refinement."""
    # Mock search_news to avoid network calls
    with patch('src.agent.search_news', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = []
        
        # Ensure refine is NOT called
        mock_agent._refine_search_query = AsyncMock()
        
        await mock_agent._handle_search_intent("latest india news")
        
        mock_agent._refine_search_query.assert_not_called()
        mock_search.assert_called_with("latest india news", max_results=mock_agent.article_limit, timelimit=None)

@pytest.mark.asyncio
async def test_query_refinement_topic_shift(mock_agent):
    """Should ignore context for new topics."""
    # Mock history with previous topic
    mock_agent.history = [
        {"role": "user", "content": "Who is Elon Musk?"},
        {"role": "assistant", "content": "Elon Musk is the CEO of Tesla."}
    ]
    
    # Mock LLM response to indicate NEW topic behavior
    mock_agent.client.chat.return_value = {
        'message': {'content': "TIMELIMIT: NONE\nQUERY: latest AI news"}
    }
    
    query, _ = await mock_agent._refine_search_query("latest AI news")
    
    assert "Elon" not in query
    assert "Tesla" not in query
    assert "AI" in query

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
