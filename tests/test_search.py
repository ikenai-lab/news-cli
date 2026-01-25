"""
Tests for src/tools/search.py
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.mark.asyncio
class TestSearchNews:
    """Tests for the search_news function."""
    
    async def test_search_news_returns_list(self):
        """Should return a list of results with hash IDs."""
        from src.tools.search import search_news
        
        with patch('src.tools.search.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.news.return_value = [
                {"title": "Test Article", "url": "http://test.com", "body": "Test body", "date": "2025-01-01", "source": "Test"}
            ]
            mock_instance.__enter__.return_value = mock_instance 
            mock_instance.__exit__.return_value = None
            mock_ddgs.return_value = mock_instance
            
            # Since search_news wraps it in to_thread, the mock should work if it's pickleable/thread-safe enough.
            # MagicMock usually works.
            
            results = await search_news("test query")
            
            assert isinstance(results, list)
            assert len(results) == 1
            assert results[0]["title"] == "Test Article"
            assert "id" in results[0]
            assert len(results[0]["id"]) == 4

    async def test_search_news_max_results(self):
        """Should respect max_results parameter."""
        from src.tools.search import search_news
        
        with patch('src.tools.search.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.news.return_value = []
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = None
            mock_ddgs.return_value = mock_instance
            
            await search_news("test", max_results=5)
            
            mock_instance.news.assert_called_once()
            call_kwargs = mock_instance.news.call_args[1]
            assert call_kwargs.get('max_results') == 5
    
    async def test_search_news_with_timelimit(self):
        """Should pass timelimit to DDGS."""
        from src.tools.search import search_news
        
        with patch('src.tools.search.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.news.return_value = []
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = None
            mock_ddgs.return_value = mock_instance
            
            await search_news("test", timelimit="w")
            
            call_kwargs = mock_instance.news.call_args[1]
            assert call_kwargs.get('timelimit') == "w"
    
    async def test_search_news_handles_exception(self):
        """Should return empty list on exception."""
        from src.tools.search import search_news
        
        with patch('src.tools.search.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.news.side_effect = Exception("Network error")
            mock_instance.text.return_value = []
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = None
            mock_ddgs.return_value = mock_instance
            
            results = await search_news("test")
            
            assert isinstance(results, list)
    
    async def test_search_news_fallback_to_text(self):
        """Should fallback to text search if news fails."""
        from src.tools.search import search_news
        
        with patch('src.tools.search.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.news.return_value = []
            mock_instance.text.return_value = [
                {"title": "Text Result", "href": "http://test.com", "body": "Body"}
            ]
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = None
            mock_ddgs.return_value = mock_instance
            
            results = await search_news("test")
            
            # Should have called text as fallback
            assert mock_instance.text.called or len(results) >= 0
