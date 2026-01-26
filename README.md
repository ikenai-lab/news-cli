# 📰 News CLI

An AI-powered terminal news assistant that lets you search for news, read articles, fact-check claims, and have intelligent conversations—all from your command line.

![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/Status-Under_Development-orange)

![News CLI Demo](demo.gif)

## ✨ Features

### Core Features
- **🔍 Smart News Search** — Natural language search with automatic date parsing ("last year AI news" → searches 2024)
- **📖 Robust Article Reading** — Multi-method scraping with 6 fallback strategies including browser-based extraction
- **🤖 AI Summaries** — Context-aware summaries powered by local LLM (Ollama)
- **💬 Conversational** — Chat naturally with context-aware responses
- **✅ Fact-Checking** — Verify claims against trusted sources (Snopes, PolitiFact, FactCheck.org)

### User Experience
- **📊 Morning Briefing** — Geo-located dashboard with top news on startup
- **🔢 Sequential IDs** — Simple numeric IDs (1, 2, 3) for easy command typing
- **⌨️ Autocomplete** — Tab completion for commands with smart defaults
- **🔧 Configurable** — Adjust article limits, choose your LLM model
- **🌍 Location-Aware** — Automatic country detection for localized news
- **📝 Typo Correction** — LLM-powered input sanitization

## 📋 Prerequisites

- **Python 3.13+**
- **[Ollama](https://ollama.com/download)** — Local LLM runtime
- **[uv](https://docs.astral.sh/uv/)** — Fast Python package manager (recommended)

## 🚀 Installation

### Quick Install (Recommended)

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/ikenai-lab/news-cli/main/install.sh | bash
```

**Windows (PowerShell as Admin):**
```powershell
irm https://raw.githubusercontent.com/ikenai-lab/news-cli/main/install.ps1 | iex
```

**Global Install via uv (if you have uv installed):**
```bash
uv tool install git+https://github.com/ikenai-lab/news-cli.git
```

The install scripts will:
- ✅ Check for and install `uv` (Python package manager)
- ✅ Check for and install `Ollama` (Local LLM runtime)
- ✅ Clone the repository
- ✅ Install Python dependencies
- ✅ Pull the LLM model (~2GB)

### Manual Installation

```bash
# 1. Install prerequisites
# Linux/macOS:
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://ollama.com/install.sh | sh

# Windows (using winget):
winget install astral-sh.uv
winget install Ollama.Ollama

# 2. Clone and setup
git clone https://github.com/ikenai-lab/news-cli.git
cd news-cli
uv sync

# 3. Optional: Install browser for JS-heavy sites
uv run playwright install chromium

# 4. Pull the LLM model
ollama pull llama3.2:3b
```

## 🎯 Usage

```bash
# Run with defaults
uv run news-cli

# Specify model and article limit
uv run news-cli --model llama3.2:3b --limit 10
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--model` | `llama3.2:3b` | Ollama model to use |
| `--limit` | `5` | Articles per search (1-20) |


### Configuration

You can set persistent defaults (saved to `~/.config/news-cli/config.json`) so you don't need to specify options every time.

```bash
# View current config
news-cli config

# Set default model
news-cli config --model llama3.2:3b

# Set default article limit
news-cli config --limit 10
```

## ⌨️ Commands

Type `/` to see all available commands with autocomplete.

### Slash Commands

| Command | Description |
|---------|-------------|
| `/read <id>` | Read and summarize article (e.g. `/read 1`) |
| `/open <id>` | Open article in browser (e.g. `/open 1`) |
| `/save-article <id>` | Save article content to markdown file |
| `/save-session <file>` | Save conversation history to JSON file |
| `/analyze <id>` | AI analysis for bias, tone, facts |
| `/fact-check <id>` | Verify claims against fact-check sites |
| `/similar <id>` | Find related news from different sources |
| `/limit <n>` | Set articles per search (1-20) |
| `/briefing` | Refresh the morning briefing |
| `/quit` or `/exit` | Exit the application |

### Natural Language

Just type naturally! The AI understands:
- `"latest AI news"` → Search
- `"what happened with OpenAI last week"` → Search with date filter
- `"read the techcrunch article"` → Reads matching article
- `"give me article 3"` → Reads article #3
- `"read 1"` → Reads first article in list

## 🌅 Morning Briefing

On startup, you'll see a personalized dashboard:

```
📰 Morning Briefing (Location: India)

┏━━━━━━━━━━━━ India Headlines ━━━━━━━━━━━━┓
┃ # │ Date       │ Source     │ Title     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1 │ 2025-12-28 │ ndtv.com   │ ...       │
...

📰 12 articles loaded. Use /read <#> to read any article.
```

## 🔍 Fact-Checking

Verify claims in any article:

```
/fact-check 3

┏━━━━━━━━━━━━━━ Fact-Check Results ━━━━━━━━━━━━━━┓
┃ # │ Claim                │ Sources │ Top Source ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━┩
│ 1 │ "AI will replace..." │ 3       │ Snopes...  │
...
```

## 🏗️ Project Structure

```
news-cli/
├── src/
│   ├── main.py           # CLI entry point
│   ├── agent.py          # NewsAgent with LLM integration
│   ├── startup.py        # Ollama checks + geolocation
│   ├── tools/
│   │   ├── search.py     # DuckDuckGo search with time filters
│   │   ├── scraper.py    # Multi-method article scraper
│   │   └── fact_check.py # Claim verification tool
│   └── ui/
│       ├── render.py     # Rich UI components
│       └── completer.py  # Slash command autocomplete
├── pyproject.toml
└── README.md
```

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `ollama` | Local LLM client |
| `ddgs` | DuckDuckGo search |
| `nodriver` | Stealth browser automation (replacing Selenium/Playwright) |
| `cloudscraper` | Cloudflare bypass |
| `trafilatura` | Article content extraction |
| `readability-lxml` | Fallback content extraction |
| `rich` | Terminal UI components |
| `typer` | CLI framework |
| `httpx` | HTTP client |
| `prompt-toolkit` | Command autocomplete |

## 🔧 Scraping Architecture

The scraper uses a multi-layered approach with 6 fallback methods:

```
┌─────────────────────────────────────────────────────────┐
│ 1. Cloudscraper                                         │
│    ↳ Fast, lightweight Cloudflare bypass                │
│    ↓ (if fails)                                         │
│ 2. Nodriver (Stealth Browser)                           │
│    ↳ Chrome DevTools Protocol based (masked as User)    │
│    ↳ Handles heavy JS and complex anti-bots             │
│    ↓ (if fails)                                         │
│ 3. Direct Fetch (httpx + trafilatura)                   │
│    ↳ Standard HTTP with article extraction              │
│    ↓ (if fails)                                         │
│ 4. Archive.org (Wayback Machine)                        │
│    ↳ Check for cached snapshots if live site fails      │
└─────────────────────────────────────────────────────────┘
```

For sites that block all scraping (like MSN), use `/open <id>` to view in browser.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
