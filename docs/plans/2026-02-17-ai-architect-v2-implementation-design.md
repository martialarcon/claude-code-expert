# AI Architect v2 - Implementation Design

**Date:** 2026-02-17
**Status:** Approved
**Approach:** Sequential phases (end-to-end v2 implementation)

---

## 1. Architecture Overview

The v2 architecture uses Claude Code subagents for LLM-intensive tasks while keeping Python for deterministic orchestration:

```
Python Orchestrator (main.py)
    │
    ├── Collectors (15 sources) → CollectedItem → ChromaDB
    │
    └── Processors (4 Claude Code subagents):
        ├── @agent-ranker: Batch scoring (10 items/batch)
        ├── @agent-analyzer: Individual deep analysis
        ├── @agent-synthesizer: Daily/weekly/monthly synthesis
        └── @agent-competitive: Weekly competitive matrix
```

**Key principle:** Subagents handle judgment (scoring, analysis, synthesis). Python handles determinism (collection, storage, orchestration).

**Hardware constraint:** Sequential execution only on Jetson Orin Nano (8GB RAM). No parallel agent calls.

---

## 2. Subagent Architecture

### 2.1 @agent-ranker

**Purpose:** Score items in batches of 10 for signal depth, impact, and practical evidence.

**Input:** JSON array of 10 CollectedItem summaries
**Output:** JSON array with `signal_score`, `impact_dimensions`, `impact_level`, `maturity_level` per item

**Location:** `.claude/agents/ranker.md`

### 2.2 @agent-analyzer

**Purpose:** Deep analysis of individual high-signal items.

**Input:** Single ProcessedItem with full content
**Output:** AnalyzedItem with `summary`, `key_insights`, `actionable_takeaways`, `related_topics`, `confidence`

**Location:** `.claude/agents/analyzer.md`

### 2.3 @agent-synthesizer

**Purpose:** Strategic synthesis across multiple time horizons.

**Modes:**
- Daily: Digest of day's items
- Weekly: Pattern detection, trend emergence
- Monthly: Strategic overview, competitive shifts

**Location:** `.claude/agents/synthesizer.md`

### 2.4 @agent-competitive

**Purpose:** Weekly competitive landscape mapping.

**Output:** CompetitiveMatrix with tool comparisons, feature gaps, adoption trends

**Location:** `.claude/agents/competitive.md`

---

## 3. Collector Additions

### Phase 1 Collectors (existing, enhance):
- `docs.py` - Official documentation diff detection
- `github_repos.py` - Consolidated repos (>100 stars)
- `github_emerging.py` - Emerging repos (<100 stars, growth tracking)
- `github_signals.py` - Issues/PRs/Discussions from critical repos
- `blogs.py` - RSS feeds (Simon Willison, Anthropic)
- `stackoverflow.py` - Questions with relevant tags

### Phase 2 Collectors (new):
- `podcasts.py` - RSS + faster-whisper transcription
- `packages.py` - PyPI/npm growth tracking
- `reddit.py` - Revised filtering (high comment/vote ratio)
- `hackernews.py` - Revised filtering (Ask HN, Show HN)

### Phase 3 Collectors (new):
- `jobs.py` - HN Who's Hiring scraping
- `conferences.py` - Conference program/CFP monitoring
- `youtube.py` - YouTube Data API + transcript-api
- `engineering_blogs.py` - Postmortems and architecture posts
- `arxiv.py` - Revised filtering (no citation threshold)

---

## 4. Schema Updates

### 4.1 SourceType Enum (expand)

```python
class SourceType(str, Enum):
    # Existing
    DOCS_OFFICIAL = "docs_official"
    GITHUB_ISSUES = "github_issues"
    GITHUB_PRS = "github_prs"
    GITHUB_DISCUSSIONS = "github_discussions"
    GITHUB_REPO_EMERGING = "github_repo_emerging"
    GITHUB_REPO_CONSOLIDATED = "github_repo_consolidated"
    BLOG = "blog"
    STACKOVERFLOW = "stackoverflow"
    # New
    PODCAST = "podcast"
    PYPI = "pypi"
    NPM = "npm"
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    ENGINEERING_BLOG = "engineering_blog"
    NEWSLETTER = "newsletter"
    ARXIV = "arxiv"
    YOUTUBE = "youtube"
    JOB_POSTING = "job_posting"
    CONFERENCE = "conference"
```

### 4.2 CollectedItem (enhance metadata)

```python
class CollectedItem(BaseModel):
    id: str  # SHA256(source_type + url)
    title: str
    url: str
    source_type: SourceType
    source_name: str
    published_at: datetime
    collected_at: datetime
    content: str  # Truncated to 15,000 tokens
    content_truncated: bool = False
    metadata: dict  # Source-specific fields (stars, comments, score, etc.)
```

### 4.3 ProcessedItem (full schema)

```python
class ImpactDimension(str, Enum):
    API = "api"
    INFRASTRUCTURE = "infrastructure"
    ORCHESTRATION = "orchestration"
    SECURITY = "security"
    PERFORMANCE = "performance"
    EVALUATION = "evaluation"
    TOOLING = "tooling"
    GOVERNANCE = "governance"
    BENCHMARK = "benchmark"
    DEVELOPER_EXPERIENCE = "developer_experience"

class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MaturityLevel(str, Enum):
    EXPERIMENTAL = "experimental"
    EMERGING = "emerging"
    PRODUCTION_VIABLE = "production_viable"
    CONSOLIDATED = "consolidated"
    DECLINING = "declining"

class ProcessedItem(BaseModel):
    collected_item: CollectedItem
    signal_score: int  # 1-10
    novelty_score: float  # 0.0-1.0
    impact_dimensions: list[ImpactDimension]
    impact_level: ImpactLevel
    maturity_level: MaturityLevel
    processing_metadata: dict = {}
    discarded: bool = False
    discard_reason: str | None = None
```

### 4.4 AnalyzedItem (new)

```python
class AnalyzedItem(BaseModel):
    processed_item: ProcessedItem
    summary: str  # 2-3 sentences
    key_insights: list[str]  # 3-5 insights
    actionable_takeaways: list[str]  # 0-3 actions
    related_topics: list[str]
    confidence: float  # 0.0-1.0
    analyzed_at: datetime
```

### 4.5 Synthesis Types (new)

```python
class DailySynthesis(BaseModel):
    date: date
    items_processed: int
    items_discarded: int
    top_items: list[str]  # Top 5 item IDs
    themes: list[str]  # 3-5 emerging themes
    summary: str
    created_at: datetime

class WeeklySynthesis(BaseModel):
    week_start: date
    week_end: date
    items_processed: int
    patterns_detected: list[str]
    emerging_trends: list[str]
    declining_trends: list[str]
    strategic_summary: str
    created_at: datetime

class MonthlySynthesis(BaseModel):
    month: str  # "2026-02"
    items_processed: int
    major_shifts: list[str]
    competitive_changes: list[str]
    strategic_recommendations: list[str]
    created_at: datetime
```

### 4.6 CompetitiveMatrix (new)

```python
class ToolComparison(BaseModel):
    tool_name: str
    vendor: str
    features: dict[str, bool]  # feature_name -> supported
    model: str
    extensibility: str  # "mcp" | "plugins" | "closed"
    pricing_tier: str
    limitations: list[str]

class CompetitiveMatrix(BaseModel):
    week: str  # "2026-W07"
    tools: list[ToolComparison]
    feature_gaps: list[str]
    adoption_trends: dict[str, str]  # tool -> "rising" | "stable" | "declining"
    created_at: datetime
```

---

## 5. Output Formats

### Directory Structure

```
output/
├── daily/
│   └── 2026-02-17.md
├── weekly/
│   └── 2026-W07.md
├── monthly/
│   └── 2026-02.md
├── competitive/
│   └── 2026-W07.md
├── topics/
│   └── mcp-servers.md
├── master.md
└── index.md
```

### Markdown Templates

Each output type follows structured templates defined in `src/storage/markdown_gen.py`.

---

## 6. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

1. Create 4 subagent definitions in `.claude/agents/`
2. Update Pydantic schemas in `src/models/`
3. Refactor existing processors to invoke subagents
4. Add Phase 2 collectors (podcasts, packages, reddit, hackernews)
5. Test end-to-end pipeline

### Phase 2: Intelligence Layer (Weeks 3-4)

1. Add Phase 3 collectors (jobs, conferences, youtube, engineering_blogs, arxiv)
2. Implement weekly synthesis mode
3. Implement monthly synthesis mode
4. Create competitive mapper
5. Test all synthesis modes

### Phase 3: Advanced Sources (Weeks 5-6)

1. Add podcast transcription (faster-whisper)
2. Add YouTube transcription
3. Implement growth tracking for packages
4. Add pattern detection for StackOverflow

### Phase 4: Calibration (Ongoing)

1. Tune signal_score thresholds based on data
2. Calibrate novelty_score distances
3. Optimize batch sizes
4. Performance profiling on Jetson

---

## 7. Hardware Considerations

### Memory Constraints (8GB RAM)

- Sequential execution: No parallel Claude CLI calls
- Podcast transcription runs as pre-process (Fase 0)
- ChromaDB in embedded mode (not separate container)
- Release memory between phases

### Execution Order

1. Fase 0: Podcast transcription (if new episodes) → release whisper
2. Fase 1: Collection from all sources → store items to disk
3. Fase 2: Batch processing → ChromaDB + subagents sequential
4. Fase 3: Synthesis and output generation
5. Fase 4: Notification

---

## 8. Configuration Updates

### config.yaml Additions

```yaml
# New collectors
collectors:
  podcasts:
    enabled: true
    feeds:
      - name: "Latent Space"
        url: "https://www.latent.space/podcast.rss"
    transcript_dir: "data/transcripts"

  packages:
    enabled: true
    pypi_packages:
      - "anthropic"
      - "mcp"
    npm_packages:
      - "@anthropic-ai/sdk"
    history_dir: "data/packages"

  reddit:
    enabled: true
    subreddits:
      - "LocalLLaMA"
      - "ClaudeAI"
    min_comments: 5

  hackernews:
    enabled: true
    min_points: 30  # Lowered from 50

# Synthesis modes
synthesis:
  daily:
    enabled: true
    time: "23:00"
  weekly:
    enabled: true
    day: "sunday"
  monthly:
    enabled: true
    day: 1

# Competitive mapping
competitive:
  enabled: true
  tools:
    - "claude-code"
    - "cursor"
    - "windsurf"
    - "cline"
    - "aider"
  frequency: "weekly"
```

---

## 9. Success Criteria

- [ ] All 4 subagents operational and invoked by orchestrator
- [ ] 15 collectors functional (6 existing + 9 new)
- [ ] Daily synthesis producing markdown output
- [ ] Weekly synthesis generating pattern reports
- [ ] Monthly synthesis generating strategic overviews
- [ ] Competitive matrix updating weekly
- [ ] Memory usage staying under 6GB during execution
- [ ] End-to-end pipeline completing in <30 minutes daily
