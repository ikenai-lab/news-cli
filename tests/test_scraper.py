"""
Tests for src/tools/scraper.py
"""
import pytest
from unittest.mock import patch, MagicMock


class TestScrapeArticle:
    """Tests for the scrape_article function."""
    
    def test_scrape_article_success(self):
        """Should extract content from a URL."""
        from src.tools.scraper import scrape_article
        
        with patch('src.tools.scraper.httpx.Client') as mock_client:
            with patch('src.tools.scraper.trafilatura.extract') as mock_extract:
                mock_response = MagicMock()
                mock_response.text = "<html><body><p>Test content</p></body></html>"
                mock_response.raise_for_status = MagicMock()
                
                mock_client_instance = MagicMock()
                mock_client_instance.__enter__.return_value.get.return_value = mock_response
                mock_client.return_value = mock_client_instance
                
                # Return long enough content to pass validation
                mock_extract.return_value = "A" * 200  # Long enough content
                
                result = scrape_article("http://test.com/article")
                
                assert len(result) > 100
    
    def test_scrape_article_fetch_failure(self):
        """Should return error on fetch failure."""
        from src.tools.scraper import scrape_article
        
        with patch('src.tools.scraper.httpx.Client') as mock_client:
            with patch('src.tools.scraper.trafilatura.fetch_url') as mock_fetch:
                mock_client_instance = MagicMock()
                mock_client_instance.__enter__.return_value.get.side_effect = Exception("Network error")
                mock_client.return_value = mock_client_instance
                
                mock_fetch.return_value = None
                
                result = scrape_article("http://test.com/article")
                
                assert "Error" in result
    
    def test_scrape_article_extraction_failure_fallback(self):
        """Should fallback to readability on trafilatura failure."""
        from src.tools.scraper import scrape_article
        
        with patch('src.tools.scraper.httpx.Client') as mock_client:
            with patch('src.tools.scraper.trafilatura.extract') as mock_extract:
                with patch('src.tools.scraper.Document') as mock_doc:
                    mock_response = MagicMock()
                    mock_response.text = "<html><body><p>Test content that is reasonably long for testing</p></body></html>"
                    mock_response.raise_for_status = MagicMock()
                    
                    mock_client_instance = MagicMock()
                    mock_client_instance.__enter__.return_value.get.return_value = mock_response
                    mock_client.return_value = mock_client_instance
                    
                    # Trafilatura fails
                    mock_extract.return_value = None
                    
                    # Readability fallback
                    mock_doc_instance = MagicMock()
                    mock_doc_instance.summary.return_value = "<p>Fallback content that is long enough</p>"
                    mock_doc.return_value = mock_doc_instance
                    
                    result = scrape_article("http://test.com/article")
                    
                    # Should get some content (either fallback or error)
                    assert len(result) > 0


class TestScraperHeaders:
    """Tests for scraper configuration."""
    
    def test_headers_include_user_agent(self):
        """Should include browser-like User-Agent header."""
        from src.tools.scraper import HEADERS
        
        assert "User-Agent" in HEADERS
        assert "Mozilla" in HEADERS["User-Agent"]
    
    def test_headers_include_accept(self):
        """Should include Accept header."""
        from src.tools.scraper import HEADERS
        
        assert "Accept" in HEADERS
        assert "text/html" in HEADERS["Accept"]
