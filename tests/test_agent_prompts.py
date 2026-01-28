import pytest
from unittest.mock import AsyncMock, patch
from src.agent import NewsAgent

@pytest.fixture
def mock_agent():
    with patch('ollama.AsyncClient') as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.chat.return_value = {'message': {'content': 'Mock Response'}}
        mock_client_cls.return_value = mock_client
        
        agent = NewsAgent()
        return agent

@pytest.mark.asyncio
async def test_system_prompt_content(mock_agent):
    """Verify the system prompt contains specific 'Balanced Context' and fallback instructions."""
    system_prompt = mock_agent.history[0]['content']
    
    # Check for Balanced Context definition
    assert "concise sentence stating the main claim" in system_prompt
    assert "2-3 bullet points" in system_prompt
    
    # Check for Fallback instruction
    assert "explicitly ask: 'I don't have that information" in system_prompt
    assert "Should I search the web" in system_prompt

@pytest.mark.asyncio
async def test_summarize_prompt_structure(mock_agent):
    """Verify the summarization prompt explicitly requests the format."""
    mock_agent.search_cache = {"123": {"url": "http://test.com", "title": "Test Title"}}
    
    with patch('src.agent.scrape_article', new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = "Article Content"
        mock_agent._prune_history = AsyncMock() # prevent pruning from messing up history inspection
        mock_agent._chat_with_llm = AsyncMock(return_value="Summary")
        
        await mock_agent._scrape_and_summarize("123")
        
        # Check the user message added to history
        last_msg = mock_agent.history[-1]['content']
        assert "Summarize the following article using the 'Balanced Context' format" in last_msg
        assert "Main Claim + 2-3 supporting bullet points" in last_msg
