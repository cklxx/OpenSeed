# Changelog

All notable changes to this project will be documented in this file.

## [0.9.1] - 2026-03-19

### Added
- `feedparser>=6.0` dependency; fixed async/sync boundary in `reader.py` and `autoresearch.py`
- API key authentication middleware for web dashboard (controlled via `OPENSEED_API_KEY` env var)
- SQLite connection pooling via FastAPI dependency injection
- `openseed version show` and `openseed version bump [patch|minor|major]` CLI commands for version management
- Rich progress bars and live status indicators for long-running CLI operations

## [0.9.0] - 2026-03-01

### Initial release
- AI-powered research workflow management CLI
- ArXiv and Semantic Scholar integration
- PDF processing and library management
- Agent-based auto-research pipeline
- Web dashboard (FastAPI)
