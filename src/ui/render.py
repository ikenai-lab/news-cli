from urllib.parse import urlparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

def print_search_results(results: list[dict]):
    """
    Renders search results in a table.
    """
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Date", min_width=12)
    table.add_column("Source", min_width=15)
    table.add_column("Title")

    for i, res in enumerate(results, 1):
        # Extract source domain
        try:
            source = urlparse(res.get('href', '')).netloc.replace('www.', '')
        except:
            source = "Unknown"
            
        date = res.get('date', '')
        if not date:
            date = "Unknown"
            
        table.add_row(str(i), date, source, res.get('title', 'No Title'))

    console.print(table)

def print_article(title: str, content: str):
    """
    Renders an article in a markdown panel.
    """
    md = Markdown(content)
    console.print(Panel(md, title=title, expand=False, border_style="blue"))

def print_error(message: str):
    """
    Renders an error message in a red panel.
    """
    console.print(Panel(message, title="Error", style="bold red"))
