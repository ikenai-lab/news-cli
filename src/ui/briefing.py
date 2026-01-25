from rich.console import Console
from rich.table import Table
from rich.box import ROUNDED
from src.tools.search import search_news
import asyncio

console = Console()

async def render_briefing(categories: list[tuple[str, str]], article_limit: int = 3) -> list[dict]:
    """
    Renders morning briefing dashboard.
    
    Args:
        categories: list of (display_name, search_query)
        article_limit: number of articles per category
        
    Returns:
        List of all loaded articles (dicts) for caching.
    """
    total_articles = []
    
    tasks = [search_news(query, max_results=article_limit, timelimit='w') for _, query in categories]
    
    with console.status("[bold cyan]Fetching Morning Briefing...[/bold cyan]", spinner="dots"):
        results_list = await asyncio.gather(*tasks)
    
    console.print(f"\n[bold]📅 Morning Briefing[/bold]\n")
    
    global_counter = 1
    
    for (cat_name, _), results in zip(categories, results_list):
        table = Table(title=f"[bold]{cat_name}[/bold]", show_header=True, header_style="bold magenta", expand=True, box=ROUNDED)
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Date", style="dim", width=12)
        table.add_column("Source", style="blue")
        table.add_column("Title")
        
        if results:
            for res in results:
                # Add category info to result
                res['category'] = cat_name
                # Add sequential index for display
                res['seq_id'] = str(global_counter)
                
                total_articles.append(res)
                
                # Cleanup date
                date_str = res.get('date', '') or "-"
                if len(date_str) > 10: date_str = date_str[:10]
                
                table.add_row(
                    str(global_counter),  # ID
                    date_str,
                    res.get('source', 'Unknown'), 
                    res['title']
                )
                global_counter += 1
        else:
            table.add_row("-", "-", "-", "[dim]No recent news found.[/dim]")
            
        console.print(table)
        console.print() # spacing
        
    return total_articles
