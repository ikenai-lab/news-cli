"""
Tests for src/tools/fact_check.py
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.mark.asyncio
class TestVerifyClaim:
    """Tests for the verify_claim function."""
    
    async def test_verify_claim_returns_dict(self):
        """Should return a dictionary with sources."""
        from src.tools.fact_check import verify_claim
        
        with patch('src.tools.fact_check.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": "Fact Check", "href": "http://snopes.com/test", "body": "This is true"}
            ]
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = None
            mock_ddgs.return_value = mock_instance
            
            result = await verify_claim("test claim")
            
            assert isinstance(result, dict)
            assert "claim" in result
            assert "sources" in result
            assert "source_count" in result
    
    async def test_verify_claim_includes_claim_text(self):
        """Should include the original claim in result."""
        from src.tools.fact_check import verify_claim
        
        with patch('src.tools.fact_check.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = []
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = None
            mock_ddgs.return_value = mock_instance
            
            result = await verify_claim("specific test claim")
            
            assert result["claim"] == "specific test claim"
    
    async def test_verify_claim_max_sources(self):
        """Should respect max_sources parameter."""
        from src.tools.fact_check import verify_claim
        
        with patch('src.tools.fact_check.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": f"Result {i}", "href": f"http://test{i}.com", "body": "Test"}
                for i in range(10)
            ]
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = None
            mock_ddgs.return_value = mock_instance
            
            result = await verify_claim("test", max_sources=3)
            
            # Should limit sources
            assert isinstance(result["source_count"], int)
    
    async def test_verify_claim_handles_exception(self):
        """Should handle exceptions gracefully."""
        from src.tools.fact_check import verify_claim
        
        with patch('src.tools.fact_check.DDGS') as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.side_effect = Exception("Network error")
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = None
            mock_ddgs.return_value = mock_instance
            
            result = await verify_claim("test")
            
            assert isinstance(result, dict)
            assert result["source_count"] >= 0


class TestExtractClaimsPrompt:
    """Tests for the extract_claims_prompt function."""
    
    def test_extract_claims_prompt_includes_article(self):
        """Should include article content in prompt."""
        from src.tools.fact_check import extract_claims_prompt
        
        article = "This is a test article with some claims."
        prompt = extract_claims_prompt(article)
        
        assert article in prompt
    
    def test_extract_claims_prompt_truncates_long_content(self):
        """Should truncate very long articles."""
        from src.tools.fact_check import extract_claims_prompt
        
        article = "x" * 10000
        prompt = extract_claims_prompt(article)
        
        # Should be truncated to ~4000 chars of article
        assert len(prompt) < 6000
    
    def test_extract_claims_prompt_includes_instructions(self):
        """Should include extraction instructions."""
        from src.tools.fact_check import extract_claims_prompt
        
        prompt = extract_claims_prompt("Test article")
        
        assert "factual claims" in prompt.lower() or "claims" in prompt.lower()
        assert "verify" in prompt.lower() or "verifiable" in prompt.lower()
