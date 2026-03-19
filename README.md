# browsegrab

> Token-efficient browser agent for local LLMs — Playwright + accessibility tree + MarkGrab, MCP native.

**browsegrab** is a lightweight browser automation library designed for local LLMs (8B-35B parameters). It combines Playwright's accessibility tree with [MarkGrab](https://github.com/QuartzUnit/markgrab)'s HTML-to-markdown conversion to achieve **5-8x fewer tokens per step** compared to alternatives like browser-use.

## Features

- **Token-efficient**: ~500-1,500 tokens/step (vs 4,000-10,000 for browser-use)
- **Local LLM first**: Optimized for vLLM, Ollama, and OpenAI-compatible endpoints
- **MCP native**: Built-in MCP server with 8 browser automation tools
- **MarkGrab integration**: HTML → clean markdown for content extraction
- **Accessibility tree + ref system**: Stable element references (`e1`, `e2`, ...) without vision models
- **Success pattern caching**: Zero LLM calls on repeated workflows
- **5-stage JSON parser**: Robust action parsing for local LLM outputs
- **Minimal dependencies**: Only `playwright` + `httpx` in core

## Installation

```bash
pip install browsegrab
playwright install chromium
```

With optional features:

```bash
pip install browsegrab[mcp]      # MCP server support
pip install browsegrab[content]  # MarkGrab content extraction
pip install browsegrab[cli]      # CLI with rich output
pip install browsegrab[all]      # Everything
```

## Quick Start

### Python API

```python
from browsegrab import BrowseSession

async with BrowseSession() as session:
    # Navigate and get accessibility tree snapshot
    await session.navigate("https://example.com")
    snap = await session.snapshot()
    print(snap.tree_text)
    # - heading "Example Domain" [level=1]
    # - link "Learn more": [ref=e1]

    # Click using ref ID
    result = await session.click("e1")
    print(result.url)  # https://www.iana.org/help/example-domains

    # Type into search box
    await session.navigate("https://en.wikipedia.org")
    snap = await session.snapshot()
    await session.type("e4", "Python programming", submit=True)

    # Extract compressed content (AX tree + markdown)
    content = await session.extract_content()
```

### CLI

```bash
# Accessibility tree snapshot
browsegrab snapshot https://example.com

# JSON output
browsegrab snapshot https://example.com -f json

# Extract content (AX tree + markdown)
browsegrab extract https://en.wikipedia.org/wiki/Python

# Agentic browse (requires LLM endpoint)
browsegrab browse https://example.com "Find the about page"
```

### MCP Server

```bash
browsegrab-mcp  # Start MCP server (stdio)
```

Claude Desktop / Cursor / VS Code config:

```json
{
  "mcpServers": {
    "browsegrab": {
      "command": "browsegrab-mcp"
    }
  }
}
```

**8 MCP tools**: `browser_navigate`, `browser_click`, `browser_type`, `browser_snapshot`, `browser_scroll`, `browser_extract_content`, `browser_go_back`, `browser_wait`

## How It Works

browsegrab separates **structure** (accessibility tree) from **content** (MarkGrab markdown), sending only what the LLM needs:

```
Raw HTML
├── Structure: Accessibility tree → interactive elements → [ref=eN]
│   → ~200-500 tokens
└── Content: MarkGrab → clean markdown (on-demand)
    → ~300-800 tokens

Combined: ~500-1,300 tokens per step
```

### Token efficiency (measured)

| Page | Interactive elements | Tokens | browser-use equivalent |
|------|---------------------|--------|----------------------|
| example.com | 1 | ~60 | ~500+ |
| Wikipedia article | 452 | ~1,254 | ~10,000+ |

## Architecture

```
browsegrab/
├── config.py                 # Dataclass configs (env var loading)
├── result.py                 # Result types (ActionResult, BrowseResult, ...)
├── session.py                # BrowseSession orchestrator
├── browser/
│   ├── manager.py            # Playwright lifecycle (async context manager)
│   ├── snapshot.py           # Accessibility tree + ref system
│   ├── selectors.py          # 4-strategy selector resolver
│   └── actions.py            # navigate, click, type, scroll, go_back, wait
├── dom/
│   ├── ref_map.py            # ref ID ↔ element bidirectional mapping
│   └── compress.py           # AX tree + MarkGrab → compressed context
├── llm/
│   ├── base.py               # LLMProvider ABC
│   ├── provider.py           # vLLM, Ollama, OpenAI-compatible
│   ├── prompt.py             # System prompts (~400 tokens)
│   └── parse.py              # 5-stage JSON fallback parser
├── agent/
│   ├── history.py            # Sliding window history compression
│   ├── cache.py              # Domain-based success pattern cache
│   └── loop_guard.py         # Duplicate action detection
├── __main__.py               # CLI (click)
└── mcp_server.py             # FastMCP server (8 tools)
```

## Configuration

All settings via environment variables (`BROWSEGRAB_*` prefix):

```bash
# Browser
BROWSEGRAB_BROWSER_HEADLESS=true
BROWSEGRAB_BROWSER_TIMEOUT_MS=30000

# LLM (for agentic browse)
BROWSEGRAB_LLM_PROVIDER=vllm          # vllm | ollama | openai
BROWSEGRAB_LLM_BASE_URL=http://localhost:30000/v1
BROWSEGRAB_LLM_MODEL=Qwen/Qwen3.5-32B-AWQ

# Agent
BROWSEGRAB_AGENT_MAX_STEPS=10
BROWSEGRAB_AGENT_ENABLE_CACHE=true
```

## Part of the QuartzUnit Ecosystem

| Library | Role |
|---------|------|
| [markgrab](https://github.com/QuartzUnit/markgrab) | Passive extraction (URL → markdown) |
| [snapgrab](https://github.com/QuartzUnit/snapgrab) | Passive capture (URL → screenshot) |
| [docpick](https://github.com/QuartzUnit/docpick) | Document OCR → structured JSON |
| **browsegrab** | Active automation (goal → browser actions → results) |

## Development

```bash
git clone https://github.com/QuartzUnit/browsegrab.git
cd browsegrab
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

# Unit tests (no browser needed)
pytest tests/ -m "not e2e"

# Full suite including E2E
pytest tests/ -v
```

## License

[MIT](LICENSE)

<!-- mcp-name: io.github.ArkNill/browsegrab -->
