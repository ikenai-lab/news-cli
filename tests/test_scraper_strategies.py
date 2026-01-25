"""
Tests for src/tools/scraper.py matching the new flow:
CloudScraper -> Nodriver -> Archive -> Direct
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

@pytest.mark.asyncio
class TestScrapeArticleFlow:
    """Tests the main scrape_article fallback chain."""
    
    @patch('src.tools.scraper.scrape_with_cloudscraper_sync')
    async def test_cloudscraper_priority(self, mock_cloud):
        """Should return Cloudscraper result first if available."""
        from src.tools.scraper import scrape_article
        
        mock_cloud.return_value = "Cloudscraper Content"
        
        with patch('src.tools.scraper.scrape_with_nodriver', new_callable=AsyncMock) as mock_nodriver:
            result = await scrape_article("http://example.com")
            
            assert result == "Cloudscraper Content"
            mock_nodriver.assert_not_called()

    @patch('src.tools.scraper.scrape_with_cloudscraper_sync')
    async def test_nodriver_fallback(self, mock_cloud):
        """Should fall back to Nodriver if Cloudscraper fails."""
        from src.tools.scraper import scrape_article
        
        mock_cloud.return_value = None
        
        with patch('src.tools.scraper.scrape_with_nodriver', new_callable=AsyncMock) as mock_nodriver:
            mock_nodriver.return_value = "Nodriver Content"
            
            result = await scrape_article("http://example.com")
            
            assert result == "Nodriver Content"
            mock_cloud.assert_called_once()
            mock_nodriver.assert_called_once()

    @patch('src.tools.scraper.scrape_with_cloudscraper_sync')
    @patch('src.tools.scraper.scrape_with_nodriver', new_callable=AsyncMock)
    @patch('src.tools.scraper.scrape_with_archive', new_callable=AsyncMock)
    async def test_archive_fallback(self, mock_archive, mock_nodriver, mock_cloud):
        """Should fall back to Archive.org if Nodriver fails."""
        from src.tools.scraper import scrape_article
        
        mock_cloud.return_value = None
        mock_nodriver.return_value = None
        mock_archive.return_value = "Archive Content"
        
        result = await scrape_article("http://example.com")
        
        assert result == "Archive Content"

@pytest.mark.asyncio
class TestScrapeWithNodriver:
    """Tests for the actual nodriver implementation logic."""
    
    async def test_scrape_with_nodriver_success(self):
        """Should start browser, get content, and extract text."""
        from src.tools.scraper import scrape_with_nodriver
        
        with patch('src.tools.scraper._extract_content') as mock_extract:
            mock_extract.return_value = "Extracted Content"
            
            # Mock nodriver module
            with patch.dict('sys.modules', {'nodriver': MagicMock()}):
                import nodriver
                
                # Mock browser and tab
                mock_browser = MagicMock()
                mock_tab = AsyncMock()
                
                # Configure start to return mock browser
                mock_start = AsyncMock(return_value=mock_browser)
                nodriver.start = mock_start
                
                # Configure browser.get to return mock tab
                mock_browser.get = AsyncMock(return_value=mock_tab)
                
                # Configure tab.get_content
                mock_tab.get_content.return_value = "<html>Content</html>"
                
                # We need to ensure tab.sleep is mocked/awaited 
                mock_tab.sleep = AsyncMock()
                
                result = await scrape_with_nodriver("http://example.com")
                
                assert result == "Extracted Content"
                mock_browser.stop.assert_called_once()
                mock_tab.sleep.assert_called_once()
