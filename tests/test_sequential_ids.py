import pytest
from unittest.mock import MagicMock, AsyncMock, patch

@pytest.mark.asyncio
async def test_agent_searches_and_sets_id_map():
    """Verify that search populates id_map correctly."""
    from src.agent import NewsAgent
    
    agent = NewsAgent()
    
    # Mock search_news to return specific hash IDs
    with patch('src.agent.search_news', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {"id": "aabb", "title": "News 1", "href": "url1", "date": "2025", "body": ""},
            {"id": "ccdd", "title": "News 2", "href": "url2", "date": "2025", "body": ""}
        ]
        
        with patch('src.agent.print_search_results') as mock_print:
            with patch.object(agent, '_chat_with_llm', new_callable=AsyncMock) as mock_chat:
                mock_chat.return_value = "Summary"
                agent._extract_date_context = AsyncMock(return_value=("query", None))
                
                await agent._handle_search_intent("test")
                
                # Check id_map
                assert "1" in agent.id_map
                assert "2" in agent.id_map
                assert agent.id_map["1"] == "aabb"
                assert agent.id_map["2"] == "ccdd"
                
                # Check search_cache (should map Hash ID -> Content)
                assert "aabb" in agent.search_cache
                assert agent.search_cache["aabb"]["title"] == "News 1"

@pytest.mark.asyncio
async def test_agent_read_uses_id_map():
    """Verify that read command resolves sequential ID."""
    from src.agent import NewsAgent
    
    agent = NewsAgent()
    # Pre-populate map
    agent.id_map = {"1": "aabb"}
    agent.search_cache = {"aabb": {"url": "url1", "title": "News 1"}}
    
    with patch('src.agent.scrape_article', new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = "Content"
        with patch.object(agent, '_chat_with_llm', new_callable=AsyncMock):
            
            # Call with sequential ID
            await agent._handle_read_match("1")
            
            # Should look up "1" -> "aabb" -> "url1"
            mock_scrape.assert_called_with("url1")

@pytest.mark.asyncio
async def test_agent_read_fallback_hash():
    """Verify fallback to Hash ID if not in map."""
    from src.agent import NewsAgent
    agent = NewsAgent()
    agent.id_map = {"1": "aabb"}
    agent.search_cache = {"ccdd": {"url": "url2", "title": "News 2"}}
    
    with patch('src.agent.scrape_article', new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = "Content"
        with patch.object(agent, '_chat_with_llm', new_callable=AsyncMock):
            
            await agent._handle_read_match("ccdd")
            mock_scrape.assert_called_with("url2")

@pytest.mark.asyncio
async def test_agent_slash_command_uses_id_map():
    """Verify that slash commands (like /fact-check) resolve sequential ID."""
    from src.agent import NewsAgent
    agent = NewsAgent()
    agent.id_map = {"4": "eeff"}
    agent.search_cache = {"eeff": {"url": "url4", "title": "News 4"}}
    
    with patch('src.agent.scrape_article', new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = "Content"
        with patch('src.agent.extract_claims_prompt') as mock_prompt:
             # We just want to see if it gets past the ID check
             #Mock client to return empty string to stop execution or just error out but confirm ID check passed
             agent.client = AsyncMock()
             agent.client.chat.return_value = {'message': {'content': ''}}
             
             await agent._fact_check_article("4")
             
             # scrape_article should be called with url4, proving "4" -> "eeff" -> "url4"
             mock_scrape.assert_called_with("url4")

@pytest.mark.asyncio
async def test_agent_save_article_uses_id_map():
    """Verify that /save-article resolves sequential ID."""
    from src.agent import NewsAgent
    agent = NewsAgent()
    agent.id_map = {"5": "gghh"}
    agent.search_cache = {"gghh": {"url": "url5", "title": "News 5"}}
    
    with patch('src.agent.scrape_article', new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = "Content"
        with patch('builtins.open', new_callable=MagicMock):
            
            await agent._handle_save_match("5")
            
            mock_scrape.assert_called_with("url5")

@pytest.mark.asyncio
async def test_agent_open_uses_id_map():
    """Verify that /open resolves sequential ID."""
    from src.agent import NewsAgent
    agent = NewsAgent()
    agent.id_map = {"6": "jjkk"}
    agent.search_cache = {"jjkk": {"url": "url6", "title": "News 6"}}
    
    with patch('webbrowser.open') as mock_browser:
        await agent._open_in_browser("6")
        mock_browser.assert_called_with("url6")
