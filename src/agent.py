import re
import ollama
import asyncio
import json
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel

from datetime import datetime
import webbrowser
from rich.box import ROUNDED
from src.config import config
from src.tools.search import search_news
from src.tools.scraper import scrape_article
from src.tools.fact_check import verify_claim, extract_claims_prompt
from src.ui.render import print_search_results, print_article, print_error

console = Console()

class NewsAgent:
    def __init__(self, model: str = None, article_limit: int = None):
        self.model = model or config.default_model
        self.article_limit = article_limit or config.default_limit
        self.client = ollama.AsyncClient()
        self.history = [
            {"role": "system", "content": "You are a helpful news assistant. You have access to search tools. When provided with search results or article content, summarize them concisely for the user. If the user asks to read a specific item by ID, assume the content will be provided to you."}
        ]
        self.search_cache = {}  # Maps ID (str) -> {url, title}
        self.id_map = {}        # Maps Seq ID (str) -> Hash ID (str)

    async def process_user_input(self, user_text: str) -> str:
        """
        Determines intent, executes tools if needed, and returns the response.
        """
        if user_text.startswith("/"):
            return await self._handle_slash_command(user_text)
            
        read_match = re.search(r"^(read|open|give me) (\w+)$", user_text.lower())
        if read_match:
             article_id = read_match.group(2)
             if article_id in self.search_cache:
                 return await self._scrape_and_summarize(article_id)
        
        intent = await self._classify_intent(user_text)
        
        if intent == "READ":
            return await self._handle_read_intent(user_text)
        elif intent == "SEARCH":
            # Check for simple search vs date extraction
            return await self._handle_search_intent(user_text)
        else:
            # Add to history and chat
            self.history.append({"role": "user", "content": user_text})
            self._prune_history()
            return await self._chat_with_llm()

    def _prune_history(self):
        """Keeps system prompt + last 6 messages (3 turns)."""
        if len(self.history) > 7:
             self.history = [self.history[0]] + self.history[-6:]

    async def _handle_slash_command(self, user_text: str) -> str:
        parts = user_text.strip().split()
        command = parts[0].lower()
        args = parts[1:]
        
        if command == "/read" and args:
            return await self._handle_read_match(args[0])
        elif command == "/open" and args:
            return await self._open_in_browser(args[0])
        elif command == "/":
             self._print_help()
             return ""
        elif command == "/save-article" and args:
            return await self._handle_save_match(args[0])
        elif command == "/save-session" and args:
             return self._save_session(args[0])
        elif command == "/analyze" and args:
            return await self._analyze_article(args[0])
        elif command == "/similar" and args:
            return await self._find_similar(args[0])
        elif command == "/limit":
            if not args:
                return f"Current limit: {self.article_limit} articles per search. Usage: /limit <1-20>"
            try:
                new_limit = int(args[0])
                if 1 <= new_limit <= 20:
                    self.article_limit = new_limit
                    return f"Article limit updated to {new_limit}"
                else:
                    return "Limit must be between 1 and 20"
            except ValueError:
                return "Invalid limit. Usage: /limit <1-20>"
        elif command == "/fact-check" and args:
            return await self._fact_check_article(args[0])
        elif command == "/briefing":
            return "REFRESH_BRIEFING"
        elif command in ["/exit", "/quit"]:
            return "Goodbye!"
        else:
            return f"Unknown command: {command}"

    def _print_help(self):
         table = Table(title="[bold]Available Commands[/bold]", box=ROUNDED, show_header=True, header_style="bold magenta")
         table.add_column("Command", style="cyan", no_wrap=True)
         table.add_column("Usage", style="green")
         table.add_column("Description", style="white")
         
         table.add_row("/read", "/read <id>", "Read full content of article #ID")
         table.add_row("/open", "/open <id>", "Open article in browser")
         table.add_row("/save-article", "/save-article <id>", "Save article content to file")
         table.add_row("/save-session", "/save-session <file>", "Save current chat history")
         table.add_row("/analyze", "/analyze <id>", "AI analysis (bias, facts, tone)")
         table.add_row("/fact-check", "/fact-check <id>", "Verify claims against fact-check sites")
         table.add_row("/similar", "/similar <id>", "Search for related news")
         table.add_row("/limit", "/limit <n>", "Set articles per search (1-20)")
         table.add_row("/briefing", "/briefing", "Refresh morning briefing")
         table.add_row("/quit", "/quit", "Exit application")
         console.print(table)

    async def _handle_read_match(self, arg: str) -> str:
        # Try resolving sequential ID -> Hash ID
        if arg in self.id_map:
            arg = self.id_map[arg]
            
        if arg in self.search_cache:
            return await self._scrape_and_summarize(arg)
        return "Invalid article ID."

    async def _handle_read_intent(self, user_text: str, strict: bool = True) -> str | None:
        if not self.search_cache:
            if strict: return "No search results available."
            return None
            
        # Check LLM assistance or simple fuzzy match
        # For simplicity, let's ask LLM if regex failed
        return await self._identify_article_with_llm(user_text)

    async def _scrape_and_summarize(self, item_id: str) -> str:
        item = self.search_cache[item_id]
        url = item["url"]
        title = item["title"]
        console.print(f"[blue]Scraping article {item_id}: {url}[/blue]")
        
        # Async scrape
        article_content = await scrape_article(url)
        
        if article_content.startswith("Error:"):
            print_error(article_content)
            return "I was unable to read the article due to a scraping error."
        
        print_article(title, article_content)
        
        user_message = f"Please summarize this article:\n\nTitle: {title}\n\n{article_content[:5000]}"
        self.history.append({"role": "user", "content": user_message})
        self._prune_history()
        
        return await self._chat_with_llm()

    async def _identify_article_with_llm(self, user_text: str) -> str:
        cache_summary = "\n".join([f"{i}. {item['title']}" for i, item in self.search_cache.items()])
        prompt = f"""User asked: "{user_text}"
        Available:
        {cache_summary}
        
        Which ID (e.g. a1b2) is the user referring to? Return ONLY the ID/number or NONE."""
        
        try:
            resp = await self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            answer = resp['message']['content'].strip()
            if answer in self.id_map:
                answer = self.id_map[answer]
            
            if answer in self.search_cache:
                return await self._scrape_and_summarize(answer)
            return "I couldn't identify the article."
        except:
             return "I couldn't identify the article."

    async def _handle_search_intent(self, user_text: str, skip_date_extraction: bool = False) -> str:
        if skip_date_extraction:
            search_query = user_text
            timelimit = None
        else:
            search_query, timelimit = await self._refine_search_query(user_text)
            
        console.print(f"[blue]Searching for: {search_query}[/blue]")
        if timelimit: console.print(f"[dim]Time filter: {timelimit}[/dim]")
        
        results = await search_news(search_query, max_results=self.article_limit, timelimit=timelimit)
        
        if not results: return "I couldn't find any news."
        
        # UX: Map Hash IDs to Sequential IDs (1, 2, 3...)
        self.search_cache = {}
        self.id_map = {}
        display_results = []
        
        formatted_results = "Search results:\n"
        for i, res in enumerate(results, 1):
            seq_id = str(i)
            hash_id = res['id']
            
            self.id_map[seq_id] = hash_id
            self.search_cache[hash_id] = {"url": res['href'], "title": res['title']}
            
            # Create display copy
            d_res = res.copy()
            d_res['id'] = seq_id
            display_results.append(d_res)
            
            formatted_results += f"ID: {seq_id} | {res['title']} ({res['date']})\n"
            
        print_search_results(display_results)
        
        user_message = f"I searched for '{search_query}'. Results:\n{formatted_results}\nPresent these concisely."
        self.history.append({"role": "user", "content": user_message})
        self._prune_history()
        
        return await self._chat_with_llm()

    async def _refine_search_query(self, query: str) -> tuple[str, str | None]:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get last 2 turns of history for context
        context_history = ""
        if len(self.history) >= 2:
             # Skip system prompt
             recent = self.history[-2:]
             context_history = "Previous conversation:\n"
             for msg in recent:
                 role = "User" if msg['role'] == "user" else "Agent"
                 # Truncate content for token efficiency
                 content = msg['content'][:500].replace("\n", " ") 
                 context_history += f"{role}: {content}\n"
        
        prompt = f"""Today is {current_date}. 
        User Query: "{query}"
        {context_history}
        
        Task: Refine the query for a search engine. if the query refers to previous context (e.g. "it", "this", "the same"), rewrite it using the context.
        Also check if it needs a time filter (d/w/m/y).
        
        Return format: 
        TIMELIMIT: [d/w/m/y/NONE]
        QUERY: [refined search query]"""
        
        try:
            resp = await self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            answer = resp['message']['content'].strip()
            
            timelimit = None
            cleaned_query = query
            
            for line in answer.split('\n'):
                if "TIMELIMIT:" in line:
                    tl = line.split(":", 1)[1].strip().lower()
                    if tl in ['d', 'w', 'm', 'y']: timelimit = tl
                elif "QUERY:" in line:
                    cleaned_query = line.split(":", 1)[1].strip()
                    
            return (cleaned_query, timelimit)
        except:
             return (query, None)

    async def _classify_intent(self, text: str) -> str:
         # Use regex first?
         if any(k in text.lower() for k in ["news", "search", "headlines", "latest"]):
             return "SEARCH"
         
         # Fallback to LLM
         try:
             resp = await self.client.chat(model=self.model, messages=[
                 {"role": "system", "content": "You are a classifier. Output ONLY one word: SEARCH, READ, or CHAT. Rules:\n- Requesting news/info -> SEARCH\n- Reading specific article -> READ\n- Conversation -> CHAT\nOutput nothing else."},
                 {"role": "user", "content": text}
             ])
             intent = resp['message']['content'].strip().upper()
             # Clean up potential punctuation
             intent = re.sub(r"[^A-Z]", "", intent)
             
             if intent in ["SEARCH", "READ", "CHAT"]:
                 return intent
             return "CHAT"
         except:
             return "CHAT"

    async def _chat_with_llm(self) -> str:
        try:
            full_response = ""
            console.print("[bold purple]Agent:[/bold purple]")
            
            # Using rich Live for correct streaming
            with Live(Markdown(""), refresh_per_second=10, console=console) as live:
                async for chunk in await self.client.chat(model=self.model, messages=self.history, stream=True):
                    content = chunk['message']['content']
                    full_response += content
                    live.update(Markdown(full_response))
            
            console.print()
            self.history.append({"role": "assistant", "content": full_response})
            self._prune_history()
            return full_response
        except Exception as e:
            return f"Error: {e}"

    # Helpers
    async def _open_in_browser(self, arg: str) -> str:
        if arg in self.id_map:
            arg = self.id_map[arg]
            
        if arg in self.search_cache:
            url = self.search_cache[arg]['url']
            try:
                webbrowser.open(url)
                return f"Opened {url}"
            except Exception as e: return f"Error: {e}"
        return "Invalid ID"

    def _save_session(self, filename: str) -> str:
        try:
            with open(filename, "w") as f:
                json.dump(self.history, f, indent=2)
            return f"Session saved to {filename}"
        except Exception as e:
            return f"Error saving session: {e}"

    async def _save_article(self, item_id: str, filename: str = None) -> str:
        item = self.search_cache[item_id]
        title = item["title"]
        console.print(f"[blue]Scraping to save article {item_id}...[/blue]")
        
        content = await scrape_article(item['url'])
        if content.startswith("Error:"): return content
        
        if not filename:
            filename = f"article_{item_id}.md"
        try:
            with open(filename, "w") as f:
                f.write(f"# {title}\n\nSource: {item['url']}\n\n{content}")
            return f"Article saved to {filename}"
        except Exception as e:
            return f"Error saving file: {e}"

    async def _handle_save_match(self, arg: str, filename: str = None) -> str:
        # Resolve ID if possible
        item_id = arg
        if item_id in self.id_map:
            item_id = self.id_map[item_id]
            
        if item_id in self.search_cache:
            return await self._save_article(item_id, filename)
        else:
            # Assume arg is filename for session save
            return self._save_session(arg)

    async def _analyze_article(self, arg: str) -> str:
        if arg in self.id_map: arg = self.id_map[arg]
        if arg not in self.search_cache: return "Invalid ID"
        item = self.search_cache[arg]
        
        console.print(f"[blue]Analyzing article {arg}...[/blue]")
        content = await scrape_article(item['url'])
        if content.startswith("Error:"): return content

        prompt = f"Perform a critical analysis of this article. Identify potential bias, fact-check claims where possible using your knowledge, and evaluate the tone.\n\n{content[:5000]}"
        self.history.append({"role": "user", "content": prompt})
        self._prune_history()
        return await self._chat_with_llm()

    async def _find_similar(self, arg: str) -> str:
        if arg in self.id_map: arg = self.id_map[arg]
        if arg not in self.search_cache: return "Invalid ID"
        item = self.search_cache[arg]
        # Clean title 
        clean_title = item["title"].split(" - ")[0].split(" | ")[0]
        return await self._handle_search_intent(f"news similar to {clean_title}", skip_date_extraction=True)

    async def _fact_check_article(self, arg: str) -> str:
        if arg in self.id_map: arg = self.id_map[arg]
        if arg not in self.search_cache: return "Invalid ID"
        item = self.search_cache[arg]
        title = item["title"]
        
        console.print(f"[blue]Fact-checking article {arg}: {title}[/blue]")
        
        # 1. Scrape
        content = await scrape_article(item['url'])
        if content.startswith("Error:"): return content
        
        # 2. Extract Claims (Ollama)
        console.print("[dim]Extracting claims...[/dim]")
        prompt = extract_claims_prompt(content)
        try:
            resp = await self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            claims_text = resp['message']['content'].strip()
        except Exception as e: return f"Error: {e}"
        
        # Parse claims
        claims = []
        for line in claims_text.split('\n'):
            line = line.strip()
            if line and line[0].isdigit():
                claim = line.lstrip('0123456789.)-: ').strip()
                if claim: claims.append(claim)
                
        if not claims: return "No verifiable claims found."
        
        # 3. Verify (Async with Streaming)
        console.print(f"[dim]Verifying {len(claims)} claims...[/dim]")
        
        results_table = Table(title="[bold]Fact-Check Results[/bold]", show_header=True, expand=True, box=ROUNDED)
        results_table.add_column("#", width=3, style="dim")
        results_table.add_column("Claim", ratio=2)
        results_table.add_column("Verdict", width=12, justify="center")
        results_table.add_column("Evidence", ratio=3, style="dim")
        
        verification_summary = []
        
        # Initialize table with pending rows
        for i, claim in enumerate(claims, 1):
            results_table.add_row(str(i), claim, "[yellow]Checking...[/yellow]", "")

        with Live(results_table, refresh_per_second=4, console=console) as live:
            for i, claim in enumerate(claims, 1):
                # Update status to working
                # (Rich tables are append-only mostly, so we rebuild rows or use a layout, 
                # but rebuilding rows in loop is easier for this simple case if we clear and re-add)
                
                # Actually, simpler to just update row by row? 
                # Rich Tables don't support easy row updates. We have to re-generate the table rows 
                # or use a different layout. 
                # Optimization: Just append rows as they finish?
                # User wants "Streaming". Let's clear and re-add rows or use a list of results.
                
                # Better approach for Live Table: Maintain a list of row data and re-render table on update.
                
                # Verify
                res = await verify_claim(claim)
                
                # LLM Adjudication
                verdict = "Unverified"
                evidence_snippet = "No conclusive evidence found."
                color = "white"
                
                if res['best_evidence']:
                    evidence_snippet = "Reading detailed fact-check..."
                    # Ask LLM for verdict
                    judge_prompt = f"""Review this fact-check article content and determining if the claim "{claim}" is TRUE, FALSE, or MISLEADING.
                    
                    Article:
                    {res['best_evidence']}
                    
                    Return format: VERDICT::[True/False/Misleading/Unverified] REASON::[1 sentence summary]"""
                    
                    try:
                        resp = await self.client.chat(model=self.model, messages=[{"role": "user", "content": judge_prompt}])
                        judge_out = resp['message']['content']
                        
                        if "VERDICT::True" in judge_out: 
                            verdict = "TRUE"
                            color = "green"
                        elif "VERDICT::False" in judge_out: 
                            verdict = "FALSE"
                            color = "red"
                        elif "VERDICT::Misleading" in judge_out: 
                             verdict = "MISLEADING"
                             color = "yellow"
                        
                        if "REASON::" in judge_out:
                            evidence_snippet = judge_out.split("REASON::")[1].strip()
                    except:
                        pass
                elif res['sources']:
                     # Fallback to snippet analysis
                     top_src = res['sources'][0]
                     evidence_snippet = f"Source: {top_src['title']}"
                
                verification_summary.append({"claim": claim, "verdict": verdict, "reason": evidence_snippet})
                
                # Re-render table
                new_table = Table(title="[bold]Fact-Check Results[/bold]", show_header=True, expand=True, box=ROUNDED)
                new_table.add_column("#", width=3, style="dim")
                new_table.add_column("Claim", ratio=2)
                new_table.add_column("Verdict", width=12, justify="center")
                new_table.add_column("Evidence", ratio=3, style="dim")
                
                # Add completed rows
                for idx, item in enumerate(verification_summary, 1):
                     v_color = "green" if item['verdict'] == "TRUE" else "red" if item['verdict'] == "FALSE" else "yellow"
                     new_table.add_row(str(idx), item['claim'], f"[{v_color}]{item['verdict']}[/{v_color}]", item['reason'])
                
                # Add pending rows
                for p_idx in range(len(verification_summary) + 1, len(claims) + 1):
                     new_table.add_row(str(p_idx), claims[p_idx-1], "[dim]Pending...[/dim]", "")
                     
                live.update(new_table)

        # 4. Summarize (Generic summary based on verdicts)
        summary_prompt = f"Summarize the fact-check results for article: {title}\n"
        for v in verification_summary:
            summary_prompt += f"- {v['claim']}: {v['verdict']} ({v['reason']})\n"
            
        self.history.append({"role": "user", "content": summary_prompt})
        return await self._chat_with_llm()
