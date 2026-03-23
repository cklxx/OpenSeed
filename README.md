<p align="center">
  <img src="screenshot-20260317-144253.png" alt="OpenSeed" width="80%" />
</p>

<h1 align="center">OpenSeed</h1>

<p align="center">
  <strong>AI-powered research workflow CLI.</strong><br/>
  Discover, read, analyze, and synthesize academic papers with Claude — from a single search to a full autonomous research report.
</p>

<p align="center">
  <a href="https://github.com/cklxx/openSeed/actions"><img src="https://github.com/cklxx/openSeed/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://pypi.org/project/openseed/"><img src="https://img.shields.io/pypi/v/openseed.svg" alt="PyPI"/></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"/></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"/></a>
</p>

---

## Why OpenSeed?

- **One command, full report** — `openseed research run "topic"` runs multi-round discovery, analysis, and synthesis autonomously.
- **Real ranking** — papers ranked by actual citation counts from Semantic Scholar, not keyword matching.
- **Claude-native** — every analysis step powered by Claude: summarize, review, compare, Q&A, code gen.
- **Your library, your tools** — MCP server exposes your paper library to Claude Code / Claude Desktop.
- **Local-first** — SQLite storage, no cloud dependency beyond the LLM API.

---

## Quick Start

```bash
pip install openseed

openseed doctor    # check environment
openseed setup     # configure auth + model
```

**Auth** — any of these work:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # Anthropic API key
claude setup-token                     # OAuth (openseed setup detects it)
```

---

## What You Can Do

### Search & Discover

```bash
openseed paper search "diffusion models" --count 20
openseed agent search "multi-agent systems"          # deeper search with trend summary
```

### Autonomous Research

```bash
openseed research run "ViT image classification"
# discover → analyze → synthesize → markdown report
```

### Manage Your Library

```bash
openseed paper add https://arxiv.org/abs/1706.03762
openseed paper list
openseed paper show <id>
```

### Analyze Papers

```bash
openseed agent summarize <id>            # structured summary
openseed agent summarize <id> --cn       # Chinese summary
openseed agent review <id>               # peer review
openseed agent compare <id1> <id2>       # side-by-side comparison
openseed agent ask "What is RLHF?"       # research Q&A
openseed agent codegen <id>              # generate experiment code
```

### MCP Server

```bash
openseed mcp    # expose library as Claude tools
```

Available tools: `library_stats`, `search_papers`, `get_paper`, `get_graph`, `search_memories`, `ask_research`

---

## How It Works

```
Search query
     ↓
  ArXiv + Claude WebSearch ── find candidates
     ↓
  Semantic Scholar ────────── rank by citations, fetch metadata
     ↓
  PDF extraction (PyMuPDF) ── full text
     ↓
  Claude analysis ─────────── summarize · review · compare · synthesize
     ↓
  SQLite library ──────────── persist with knowledge graph + FTS5
     ↓
  MCP / Web / CLI ─────────── access from anywhere
```

---

## Architecture

```
src/openseed/
├── cli/                 Click CLI: paper, agent, research, experiment
├── agent/               AI-powered analysis
│   ├── autoresearch     autonomous multi-round research engine
│   ├── reader           structured summarize / analyze
│   ├── assistant        freeform research Q&A
│   ├── discovery        paper discovery via Claude + Semantic Scholar
│   ├── compare          side-by-side paper comparison
│   ├── strategy         gap analysis + reading recommendations
│   ├── memory           FTS5-backed conversation history
│   ├── context          library-aware prompt assembly
│   └── latex            related-work export with BibTeX
├── services/            External integrations
│   ├── arxiv            ArXiv metadata fetch + search
│   ├── scholar          Semantic Scholar API
│   ├── pdf              PDF text extraction
│   ├── rss · watch      feed discovery + scheduled watches
│   ├── cron · digest    crontab management + digest generation
│   └── sharing          session export/import
├── storage/             SQLite CRUD + knowledge graph + connection pool
├── models/              Pydantic v2 data models
├── mcp/                 MCP server (library as Claude tools)
├── web/                 FastAPI dashboard
├── auth.py              Anthropic client factory
├── config.py            paths, default model
└── doctor.py            environment health checks
```

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=cklxx/openSeed&type=Date)](https://star-history.com/#cklxx/openSeed&Date)

---

## License

[MIT](LICENSE) &copy; 2025 cklxx
