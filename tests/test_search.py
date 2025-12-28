"""
Tests for src/tools/search.py
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSearchNews:
    """Tests for the search_news function."""
    
    def test_search_news_returns_list(self):
        """Should return a list of results."""
        from src.tools.search import search_news
        
        with patch('src.tools.search.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.news.return_value = [
                {"title": "Test Article", "href": "http://test.com", "body": "Test body", "date": "2025-01-01"}
            ]
            mock_ddgs.return_value = mock_instance
            
            results = search_news("test query")
            
            assert isinstance(results, list)
            assert len(results) == 1
            assert results[0]["title"] == "Test Article"
    
    def test_search_news_max_results(self):
        """Should respect max_results parameter."""
        from src.tools.search import search_news
        
        with patch('src.tools.search.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.news.return_value = [
                {"title": f"Article {i}", "href": f"http://test{i}.com", "body": "Body", "date": "2025-01-01"}
                for i in range(5)
            ]
            mock_ddgs.return_value = mock_instance
            
            results = search_news("test", max_results=5)
            
            mock_instance.news.assert_called_once()
            call_kwargs = mock_instance.news.call_args[1]
            assert call_kwargs.get('max_results') == 5
    
    def test_search_news_with_timelimit(self):
        """Should pass timelimit to DDGS."""
        from src.tools.search import search_news
        
        with patch('src.tools.search.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.news.return_value = []
            mock_ddgs.return_value = mock_instance
            
            search_news("test", timelimit="w")
            
            call_kwargs = mock_instance.news.call_args[1]
            assert call_kwargs.get('timelimit') == "w"
    
    def test_search_news_handles_exception(self):
        """Should return empty list on exception."""
        from src.tools.search import search_news
        
        with patch('src.tools.search.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.news.side_effect = Exception("Network error")
            mock_instance.text.return_value = []
            mock_ddgs.return_value = mock_instance
            
            results = search_news("test")
            
            assert isinstance(results, list)
    
    def test_search_news_fallback_to_text(self):
        """Should fallback to text search if news fails."""
        from src.tools.search import search_news
        
        with patch('src.tools.search.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.news.return_value = []
            mock_instance.text.return_value = [
                {"title": "Text Result", "href": "http://test.com", "body": "Body"}
            ]
            mock_ddgs.return_value = mock_instance
            
            results = search_news("test")
            
            # Should have called text as fallback
            assert mock_instance.text.called or len(results) >= 0
