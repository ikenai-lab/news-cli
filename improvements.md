# Project Improvements & Features

Based on a detailed analysis of the `news-cli` codebase, here are the recommended improvements, bug fixes, and new features.

## 🛠️ Code Structure & Quality

### 1. Refactor `NewsAgent` Class
**Priority:** High
The `NewsAgent` class in `src/agent.py` is becoming a monolith (God Object). It handles intent classification, chat logic, search execution, and fact-checking.
- **[x] Improvement:** Split into smaller components:
    - `IntentClassifier`: Hybrid approach implemented (Regex > LLM).
    - `SearchHandler`: Logic decoupled into tools.
    - `ChatHandler`: Async chat flow implemented.
    - `ActionExecutor`: Tools separated.

### 2. Centralized Configuration
**Priority:** Medium
Configuration values (Model name "llama3.2:3b", timeouts, user agent headers) are hardcoded across multiple files.
- **[x] Improvement:** Create `src/config.py` or use a `.env` file managed by `pydantic-settings`.
    - **[x]** Allow users to set their preferred default model (e.g., via `news-cli config --set model=llama3:8b`).
    - **[x]** Centralize timeout values.

### 3. Asynchronous Architecture
**Priority:** Medium
While `scraper.py` uses some async via `crawl4ai`, the main `agent.py` and `main.py` flows are synchronous.
- **[x] Improvement:** Fully embrace `asyncio`.
    - **[x]** Make `NewsAgent` methods async.
    - **[x]** Handle search, scrape, and LLM generation concurrently where possible.
    - **[x]** This will improve interface responsiveness, especially during long scraping tasks.

## 🐛 Bug Fixes & Reliability

### 4. Robust Startup Checks
**Priority:** High
`check_and_start_ollama()` in `src/startup.py` relies on `subprocess.call` which might hang or fail silently on some systems.
- **[x] Fix:** Add better timeouts and error handling for subprocess calls.
- **[x] Fix:** Check for internet connectivity before attempting to pull models or run country detection.

### 5. Intent Classification Edge Cases
**Priority:** Medium
The regex-based and LLM-based intent verification in `_classify_intent` handles basic cases but might fail on nuanced queries.
- **[x] Fix:** specific edge cases where "read article about X" might be confused with "search for X".
- **[x] Improvement:** Implement a clearer state machine for the agent (e.g., if just searched, bias towards "READ").

## 🧪 Testing

### 6. Improve Test Coverage
**Priority:** High
Current tests focus heavily on `scraper.py`.
- **[x] New Tests:**
    - `tests/test_agent.py`: Mock `ollama` client to test `NewsAgent` logic without running an actual LLM.
    - `tests/test_search.py`: Test `search_news` with mocked `ddgs` responses.
    - `tests/test_startup.py`: Test configuration loading and startup checks.

## ✨ New Features

### 7. Offline Mode & Caching
**Priority:** Medium
Currently, `search_cache` is in-memory and lost on exit.
- **Feature:** Persist articles to a local SQLite database or JSON file.
- **Benefit:** Allow users to read previously fetched articles even when offline (`/history` command).

### 8. Export Functionality
**Priority:** Low
Users can currently only interact via terminal or see markdown.
- **Feature:** `/export <id> pdf` or `/export <id> html`.
- **Benefit:** Shareable reports.

### 9. Multi-Source Search
**Priority:** Medium
Currently relies on DuckDuckGo.
- **Feature:** Add Google News RSS feed support as a fallback or alternative source.
- **Feature:** Add Bing News support.

### 10. System Prompts & Persona Customization
**Priority:** Low
The agent has a fixed "helpful news assistant" persona.
- **Feature:** Allow users to define custom personas (e.g., "Skeptical Fact Checker", "Excited Tech Enthusiast") via config.

### 11. Interactive TUI
**Priority:** Low
The current UI is a command-line REPL.
- **Feature:** Use `textual` or `rich` 's live display to create a more interactive TUI where users can navigate headlines with arrow keys instead of typing `/read 1`.

## 🚀 Performance

### 12. Streaming Responses
**Priority:** Medium
`_chat_with_llm` supports streaming, but other long-running tasks like fact-checking do not provide real-time feedback loops beyond a spinner.
- **Improvement:** Stream intermediate steps of logical reasoning (Chain of Thought) to the user during complex tasks like fact-checking.
