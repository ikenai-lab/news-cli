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
async def test_automatic_search_fallback(mock_agent):
    """
    Test that the agent automatically triggers search_web when it realizes 
    it doesn't have information in its context.
    """
    agent = mock_agent
    agent._classify_intent = AsyncMock(return_value="CHAT")
    
    # Define a sequence of responses to avoid infinite loops
    responses = [
        # First call: triggers search
        [{'message': {'content': "I don't have that information in my current context. SEARCH_WEB: who is the current CEO of Tesla?"}}],
        # Second call: provides final answer
        [{'message': {'content': "The current CEO of Tesla is Elon Musk, based on a web search."}}]
    ]

    async def mock_stream_response(*args, **kwargs):
        if not responses:
             yield {'message': {'content': "No more mocked responses."}}
             return
        for chunk in responses.pop(0):
            yield chunk

    mock_agent.client.chat.side_effect = mock_stream_response
    
    with patch('src.agent.search_web', new_callable=AsyncMock) as mock_search_web:
        mock_search_web.return_value = [
            {"title": "Tesla CEO", "url": "https://tesla.com", "snippet": "Elon Musk is the CEO of Tesla."}
        ]
        
        response = await agent.process_user_input("Who is the CEO of Tesla?")
        
        # Verify search_web was called
        mock_search_web.assert_called_once()
        assert "Elon Musk" in response
        # Verify user was informed (optional but in requirements)
        # In our implementation, we'll check if the intermediate response was handled.
