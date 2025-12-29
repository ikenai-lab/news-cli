import typer
from rich.console import Console
from src.startup import check_and_start_ollama
from src.agent import NewsAgent

app = typer.Typer()
console = Console()

@app.command()
def main(
    model: str = typer.Option("llama3.2:3b", help="Ollama model to use for the agent"),
    limit: int = typer.Option(5, min=1, max=20, help="Number of articles per search (1-20)")
):
    """
    News CLI - Your AI-powered news assistant.
    """
    # 1. Startup Checks
    console.print("[bold yellow]Initializing...[/bold yellow]")
    if not check_and_start_ollama():
        console.print("[bold red]Startup failed. Exiting.[/bold red]")
        raise typer.Exit(code=1)
    
    # 2. Initialize Agent with limit
    console.print(f"[bold green]News Agent Ready! (Model: {model}, Limit: {limit})[/bold green]")
    agent = NewsAgent(model=model, article_limit=limit)
    
    # 3. Startup Dashboard
    console.print("\n[bold cyan]Fetching Morning Briefing...[/bold cyan]")
    from src.tools.search import search_news
    from src.startup import get_user_country
    from rich.table import Table
    from rich.layout import Layout
    
    country = get_user_country()
    # All categories are now geo-located
    categories = [
        (f"{country}", f"top {country} news"),
        ("Global", "top world news"),
        ("Tech", f"{country} technology news"),
        ("Sports", f"{country} sports news")
    ]
    
    # Store all dashboard results to populate agent's cache
    all_dashboard_results = []
    article_counter = 1
    
    # Dashboard shows fewer articles per category for readability
    dashboard_limit = min(agent.article_limit, 5)  # Cap at 5 for dashboard
    
    with console.status(f"Loading dashboard (Location: {country})...", spinner="dots"):
        for cat_name, search_query in categories:
            results = search_news(search_query, max_results=dashboard_limit)
            
            # Create a table for each category
            table = Table(title=f"[bold]{cat_name} Headlines[/bold]", show_header=True, header_style="bold magenta", expand=True)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Date", min_width=10)
            table.add_column("Source", min_width=15)
            table.add_column("Title")
            
            if results:
                for res in results:
                    # Simplified source extraction
                    try:
                        from urllib.parse import urlparse
                        source = urlparse(res.get('href', '')).netloc.replace('www.', '')
                    except: source = "Unknown"
                    
                    table.add_row(str(article_counter), res.get('date', '')[:10], source, res.get('title', ''))
                    
                    # Add to all results for cache
                    all_dashboard_results.append({
                        "id": article_counter,
                        "title": res.get('title', ''),
                        "href": res.get('href', ''),
                        "category": cat_name
                    })
                    article_counter += 1
            else:
                table.add_row("-", "-", "-", "No news found.")
            
            console.print(table)
            console.print() # spacing
    
    # Populate agent's search cache with all dashboard articles
    for item in all_dashboard_results:
        agent.search_cache[item["id"]] = {"url": item["href"], "title": item["title"]}
    
    console.print(f"[dim]📰 {len(all_dashboard_results)} articles loaded. Use /read <#> to read any article.[/dim]\n")

    # 4. Main Loop with prompt_toolkit autocomplete
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import HTML
    from src.ui.completer import SlashCommandCompleter
    
    session = PromptSession(
        completer=SlashCommandCompleter(),
        complete_while_typing=True
    )
    
    console.print("[dim]Type '/' to see available commands, or just type your question[/dim]\n")
    
    while True:
        try:
            user_input = session.prompt(HTML("<ansigreen><b>You > </b></ansigreen>"))
            if user_input.lower().strip() in ("exit", "quit", "/exit", "/quit"):
                console.print("[blue]Goodbye![/blue]")
                break
                
            if not user_input.strip():
                continue

            # with console.status("Thinking...", spinner="dots"):
            #     response = agent.process_user_input(user_input)
            
            # Since agent now handles streaming/printing, we just call it.
            # But we still want to handle the return value (maybe just for logging or history?)
            # or if it returns a non-streamed string (error message or save confirmation).
            
            response = agent.process_user_input(user_input)
            
            # Handle special signals
            if response == "REFRESH_BRIEFING":
                # Re-run the dashboard (we'll refactor this into a function later)
                console.print("[cyan]Refreshing morning briefing...[/cyan]\n")
                agent.search_cache = {}  # Clear old cache
                article_counter = 1
                for cat_name, search_query in categories:
                    results = search_news(search_query, max_results=3)
                    table = Table(title=f"[bold]{cat_name} Headlines[/bold]", show_header=True, header_style="bold magenta", expand=True)
                    table.add_column("#", style="cyan", width=4)
                    table.add_column("Date", min_width=10)
                    table.add_column("Source", min_width=15)
                    table.add_column("Title")
                    if results:
                        for res in results:
                            try:
                                from urllib.parse import urlparse
                                source = urlparse(res.get('href', '')).netloc.replace('www.', '')
                            except: source = "Unknown"
                            table.add_row(str(article_counter), res.get('date', '')[:10], source, res.get('title', ''))
                            agent.search_cache[article_counter] = {"url": res.get('href', ''), "title": res.get('title', '')}
                            article_counter += 1
                    else:
                        table.add_row("-", "-", "-", "No news found.")
                    console.print(table)
                    console.print()
                console.print(f"[dim]📰 {article_counter-1} articles loaded. Use /read <#> to read any article.[/dim]\n")
                continue
            
            # Heuristic: Print short system messages from slash commands.
            # Long responses are streamed by agent directly.
            # Check for common system message patterns or short responses
            if response and (
                response.startswith("Session saved") or 
                response.startswith("Error") or 
                response.startswith("Article limit") or
                response.startswith("Current limit") or
                response.startswith("Opened in browser") or
                response.startswith("Article saved") or
                response.startswith("Invalid") or
                response.startswith("Usage:") or
                response.startswith("Limit must") or
                response.startswith("No verifiable") or
                len(response) < 100  # Short messages are system responses
            ):
                 console.print(f"\n[bold purple]System:[/bold purple] {response}\n")
            
        except KeyboardInterrupt:
            console.print("\n[blue]Goodbye![/blue]")
            break
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")
def entry_point():
    """ Wrapper to invoke typer properly"""
    typer.run(main)

if __name__ == "__main__":
    app()
