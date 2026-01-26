import typer
import asyncio
from rich.console import Console
from src.startup import check_and_start_ollama, get_user_country
from src.agent import NewsAgent
from src.ui.briefing import render_briefing
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from src.ui.completer import SlashCommandCompleter

app = typer.Typer()
console = Console()
console = Console()
from src.config import config as app_config

async def async_main(model: str, limit: int):
    """
    News CLI - Your AI-powered news assistant.
    """
    console.print(f"[bold yellow]Initializing with model: {model}...[/bold yellow]")
    if not check_and_start_ollama(target_model=model):
        console.print("[bold red]Startup failed. Exiting.[/bold red]")
        raise typer.Exit(code=1)
    
    country = get_user_country()
    
    console.print(f"[bold green]News Agent Ready! (Model: {model}, Limit: {limit})[/bold green]")
    agent = NewsAgent(model=model, article_limit=limit)
    
    categories = [
        (f"{country}", f"latest {country} news headlines today"),
        ("Global", "latest world news headlines today"),
        ("Tech", f"latest technology news {country} today"),
        ("Sports", f"latest sports news {country} today")
    ]
    
    # Initial load
    articles = await render_briefing(categories, article_limit=min(limit, 5))
    
    # Populate cache
    agent.search_cache = {}
    agent.id_map = {}
    
    for item in articles:
        agent.search_cache[item['id']] = {"url": item['href'], "title": item['title']}
        if 'seq_id' in item:
            agent.id_map[item['seq_id']] = item['id']
    
    console.print(f"[dim]📰 {len(articles)} articles loaded. Use /read <id> (e.g., 1, 2) to read.[/dim]\n")

    console.print(f"[dim]📰 {len(articles)} articles loaded. Use /read <id> (e.g., 1, 2) to read.[/dim]\n")
    
    bindings = KeyBindings()

    @bindings.add("tab")
    def _(event):
        """Bind Tab to select the first completion."""
        b = event.app.current_buffer
        if b.complete_state:
            b.complete_next()
        else:
            b.start_completion(select_first=True)

    session = PromptSession(
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        key_bindings=bindings
    )
    
    console.print("[dim]Type '/' to see available commands, or just type your question[/dim]\n")
    
    while True:
        try:
            # Async prompt allows other async tasks to run if needed (though we mostly wait here)
            user_input = await session.prompt_async(HTML("<ansigreen><b>You > </b></ansigreen>"))
            
            user_input = user_input.strip()
            if not user_input:
                continue
                
            if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
                console.print("[blue]Goodbye![/blue]")
                break

            response = await agent.process_user_input(user_input)
            
            # Handle special signals
            if response == "REFRESH_BRIEFING":
                console.print("[cyan]Refreshing morning briefing...[/cyan]\n")
                articles = await render_briefing(categories, article_limit=min(limit, 5))
                agent.search_cache = {}
                agent.id_map = {}
                for item in articles:
                    agent.search_cache[item['id']] = {"url": item['href'], "title": item['title']}
                    if 'seq_id' in item:
                        agent.id_map[item['seq_id']] = item['id']
                console.print(f"[dim]📰 {len(articles)} articles loaded.[/dim]\n")
                continue
            
            # Print short system messages
            if response and len(response) < 200 and not response.startswith("#"): 
                 # Heuristic: if short and no markdown header, likely a system msg
                 if any(k in response for k in ["Session saved", "Error", "Invalid", "Usage:", "Limit updated", "Article saved"]):
                     console.print(f"\n[bold purple]System:[/bold purple] {response}\n")
            
        except (KeyboardInterrupt, EOFError):
            console.print("\n[blue]Goodbye![/blue]")
            break
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")

@app.command()
def config(
    model: str = typer.Option(None, help="Set default Ollama model"),
    limit: int = typer.Option(None, min=1, max=20, help="Set default article limit")
):
    """
    View or update default configuration.
    """
    from src.config import config
    from rich.panel import Panel
    
    # Update if provided
    if model:
        try:
            config.set("default_model", model)
            console.print(f"[green]✓ Default model updated to: {model}[/green]")
        except Exception as e:
            console.print(f"[red]Error setting model: {e}[/red]")
            
    if limit:
        try:
            config.set("default_limit", limit)
            console.print(f"[green]✓ Default limit updated to: {limit}[/green]")
        except Exception as e:
            console.print(f"[red]Error setting limit: {e}[/red]")
            
    # Show current config if no updates
    if not model and not limit:
        console.print(Panel(
            f"Model: [cyan]{config.default_model}[/cyan]\n"
            f"Limit: [cyan]{config.default_limit}[/cyan]\n\n"
            f"[dim]Config file: {config._get_config_path()}[/dim]",
            title="Current Configuration",
            border_style="blue"
        ))

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    model: str = typer.Option(app_config.default_model, help="Ollama model to use for the agent"),
    limit: int = typer.Option(app_config.default_limit, min=1, max=20, help="Number of articles per search (1-20)")
):
    """
    Antigravity News CLI - Your AI-powered news assistant.
    """
    if ctx.invoked_subcommand is None:
        try:
            asyncio.run(async_main(model, limit))
        except KeyboardInterrupt:
            pass

def entry_point():
    """ Wrapper to invoke typer properly"""
    app()

if __name__ == "__main__":
    entry_point()
