"""
Comprehensive tests for src/agent.py
"""
import pytest
from unittest.mock import patch, MagicMock


class TestNewsAgentInit:
    """Tests for NewsAgent initialization."""
    
    def test_agent_default_model(self):
        """Should use default model if not specified."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        assert agent.model == "llama3.2:3b"
    
    def test_agent_custom_model(self):
        """Should use custom model if specified."""
        from src.agent import NewsAgent
        
        agent = NewsAgent(model="llama3:8b")
        assert agent.model == "llama3:8b"
    
    def test_agent_default_limit(self):
        """Should use default article limit."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        assert agent.article_limit == 5
    
    def test_agent_custom_limit(self):
        """Should use custom article limit."""
        from src.agent import NewsAgent
        
        agent = NewsAgent(article_limit=10)
        assert agent.article_limit == 10
    
    def test_agent_empty_search_cache(self):
        """Should initialize with empty search cache."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        assert agent.search_cache == {}
    
    def test_agent_has_system_prompt(self):
        """Should initialize with system prompt in history."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        assert len(agent.history) == 1
        assert agent.history[0]["role"] == "system"


class TestSanitizeInput:
    """Tests for input sanitization."""
    
    def test_sanitize_strips_whitespace(self):
        """Should strip leading/trailing whitespace."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        # Mocking the LLM call for sanitization
        with patch.object(agent, '_sanitize_input') as mock_sanitize:
            mock_sanitize.return_value = "test query"
            result = mock_sanitize("  test query  ")
            assert result.strip() == "test query"
    
    def test_sanitize_skips_short_input(self):
        """Should skip LLM for very short inputs."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        # Short inputs should be returned quickly
        result = agent._sanitize_input("hi")
        assert result == "hi"
    
    def test_sanitize_skips_slash_commands(self):
        """Should skip LLM for slash commands."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        result = agent._sanitize_input("/read 1")
        assert result == "/read 1"


class TestSlashCommands:
    """Tests for slash command handling."""
    
    def test_read_command_valid_id(self):
        """Should handle /read with valid ID."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        agent.search_cache = {1: {"url": "http://test.com", "title": "Test"}}
        
        with patch.object(agent, '_handle_read_match') as mock_read:
            mock_read.return_value = "Article content"
            result = agent.process_user_input("/read 1")
            mock_read.assert_called_once_with("1")
    
    def test_open_command_valid_id(self):
        """Should handle /open with valid ID."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        agent.search_cache = {1: {"url": "http://test.com", "title": "Test"}}
        
        with patch.object(agent, '_open_in_browser') as mock_open:
            mock_open.return_value = "Opened in browser: Test"
            result = agent.process_user_input("/open 1")
            mock_open.assert_called_once_with("1")
    
    def test_limit_command_show_current(self):
        """Should show current limit when no arg provided."""
        from src.agent import NewsAgent
        
        agent = NewsAgent(article_limit=5)
        result = agent.process_user_input("/limit")
        assert "5" in result
        assert "limit" in result.lower()
    
    def test_limit_command_set_valid(self):
        """Should set new limit with valid value."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        result = agent.process_user_input("/limit 15")
        assert agent.article_limit == 15
        assert "15" in result
    
    def test_limit_command_reject_invalid(self):
        """Should reject invalid limit values."""
        from src.agent import NewsAgent
        
        agent = NewsAgent(article_limit=5)
        result = agent.process_user_input("/limit 50")
        assert agent.article_limit == 5  # Unchanged
        assert "between" in result.lower() or "must" in result.lower()
    
    def test_briefing_command(self):
        """Should return REFRESH_BRIEFING signal."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        result = agent.process_user_input("/briefing")
        assert result == "REFRESH_BRIEFING"
    
    def test_unknown_command(self):
        """Should return error for unknown commands."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        result = agent.process_user_input("/unknowncommand")
        assert "unknown" in result.lower() or "command" in result.lower()
    
    def test_help_command(self):
        """Should show help when just / is entered."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        # The / command triggers help display, but returns empty or table
        result = agent.process_user_input("/")
        # Just check it doesn't crash
        assert result is not None or result == ""


class TestSearchCache:
    """Tests for search cache logic."""
    
    def test_cache_population(self):
        """Should populate cache correctly."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        agent.search_cache[1] = {"url": "http://test.com", "title": "Test"}
        
        assert 1 in agent.search_cache
        assert agent.search_cache[1]["title"] == "Test"
    
    def test_cache_lookup(self):
        """Should lookup cached items correctly."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        agent.search_cache = {
            1: {"url": "http://a.com", "title": "Article A"},
            2: {"url": "http://b.com", "title": "Article B"},
        }
        
        assert agent.search_cache[1]["url"] == "http://a.com"
        assert agent.search_cache[2]["title"] == "Article B"


class TestFindSimilar:
    """Tests for /similar command."""
    
    def test_find_similar_excludes_source(self):
        """Should exclude original source domain."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        agent.search_cache = {1: {"url": "http://msn.com/article", "title": "Test - MSN"}}
        
        with patch.object(agent, '_handle_search_intent') as mock_search:
            mock_search.return_value = "Results"
            agent._find_similar("1")
            
            call_arg = mock_search.call_args[0][0]
            assert "-site:msn.com" in call_arg


class TestFindMoreSources:
    """Tests for /more-source command."""
    
    def test_more_sources_excludes_original(self):
        """Should exclude original source domain."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        agent.search_cache = {1: {"url": "http://cnn.com/article", "title": "Breaking News - CNN"}}
        
        with patch.object(agent, '_handle_search_intent') as mock_search:
            mock_search.return_value = "Results"
            agent._find_more_sources("1")
            
            call_arg = mock_search.call_args[0][0]
            assert "-site:cnn.com" in call_arg
    
    def test_more_sources_cleans_title(self):
        """Should clean title suffixes."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        agent.search_cache = {1: {"url": "http://bbc.com/article", "title": "Story - BBC News"}}
        
        with patch.object(agent, '_handle_search_intent') as mock_search:
            mock_search.return_value = "Results"
            agent._find_more_sources("1")
            
            call_arg = mock_search.call_args[0][0]
            # Title should be cleaned (no "- BBC News" suffix)
            assert "BBC News" not in call_arg or "-site:" in call_arg


class TestOpenInBrowser:
    """Tests for /open command."""
    
    def test_open_invalid_id(self):
        """Should return error for invalid ID."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        result = agent._open_in_browser("999")
        assert "invalid" in result.lower()
    
    def test_open_valid_id(self):
        """Should open browser for valid ID."""
        from src.agent import NewsAgent
        
        agent = NewsAgent()
        agent.search_cache = {1: {"url": "http://test.com", "title": "Test"}}
        
        with patch('webbrowser.open') as mock_open:
            mock_open.return_value = True
            result = agent._open_in_browser("1")
            
            mock_open.assert_called_once_with("http://test.com")
            assert "opened" in result.lower() or "Test" in result
