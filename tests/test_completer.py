"""
Tests for src/ui/completer.py
"""
import pytest


class TestSlashCommandCompleter:
    """Tests for the SlashCommandCompleter class."""
    
    def test_completer_has_commands(self):
        """Should have COMMANDS dictionary."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert hasattr(completer, 'COMMANDS')
        assert isinstance(completer.COMMANDS, dict)
    
    def test_commands_include_read(self):
        """Should include /read command."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert "/read" in completer.COMMANDS
    
    def test_commands_include_open(self):
        """Should include /open command."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert "/open" in completer.COMMANDS
    
    def test_commands_include_save(self):
        """Should include save commands."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert "/save-article" in completer.COMMANDS
        assert "/save-session" in completer.COMMANDS
    
    def test_commands_include_analyze(self):
        """Should include /analyze command."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert "/analyze" in completer.COMMANDS
    
    def test_commands_include_fact_check(self):
        """Should include /fact-check command."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert "/fact-check" in completer.COMMANDS
    
    def test_commands_include_similar(self):
        """Should include /similar command."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert "/similar" in completer.COMMANDS
    
    
    def test_commands_include_limit(self):
        """Should include /limit command."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert "/limit" in completer.COMMANDS
    
    def test_commands_include_briefing(self):
        """Should include /briefing command."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert "/briefing" in completer.COMMANDS
    
    def test_commands_include_quit(self):
        """Should include /quit command."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert "/quit" in completer.COMMANDS
    
    def test_commands_include_exit(self):
        """Should include /exit command."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        assert "/exit" in completer.COMMANDS
    
    def test_command_descriptions_not_empty(self):
        """All commands should have descriptions."""
        from src.ui.completer import SlashCommandCompleter
        
        completer = SlashCommandCompleter()
        for cmd, desc in completer.COMMANDS.items():
            assert len(desc) > 0, f"Command {cmd} has empty description"
