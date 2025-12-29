"""
Tests for Jina and Archive scraping strategies in src/tools/scraper.py
"""
import pytest
from unittest.mock import patch, MagicMock

class TestScraperStrategies:
    """Tests for individual scraping strategies."""
    
    def test_scrape_with_jina_success(self):
        """Should utilize Jina Reader proxy."""
        from src.tools.scraper import scrape_with_jina
        
        with patch('src.tools.scraper.httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "# Markdown Content\n\nThis is content from Jina. It needs to be longer than 100 characters to pass the validation check in the scraper function. So I am adding more text here to ensure it passes."
            
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__.return_value.get.return_value = mock_response
            mock_client.return_value = mock_client_instance
            
            result = scrape_with_jina("http://example.com")
            
            # Check URL construction
            mock_client_instance.__enter__.return_value.get.assert_called_with("https://r.jina.ai/http://example.com")
            assert "This is content from Jina" in result

    def test_scrape_with_jina_failure(self):
        """Should return None on Jina failure."""
        from src.tools.scraper import scrape_with_jina
        
        with patch('src.tools.scraper.httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__.return_value.get.return_value = mock_response
            mock_client.return_value = mock_client_instance
            
            result = scrape_with_jina("http://example.com")
            
            assert result is None

    def test_scrape_with_archive_success(self):
        """Should utilize Archive.org."""
        from src.tools.scraper import scrape_with_archive
        
        with patch('src.tools.scraper.httpx.Client') as mock_client:
            with patch('src.tools.scraper._extract_content') as mock_extract:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = "<html>Archive Content</html>"
                
                mock_client_instance = MagicMock()
                mock_client_instance.__enter__.return_value.get.return_value = mock_response
                mock_client.return_value = mock_client_instance
                
                mock_extract.return_value = "Extracted Archive Content"
                
                result = scrape_with_archive("http://example.com")
                
                # Check URL construction
                mock_client_instance.__enter__.return_value.get.assert_called_with("https://web.archive.org/web/http://example.com")
                assert result == "Extracted Archive Content"

    def test_scrape_with_google_cache_redirect_stub(self):
        """Should return None if Google Cache returns a redirect stub."""
        from src.tools.scraper import scrape_with_google_cache
        
        with patch('src.tools.scraper.httpx.Client') as mock_client:
            with patch('src.tools.scraper._extract_content') as mock_extract:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = "<html>Please click here if you are not redirected within a few seconds.</html>"
                
                mock_client_instance = MagicMock()
                mock_client_instance.__enter__.return_value.get.return_value = mock_response
                mock_client.return_value = mock_client_instance
                
                # The extractor would return the text of the stub
                mock_extract.return_value = "Please click here if you are not redirected within a few seconds."
                
                result = scrape_with_google_cache("http://example.com")
                
                assert result is None


class TestScraperFallbackFlow:
    """Tests the full fallback chain."""
    
    def test_scrape_article_prioritizes_crawl4ai(self):
        """Should return Crawl4AI result first if available."""
        from src.tools.scraper import scrape_article
        
        with patch('src.tools.scraper.scrape_with_crawl4ai') as mock_crawl4ai:
            mock_crawl4ai.return_value = "Crawl4AI Content"
            
            with patch('src.tools.scraper.scrape_with_cloudscraper') as mock_cs:
                result = scrape_article("http://example.com")
                
                assert result == "Crawl4AI Content"
                mock_cs.assert_not_called()

    def test_scrape_article_falls_back_to_cloudscraper(self):
        """Should fall back to Cloudscraper if Crawl4AI fails."""
        from src.tools.scraper import scrape_article
        
        with patch('src.tools.scraper.scrape_with_crawl4ai') as mock_crawl4ai:
            mock_crawl4ai.return_value = None
            
            with patch('src.tools.scraper.scrape_with_cloudscraper') as mock_cs:
                mock_cs.return_value = "Cloudscraper Content"
                
                result = scrape_article("http://example.com")
                
                assert result == "Cloudscraper Content"

    def test_scrape_article_falls_back_to_jina(self):
        """Should fall back to Jina if Crawl4AI and Cloudscraper fail."""
        from src.tools.scraper import scrape_article
        
        with patch('src.tools.scraper.scrape_with_crawl4ai') as mock_crawl4ai:
            mock_crawl4ai.return_value = None
            
            with patch('src.tools.scraper.scrape_with_cloudscraper') as mock_cs:
                mock_cs.return_value = None
                
                with patch('src.tools.scraper.scrape_with_jina') as mock_jina:
                    mock_jina.return_value = "Jina Content"
                    
                    result = scrape_article("http://example.com")
                    
                    assert result == "Jina Content"

