from prompt_toolkit.completion import Completer, Completion


class SlashCommandCompleter(Completer):
    """
    Custom completer for slash commands.
    Shows autocomplete suggestions when user types '/'.
    """
    
    COMMANDS = {
        "/read": "Read full content of article #ID",
        "/open": "Open article #ID in your default browser",
        "/save": "Save article #ID to file OR save session to filename",
        "/analyze": "AI analysis of article (bias, facts, tone)",
        "/fact-check": "Verify claims in article #ID against fact-check sites",
        "/similar": "Search for related news to article #ID",
        "/more-source": "Find same story from other publishers",
        "/limit": "Set articles per search (1-20). Usage: /limit 10",
        "/briefing": "Show the morning briefing again",
        "/quit": "Exit the application",
        "/exit": "Exit the application",
    }

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        
        # Only show completions if starting with /
        if not text.startswith("/"):
            return
        
        # Get the word being typed
        word = text.lstrip("/")
        
        for command, description in self.COMMANDS.items():
            # Match if command starts with what user typed
            if command.startswith(text) or command.lstrip("/").startswith(word):
                yield Completion(
                    command,
                    start_position=-len(text),
                    display=f"{command}",
                    display_meta=description
                )
