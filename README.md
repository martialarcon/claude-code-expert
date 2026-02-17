# AI Architect v2

> Automated technical intelligence system for the Claude Code and AI-assisted development ecosystem.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview

AI Architect v2 is a **radar for technical intelligence** that collects, analyzes, and synthesizes information about Claude Code and AI-assisted development ecosystems. It generates structured knowledge in Markdown format stored in ChromaDB for semantic search.

### Key Features

- **6 Data Collectors** - Automated collection from docs, GitHub, blogs, StackOverflow
- **Intelligent Ranking** - Signal-based filtering with Claude Sonnet
- **Novelty Detection** - Vector similarity against historical content
- **Strategic Synthesis** - Daily/weekly/monthly reports with Claude Opus
- **Push Notifications** - Mobile alerts via ntfy.sh

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Collectors  │────▶│  Processors │────▶│   Storage   │────▶│   Output    │
│ (6 sources) │     │  (4 stages) │     │  (ChromaDB) │     │  (Markdown) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                  │
                                                                  ▼
                                                           ┌─────────────┐
                                                           │  Notifier   │
                                                           │  (ntfy.sh)  │
                                                           └─────────────┘
```

### Data Sources

| Source | Type | Description |
|--------|------|-------------|
| Docs | Official | Anthropic & Claude documentation with diff detection |
| GitHub Signals | Primary | Issues/PRs from critical repositories |
| GitHub Emerging | Discovery | Repos <100 stars with rapid growth |
| GitHub Consolidated | Popular | Repos >100 stars in AI ecosystem |
| Blogs | Editorial | Simon Willison, Anthropic blog, RSS feeds |
| StackOverflow | Behavior | Questions tagged claude, anthropic, llm |

### Processing Pipeline

1. **Collection** - Fetch items from all enabled sources
2. **Signal Ranking** - Score items 1-10 by relevance (Claude Sonnet)
3. **Novelty Detection** - Filter duplicates via vector similarity
4. **Deep Analysis** - Extract insights and actionability
5. **Synthesis** - Generate strategic reports (Claude Opus)
6. **Output** - Markdown files + ChromaDB storage

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Anthropic API key

### Installation

```bash
# Clone the repository
git clone https://github.com/martialarcon/claude-code-expert.git
cd claude-code-expert

# Create environment file
cp .env.example .env

# Add your API key
echo "ANTHROPIC_API_KEY=your_key_here" >> .env

# Build and run
docker compose up -d
```

### Run Daily Cycle

```bash
docker compose exec app python main.py --mode daily
```

### Check Output

```bash
# View today's digest
cat output/daily/$(date +%Y-%m-%d).md

# View index
cat output/index.md
```

## Configuration

Edit `config.yaml` to customize:

```yaml
# Claude models
models:
  analysis: "claude-sonnet-4-20250514"
  synthesis: "claude-opus-4-6"

# Processing thresholds
thresholds:
  signal_score_min: 4    # Discard items below this score
  novelty_score_min: 0.3 # Minimum novelty to process
  batch_size: 10         # Items per Claude call

# Enable/disable collectors
collectors:
  docs:
    enabled: true
  github_signals:
    enabled: true
  # ...
```

## Directory Structure

```
ai-architect/
├── main.py                 # Entry point
├── config.yaml             # Configuration
├── requirements.txt        # Python dependencies
├── Dockerfile
├── docker-compose.yml
├── src/
│   ├── collectors/         # Data collection modules
│   │   ├── base.py         # Abstract base class
│   │   ├── docs.py
│   │   ├── github_*.py
│   │   ├── blogs.py
│   │   └── stackoverflow.py
│   ├── processors/         # Processing pipeline
│   │   ├── claude_client.py
│   │   ├── signal_ranker.py
│   │   ├── novelty_detector.py
│   │   ├── analyzer.py
│   │   └── synthesizer.py
│   ├── storage/            # Persistence layer
│   │   ├── vector_store.py # ChromaDB
│   │   └── markdown_gen.py
│   └── utils/              # Utilities
│       ├── config.py
│       ├── logger.py
│       └── notifier.py
├── output/                 # Generated content
│   ├── daily/
│   ├── weekly/
│   ├── monthly/
│   └── index.md
├── data/                   # Persistent data
│   ├── chromadb/
│   ├── snapshots/
│   └── transcripts/
└── scripts/
    ├── setup_cron.sh       # Automated scheduling
    └── test_e2e.py         # End-to-end tests
```

## Automation

### Setup Cron Jobs

```bash
chmod +x scripts/setup_cron.sh
./scripts/setup_cron.sh
```

This configures:
- Daily digest at 00:00
- Weekly synthesis Monday 01:00
- Monthly report on 1st at 02:00

### Notifications

Configure ntfy.sh for mobile push notifications:

```yaml
notifications:
  ntfy:
    enabled: true
    topic: "ai-architect"  # Subscribe at ntfy.sh/ai-architect
```

## Target Platform

Optimized for **NVIDIA Jetson Orin Nano**:

| Spec | Value |
|------|-------|
| Architecture | ARM64 (aarch64) |
| Memory | 8GB LPDDR5 (shared) |
| Execution | Sequential (memory constraint) |
| Storage | ChromaDB embedded mode |

## Development

### Run Tests

```bash
pip install -r requirements.txt
python scripts/test_e2e.py
```

### Add a New Collector

1. Create `src/collectors/new_source.py`
2. Inherit from `BaseCollector`
3. Implement `_fetch()` and `_parse()` methods
4. Register in `main.py`

```python
from src.collectors.base import BaseCollector, CollectedItem, SourceType

class NewSourceCollector(BaseCollector[RawType]):
    def __init__(self, config=None):
        super().__init__(SourceType.NEW_SOURCE, config)

    def _fetch(self) -> list[RawType]:
        # Fetch raw data from source
        pass

    def _parse(self, raw: RawType) -> CollectedItem | None:
        # Convert to CollectedItem
        pass
```

## Roadmap

### Phase 2 (Weeks 3-4)
- [ ] Podcasts collector with transcription (faster-whisper)
- [ ] Package tracking (PyPI/npm growth anomalies)
- [ ] Jobs collector (HN Who's Hiring)
- [ ] Weekly synthesis + competitive mapper

### Phase 3 (Month 2)
- [ ] Engineering blogs collector (postmortems)
- [ ] ArXiv papers with improved filters
- [ ] YouTube transcription
- [ ] Conference programs tracking

### Phase 4 (Month 3)
- [ ] Threshold calibration
- [ ] Prompt optimization
- [ ] Performance tuning

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python scripts/test_e2e.py`
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built for the [Claude Code](https://claude.ai/code) ecosystem
- Powered by [Anthropic](https://www.anthropic.com) Claude API
- Vector search by [ChromaDB](https://www.trychroma.com)
- Notifications via [ntfy.sh](https://ntfy.sh)

---

*AI Architect v2 - Stay ahead of the AI development curve.*
