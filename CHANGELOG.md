# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-03-19

### Added
- Initial release
- Token-efficient browser agent optimized for local LLMs (8B-35B parameters)
- Playwright + accessibility tree with stable ref system (`e1`, `e2`, ...)
- MarkGrab integration for HTML to clean markdown conversion
- ~500-1,500 tokens per step (5-8x fewer than alternatives)
- MCP server with 8 browser automation tools
- Success pattern caching for zero LLM calls on repeated workflows
- 5-stage JSON parser for robust local LLM action parsing
- Agentic browse mode with multi-step task execution
- CLI interface: snapshot, extract, browse commands
- Python async API (`BrowseSession`)
- Viewport presets and element interaction (click, type, scroll)
- 200 tests
