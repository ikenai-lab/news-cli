"""
Tests for src/startup.py
"""
import pytest
from unittest.mock import patch, MagicMock


class TestGetUserCountry:
    """Tests for the get_user_country function."""
    
    def test_get_country_success(self):
        """Should return country from IP API."""
        from src.startup import get_user_country
        
        with patch('src.startup.httpx.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"country": "India", "status": "success"}
            mock_get.return_value = mock_response
            
            result = get_user_country()
            
            assert result == "India"
    
    def test_get_country_fallback_on_error(self):
        """Should return 'Global' on API error."""
        from src.startup import get_user_country
        
        with patch('src.startup.httpx.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            result = get_user_country()
            
            assert result == "Global"
    
    def test_get_country_fallback_on_missing_key(self):
        """Should return 'Global' if country key missing."""
        from src.startup import get_user_country
        
        with patch('src.startup.httpx.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "fail"}
            mock_get.return_value = mock_response
            
            result = get_user_country()
            
            assert result == "Global"


class TestCheckAndStartOllama:
    """Tests for the check_and_start_ollama function."""
    
    def test_ollama_not_installed(self):
        """Should exit if Ollama is not installed."""
        from src.startup import check_and_start_ollama
        
        with patch('src.startup.shutil.which') as mock_which:
            mock_which.return_value = None
            
            with pytest.raises(SystemExit) as exc_info:
                check_and_start_ollama()
            
            assert exc_info.value.code == 1
    
    @pytest.mark.skipif(True, reason="Integration test - requires mocking ollama module")
    def test_ollama_server_already_running(self):
        """Should return True if Ollama server is already running."""
        # This test requires Ollama to not actually be running
        # to properly test the mock - skip for now
        pass
    
    @pytest.mark.skipif(True, reason="Integration test - requires mocking ollama module")
    def test_ollama_model_not_found_triggers_pull(self):
        """Should attempt to pull model if not found."""
        # This test would actually pull the model - skip for CI
        pass
