import shutil
import subprocess
import sys
import time
from typing import Optional

import httpx
import ollama
from rich.console import Console
from rich.panel import Panel

console = Console()

def get_user_country() -> str:
    """
    Detects user's country using ip-api.com. Returns 'Global' on failure.
    """
    try:
        import httpx
        resp = httpx.get("http://ip-api.com/json/", timeout=5.0)  # Increased timeout
        data = resp.json()
        country = data.get("country", "Global")
        console.print(f"[dim]Location detected: {country}[/dim]")
        return country
    except Exception as e:
        console.print(f"[dim]Geo-location failed: {e}[/dim]")
        return "Global"

def check_and_start_ollama(target_model : str = "llama3.2:3b") -> bool:
    """
    Ensures Ollama is installed, running, and the required model is available.
    Returns True if ready, exits or returns False otherwise.
    """
    # 1. Check Install
    if shutil.which("ollama") is None:
        console.print(Panel("Error: 'ollama' binary not found in PATH.\nPlease install Ollama from https://ollama.com/download", title="Ollama Missing", style="bold red"))
        sys.exit(1)

    # 2. Check Server
    server_url = "http://localhost:11434"
    server_ready = False
    
    try:
        httpx.get(server_url, timeout=1.0)
        server_ready = True
    except (httpx.ConnectError, httpx.TimeoutException):
        console.print("[yellow]Ollama server not running. Starting...[/yellow]")
        try:
            # Start server in background
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for it to come up
            for _ in range(10):  # Wait up to 10 seconds
                time.sleep(1)
                try:
                    httpx.get(server_url, timeout=1.0)
                    server_ready = True
                    console.print("[green]Ollama server started successfully.[/green]")
                    break
                except (httpx.ConnectError, httpx.TimeoutException):
                    continue
        except Exception as e:
            console.print(f"[bold red]Failed to start Ollama server: {e}[/bold red]")
            sys.exit(1)

    if not server_ready:
        console.print("[bold red]Timed out waiting for Ollama server to start.[/bold red]")
        sys.exit(1)

    # 3. Check and Pull Model
    try:
        models = ollama.list()
        # ollama.list returns a dict with 'models' key which is a list of objects
        params = [m['model'] for m in models.get('models', [])]
        
        # Check if model exists (ignoring tag if needed, but exact match is safer for now)
        # Usually models are like 'llama3.2:3b', sometimes just 'llama3.2' if latest.
        # We will look for partial match or exact match to be safe.
        model_exists = any(target_model in name for name in params)

        if not model_exists:
            console.print(f"[blue]Model '{target_model}' not found. Pulling...[/blue]")
            # Use subprocess to show native progress bar
            try:
                subprocess.run(["ollama", "pull", target_model], check=True)
                console.print(f"[green]Model '{target_model}' pulled successfully.[/green]")
            except subprocess.CalledProcessError:
                console.print(f"[bold red]Failed to pull model '{target_model}'.[/bold red]")
                sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error checking models: {e}[/bold red]")
        sys.exit(1)

    return True

if __name__ == "__main__":
    if check_and_start_ollama():
        console.print("[bold green]Ollama is ready![/bold green]")
