import re
import ollama
from rich.console import Console

from src.tools.search import search_news
from src.tools.scraper import scrape_article
from src.tools.fact_check import verify_claim, extract_claims_prompt
from src.ui.render import print_search_results, print_article, print_error

console = Console()

class NewsAgent:
    def __init__(self, model: str = "llama3.2:3b", article_limit: int = 5):
        self.model = model
        self.article_limit = article_limit
        self.history = [
            {"role": "system", "content": "You are a helpful news assistant. You have access to search tools. When provided with search results or article content, summarize them concisely for the user. If the user asks to read a specific item by number, assume the content will be provided to you."}
        ]
        self.search_cache = {}  # Maps 1, 2, 3 -> {url, title}

    def _sanitize_input(self, text: str) -> str:
        """
        Uses LLM to sanitize and clean user input before processing.
        Fixes typos, grammatical errors, and normalizes the text.
        """
        # Quick normalization first (whitespace)
        text = ' '.join(text.split())
        
        # Skip LLM sanitization for very short inputs or slash commands
        if len(text) < 5 or text.startswith("/"):
            return text
        
        prompt = f"""Fix any typos or spelling mistakes in the following text. 
Return ONLY the corrected text, nothing else. Do not add punctuation or change the meaning.
If there are no typos, return the text as-is.

Text: "{text}"

Corrected text:"""

        try:
            response = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            corrected = response['message']['content'].strip()
            
            # Remove any quotes the LLM might have added
            corrected = corrected.strip('"\'')
            
            # Safety check: if LLM returned something wildly different, use original
            if len(corrected) > len(text) * 2 or len(corrected) < len(text) / 2:
                return text
                
            if corrected != text:
                console.print(f"[dim]Corrected: {corrected}[/dim]")
            
            return corrected
        except:
            return text

    def process_user_input(self, user_text: str) -> str:
        """
        Determines intent, executes tools if needed, and returns the response.
        """
        # Sanitize input first
        user_text = self._sanitize_input(user_text)
        
        # 0. Handle Slash Commands
        if user_text.startswith("/"):
            parts = user_text.strip().split()
            command = parts[0].lower()
            args = parts[1:]
            
            if command == "/read" and args:
                return self._handle_read_match(args[0])
            elif command == "/open" and args:
                return self._open_in_browser(args[0])
            elif command == "/":
                 from rich.table import Table
                 from rich.box import ROUNDED
                 table = Table(title="[bold]Available Commands[/bold]", box=ROUNDED, show_header=True, header_style="bold magenta")
                 table.add_column("Command", style="cyan", no_wrap=True)
                 table.add_column("Usage", style="green")
                 table.add_column("Description", style="white")
                 
                 table.add_row("/read", "/read <id>", "Read full content of article #ID")
                 table.add_row("/save", "/save <id>", "Save article #ID to Markdown file")
                 table.add_row("/save", "/save <file>", "Save current session history")
                 table.add_row("/analyze", "/analyze <id>", "AI analysis (bias, facts, tone)")
                 table.add_row("/similar", "/similar <id>", "Search for related news")
                 table.add_row("/more-source", "/more-source <id>", "Find story from other sources")
                 table.add_row("/quit", "/quit", "Exit application")
                 
                 console.print(table)
                 return ""
            elif command == "/save":
                if not args: return "Usage: /save <filename> OR /save <id>"
                # Check if arg is an ID (save article) or filename (save session)
                # Heuristic: if valid ID, save article. Else filename.
                if args[0].isdigit() and int(args[0]) in self.search_cache:
                    return self._save_article(int(args[0]))
                else:
                    return self._save_session(args[0])
            elif command == "/analyze" and args:
                return self._analyze_article(args[0])
            elif command == "/similar" and args:
                return self._find_similar(args[0])
            elif command == "/more-source" and args:
                return self._find_more_sources(args[0])
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
                return self._fact_check_article(args[0])
            elif command == "/briefing":
                return "REFRESH_BRIEFING"  # Special signal for main loop
            elif command in ["/exit", "/quit"]:
                # handled by main loop but good to have here just in case? 
                # actually main loop catches this before agent.
                return "Goodbye!"
            else:
                return f"Unknown command: {command}"

        # Get intent from LLM

        # Get intent from LLM
        intent = self._classify_intent(user_text)
        console.print(f"[dim]DEBUG: Intent={intent}[/dim]") # User reported issue, verify intent
        
        if intent == "READ":
            return self._handle_read_intent(user_text)
        elif intent == "SEARCH":
            return self._handle_search_intent(user_text)
        else:
            # Fallback: Sometimes LLM says CHAT for "give me the article"
            if any(k in user_text.lower() for k in ["article", "read", "give me", "show me"]):
                 console.print("[dim]DEBUG: Checking fallback read...[/dim]")
                 possible_read = self._handle_read_intent(user_text, strict=False)
                 if possible_read: 
                     return possible_read

            # Default Chat
            self.history.append({"role": "user", "content": user_text})
            return self._chat_with_llm()

    def _handle_read_intent(self, user_text: str, strict: bool = True) -> str | None:
        """
        Handles READ intent by finding the article by number, source, or title.
        Returns None if no match found (and strict=False), otherwise returns response string.
        """
        if not self.search_cache:
            if strict:
                 return "No search results available. Please search for news first."
            return None
        
        # Try to match by number first
        read_match = re.search(r"(\d+)", user_text)
        if read_match:
            item_id = int(read_match.group(1))
            if item_id in self.search_cache:
                return self._scrape_and_summarize(item_id)
        
        # Try to match by source domain
        user_lower = user_text.lower()
        for item_id, item in self.search_cache.items():
            url = item.get("url", "")
            # Extract domain from URL
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.replace("www.", "")
                # Match "yahoo" in "finance.yahoo.com"
                if domain:
                     # Check if user text contains the main part of the domain (e.g. "yahoo" from "finance.yahoo.com")
                     # Split domain by dots and check parts
                     parts = domain.split('.')
                     if any(part in user_lower and len(part) > 3 for part in parts):
                         return self._scrape_and_summarize(item_id)
            except:
                pass
        
        if strict:
            # If no match found, ask LLM to help identify which article
            return self._identify_article_with_llm(user_text)
        
        return None

    def _scrape_and_summarize(self, item_id: int) -> str:
        """
        Scrapes an article and returns a summary.
        """
        item = self.search_cache[item_id]
        url = item["url"]
        title = item["title"]
        console.print(f"[blue]Scraping article {item_id}: {url}[/blue]")
        
        article_content = scrape_article(url)
        
        if article_content.startswith("Error:"):
            print_error(article_content)
            return "I was unable to read the article due to a scraping error."
        
        # Render article with title from cache
        print_article(title, article_content)

        # Add context to history
        user_message = f"Please summarize this article I asked to read:\n\nTitle: {title}\n\n{article_content[:5000]}"
        self.history.append({"role": "user", "content": user_message})
        
        return self._chat_with_llm()

    def _identify_article_with_llm(self, user_text: str) -> str:
        """
        Uses LLM to identify which article the user is referring to.
        """
        cache_summary = "\n".join([f"{i}. {item['title']} (Source: {item['url']})" for i, item in self.search_cache.items()])
        
        prompt = f"""The user asked: "{user_text}"

Here are the available articles:
{cache_summary}

Which article number (1-{len(self.search_cache)}) is the user referring to? Reply with ONLY the number, or "NONE" if unclear."""
        
        try:
            response = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            answer = response['message']['content'].strip()
            
            if answer.isdigit() and int(answer) in self.search_cache:
                return self._scrape_and_summarize(int(answer))
            else:
                return "I couldn't determine which article you're referring to. Please specify the article number (e.g., 'read 2')."
        except:
            return "I couldn't determine which article you're referring to. Please specify the article number."

    def _handle_search_intent(self, user_text: str, skip_date_extraction: bool = False) -> str:
        """
        Handles SEARCH intent.
        skip_date_extraction: If True, bypasses LLM date processing (used for /similar, /more-source)
        """
        if skip_date_extraction:
            search_query = user_text
            timelimit = None
        else:
            # Extract date context from query using LLM
            search_query, timelimit = self._extract_date_context(user_text)
        
        console.print(f"[blue]Searching for: {search_query}[/blue]")
        if timelimit:
            console.print(f"[dim]Time filter: {timelimit}[/dim]")
        
        results = search_news(search_query, max_results=self.article_limit, timelimit=timelimit)
        
        if not results:
            return "I couldn't find any news matching your query."
        
        # Show Results Table
        print_search_results(results)

        # Update Cache with Title and URL
        self.search_cache = {}
        formatted_results = "Here are the search results:\n"
        for i, res in enumerate(results, 1):
            self.search_cache[i] = {"url": res['href'], "title": res['title']}
            formatted_results += f"{i}. {res['title']} ({res['date']})\n   {res['body']}\n"
        
        user_message = f"I searched for '{search_query}' and found these results:\n{formatted_results}\nPlease present these to me concisely."
        self.history.append({"role": "user", "content": user_message})
        
        return self._chat_with_llm()

    def _extract_date_context(self, query: str) -> tuple[str, str | None]:
        """
        Uses LLM to extract date context from query.
        Returns (cleaned_query, timelimit) where timelimit is 'd', 'w', 'm', 'y', or None.
        """
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.now().year
        
        prompt = f"""Today's date is {current_date}.

Given this search query: "{query}"

1. Does this query contain a time reference (like "last year", "yesterday", "this week", "2024", etc.)?
2. If yes, what is the appropriate time filter?

Respond in this exact format:
TIMELIMIT: [d/w/m/y/NONE]
QUERY: [cleaned query with year numbers if needed, or original query]

Rules:
- d = last day
- w = last week  
- m = last month
- y = last year
- NONE = no time filter needed

Examples:
- "AI news from last week" → TIMELIMIT: w, QUERY: AI news
- "2024 election results" → TIMELIMIT: NONE, QUERY: 2024 election results
- "yesterday's sports news" → TIMELIMIT: d, QUERY: sports news
- "last year AI developments" → TIMELIMIT: y, QUERY: {current_year - 1} AI developments
- "latest tech news" → TIMELIMIT: NONE, QUERY: latest tech news"""

        try:
            response = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            answer = response['message']['content'].strip()
            console.print(f"[dim]DEBUG Date extraction: {answer}[/dim]")  # Debug output
            
            # Parse response
            timelimit = None
            cleaned_query = query
            
            for line in answer.split('\n'):
                if line.upper().startswith("TIMELIMIT:"):
                    tl = line.split(":", 1)[1].strip().lower()
                    if tl in ['d', 'w', 'm', 'y']:
                        timelimit = tl
                elif line.upper().startswith("QUERY:"):
                    cleaned_query = line.split(":", 1)[1].strip()
            
            return (cleaned_query, timelimit)
        except Exception as e:
            console.print(f"[dim]DEBUG Date extraction error: {e}[/dim]")
            return (query, None)

    def _classify_intent(self, text: str) -> str:
        """
        Uses the LLM to classify the user's intent.
        Returns: SEARCH, READ, or CHAT
        """
        classification_prompt = [
            {
                "role": "system",
                "content": """You are an intent classifier. Classify the user's message into exactly one of these categories:

- SEARCH: User wants to FIND or GET news, articles, or information about a topic. Examples:
  * "what's happening with AI"
  * "latest tech news"
  * "give me news about climate change"
  * "show me top headlines"
  * "give me last year's AI news"
  * Any request to find/get news on a TOPIC

- READ: User wants to read a SPECIFIC article from search results shown earlier. They refer to it by NUMBER, source name, or exact title. Examples:
  * "read 1", "read article 2"
  * "show me the yahoo article"
  * "open the one about stocks"
  * ONLY use READ if they reference a specific previously-shown article

- CHAT: General conversation, questions about already-shown content, or anything else

IMPORTANT: If the user says "give me news about X" or "show me news on Y", that is SEARCH, not READ.
Respond with ONLY the category name (SEARCH, READ, or CHAT). Nothing else."""
            },
            {"role": "user", "content": text}
        ]
        
        try:
            response = ollama.chat(model=self.model, messages=classification_prompt)
            intent = response['message']['content'].strip().upper()
            
            # Validate the response
            if intent in ["SEARCH", "READ", "CHAT"]:
                return intent
            else:
                return "CHAT"
        except Exception as e:
            console.print(f"[dim]Intent classification failed: {e}. Defaulting to CHAT.[/dim]")
            return "CHAT"

    def _chat_with_llm(self) -> str:
        try:
            full_response = ""
            from rich.live import Live
            from rich.markdown import Markdown
            
            console.print("[bold purple]Agent:[/bold purple]")
            
            with Live(Markdown(""), refresh_per_second=10, console=console) as live:
                for chunk in ollama.chat(model=self.model, messages=self.history, stream=True):
                    content = chunk['message']['content']
                    full_response += content
                    live.update(Markdown(full_response))
            
            console.print()
            if not full_response:
                return "I'm sorry, I couldn't generate a response. Please try again."
            
            self.history.append({"role": "assistant", "content": full_response})
            return full_response

        except Exception as e:
            return f"Error communicating with AI: {e}"

    def _handle_read_match(self, arg: str) -> str:
        if arg.isdigit() and int(arg) in self.search_cache:
            return self._scrape_and_summarize(int(arg))
        return "Invalid article ID."

    def _save_session(self, filename: str) -> str:
        try:
            import json
            with open(filename, "w") as f:
                json.dump(self.history, f, indent=2)
            return f"Session saved to {filename}"
        except Exception as e:
            return f"Error saving session: {e}"

    def _save_article(self, item_id: int) -> str:
        item = self.search_cache[item_id]
        url = item["url"]
        title = item["title"]
        console.print(f"[blue]Scraping to save article {item_id}...[/blue]")
        content = scrape_article(url)
        if content.startswith("Error:"): return content
        
        filename = f"article_{item_id}.md"
        with open(filename, "w") as f:
            f.write(f"# {title}\n\nSource: {url}\n\n{content}")
        return f"Article saved to {filename}"

    def _analyze_article(self, arg: str) -> str:
        if not arg.isdigit() or int(arg) not in self.search_cache: return "Invalid ID."
        item_id = int(arg)
        # Check if URL exists in cache before accessing
        item = self.search_cache.get(item_id)
        if not item: return "Invalid ID."
        
        url = item["url"]
        
        console.print(f"[blue]Analyzing article {item_id}...[/blue]")
        content = scrape_article(url)
        if content.startswith("Error:"): return content

        prompt = f"Perform a critical analysis of this article. Identify potential bias, fact-check claims where possible using your knowledge, and evaluate the tone.\n\n{content[:6000]}"
        self.history.append({"role": "user", "content": prompt})
        return self._chat_with_llm()

    def _find_similar(self, arg: str) -> str:
        if not arg.isdigit() or int(arg) not in self.search_cache: return "Invalid ID."
        item = self.search_cache[int(arg)]
        title = item["title"]
        url = item["url"]
        
        # Extract domain to exclude
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace("www.", "")
            # Clean title and exclude current source
            clean_title = title.split(" - ")[0].split(" | ")[0]
            # Search with exclusion
            query = f'{clean_title} -site:{domain}'
            return self._handle_search_intent(query, skip_date_extraction=True)
        except:
            return self._handle_search_intent(f"news similar to {title}", skip_date_extraction=True)
        
    def _find_more_sources(self, arg: str) -> str:
        if not arg.isdigit() or int(arg) not in self.search_cache: return "Invalid ID."
        item = self.search_cache[int(arg)]
        title = item["title"]
        url = item["url"]
        
        # Strip common suffixes like " - CNN", " | BBC" to get raw headline
        clean_title = title.split(" - ")[0].split(" | ")[0]
        
        # Extract domain to exclude original source
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace("www.", "")
            # Search for exact headline from different sources
            query = f'"{clean_title}" -site:{domain}'
            return self._handle_search_intent(query, skip_date_extraction=True)
        except:
            return self._handle_search_intent(f'"{clean_title}"', skip_date_extraction=True)

    def _fact_check_article(self, arg: str) -> str:
        """
        Performs fact-checking on an article by extracting claims and verifying them.
        """
        from rich.table import Table
        from rich.panel import Panel
        
        if not arg.isdigit() or int(arg) not in self.search_cache: 
            return "Invalid ID."
        
        item_id = int(arg)
        item = self.search_cache.get(item_id)
        if not item: 
            return "Invalid ID."
        
        url = item["url"]
        title = item["title"]
        
        console.print(f"[blue]Fact-checking article {item_id}: {title}[/blue]")
        
        # Step 1: Scrape article
        content = scrape_article(url)
        if content.startswith("Error:"): 
            return content
        
        # Step 2: Extract claims using LLM
        console.print("[dim]Extracting claims...[/dim]")
        prompt = extract_claims_prompt(content)
        
        try:
            response = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            claims_text = response['message']['content'].strip()
        except Exception as e:
            return f"Error extracting claims: {e}"
        
        if claims_text == "NO_CLAIMS" or not claims_text:
            return "No verifiable claims found in this article."
        
        # Parse claims
        claims = []
        for line in claims_text.split('\n'):
            line = line.strip()
            if line and line[0].isdigit():
                # Remove numbering
                claim = line.lstrip('0123456789.)-: ').strip()
                if claim:
                    claims.append(claim)
        
        if not claims:
            return "No verifiable claims found in this article."
        
        # Step 3: Verify each claim
        console.print(f"[dim]Verifying {len(claims)} claims...[/dim]")
        
        results_table = Table(title="[bold]Fact-Check Results[/bold]", show_header=True, expand=True)
        results_table.add_column("#", width=3)
        results_table.add_column("Claim", max_width=50)
        results_table.add_column("Sources Found", width=15)
        results_table.add_column("Top Source")
        
        verification_summary = []
        
        for i, claim in enumerate(claims[:5], 1):  # Limit to 5 claims
            result = verify_claim(claim, max_sources=3)
            source_count = result['source_count']
            
            top_source = "No sources found"
            if result['sources']:
                top = result['sources'][0]
                top_source = f"{top['title'][:40]}..."
            
            results_table.add_row(
                str(i),
                claim[:50] + "..." if len(claim) > 50 else claim,
                str(source_count),
                top_source
            )
            
            verification_summary.append({
                "claim": claim,
                "sources": result['sources']
            })
        
        console.print(results_table)
        
        # Step 4: Ask LLM to summarize findings
        summary_prompt = f"""Based on the fact-checking results below, provide a summary of the verification status.

Article: {title}

Claims and Sources:
"""
        for v in verification_summary:
            summary_prompt += f"\nClaim: {v['claim']}\n"
            if v['sources']:
                for s in v['sources'][:2]:
                    summary_prompt += f"  - Source: {s['title']}\n    Snippet: {s['snippet'][:100]}...\n"
            else:
                summary_prompt += "  - No verification sources found\n"
        
        summary_prompt += "\nProvide a brief fact-check summary (2-3 sentences):"
        
        self.history.append({"role": "user", "content": summary_prompt})
        return self._chat_with_llm()

    def _open_in_browser(self, arg: str) -> str:
        """
        Opens the article URL in the user's default browser.
        """
        import webbrowser
        
        if not arg.isdigit() or int(arg) not in self.search_cache:
            return "Invalid ID."
        
        item_id = int(arg)
        item = self.search_cache.get(item_id)
        if not item:
            return "Invalid ID."
        
        url = item["url"]
        title = item["title"]
        
        try:
            webbrowser.open(url)
            return f"Opened in browser: {title}"
        except Exception as e:
            return f"Error opening browser: {e}\nURL: {url}"

