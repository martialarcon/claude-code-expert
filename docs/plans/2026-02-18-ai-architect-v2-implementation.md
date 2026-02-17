# AI Architect v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement AI Architect v2 with Claude Code subagents for ranking, analysis, synthesis, and competitive mapping.

**Architecture:** Python orchestrator invokes 4 Claude Code subagents for LLM-intensive tasks. Collectors gather data from 15 sources. ChromaDB stores vectors. Sequential execution on Jetson Orin Nano (8GB RAM).

**Tech Stack:** Python 3.11, Pydantic, ChromaDB, Anthropic SDK, feedparser, httpx

---

## Phase 1: Subagent Foundation

### Task 1: Create @agent-ranker Subagent

**Files:**
- Create: `.claude/agents/ranker.md`

**Step 1: Write the subagent definition**

```markdown
# @agent-ranker

Batch signal ranker for AI Architect v2.

## Purpose

Score collected items by signal strength in batches of 10. Assigns signal_score (1-10), impact dimension, and maturity level to each item.

## Input Format

JSON array of items with truncated content:

```json
[
  {
    "index": 0,
    "title": "Item title",
    "source_type": "github_signals",
    "content_preview": "First 1000 chars of content..."
  }
]
```

## Output Format

JSON array with scores:

```json
[
  {
    "index": 0,
    "signal_score": 7,
    "impact": "tooling",
    "maturity": "growing",
    "reasoning": "Brief explanation"
  }
]
```

## Scoring Criteria

### signal_score (1-10)

- **1-3 (Noise):** Generic content, opinions without evidence, basic tutorials, marketing
- **4-5 (Low signal):** Useful but not urgent, standard updates
- **6-7 (Medium signal):** Technical with applicable insights
- **8-9 (High signal):** Documented architectural decisions, production problems, benchmarks
- **10 (Critical):** Paradigm shift, breaking change, vulnerability, new fundamental capability

### impact (choose one)

- `tooling`: Development tools and workflows
- `architecture`: System design patterns
- `research`: Academic/industry research
- `production`: Production deployment concerns
- `ecosystem`: Library/framework ecosystem

### maturity (choose one)

- `experimental`: Proof of concept, research stage
- `early`: Early adopters, limited production
- `growing`: Growing adoption, best practices emerging
- `stable`: Widely adopted, stable APIs
- `legacy`: Declining, being replaced

## Execution

Always respond with valid JSON array. No markdown code blocks. No explanations outside JSON.
```

**Step 2: Create the file**

```bash
mkdir -p .claude/agents
```

Run: `cat > .claude/agents/ranker.md << 'EOF'
# @agent-ranker

Batch signal ranker for AI Architect v2.

## Purpose

Score collected items by signal strength in batches of 10. Assigns signal_score (1-10), impact dimension, and maturity level to each item.

## Input Format

JSON array of items with truncated content:

```json
[
  {
    "index": 0,
    "title": "Item title",
    "source_type": "github_signals",
    "content_preview": "First 1000 chars of content..."
  }
]
```

## Output Format

JSON array with scores:

```json
[
  {
    "index": 0,
    "signal_score": 7,
    "impact": "tooling",
    "maturity": "growing",
    "reasoning": "Brief explanation"
  }
]
```

## Scoring Criteria

### signal_score (1-10)

- **1-3 (Noise):** Generic content, opinions without evidence, basic tutorials, marketing
- **4-5 (Low signal):** Useful but not urgent, standard updates
- **6-7 (Medium signal):** Technical with applicable insights
- **8-9 (High signal):** Documented architectural decisions, production problems, benchmarks
- **10 (Critical):** Paradigm shift, breaking change, vulnerability, new fundamental capability

### impact (choose one)

- `tooling`: Development tools and workflows
- `architecture`: System design patterns
- `research`: Academic/industry research
- `production`: Production deployment concerns
- `ecosystem`: Library/framework ecosystem

### maturity (choose one)

- `experimental`: Proof of concept, research stage
- `early`: Early adopters, limited production
- `growing`: Growing adoption, best practices emerging
- `stable`: Widely adopted, stable APIs
- `legacy`: Declining, being replaced

## Execution

Always respond with valid JSON array. No markdown code blocks. No explanations outside JSON.
EOF
```

**Step 3: Verify file created**

Run: `cat .claude/agents/ranker.md | head -20`
Expected: First 20 lines of the ranker agent definition

**Step 4: Commit**

```bash
git add .claude/agents/ranker.md
git commit -m "feat: add @agent-ranker subagent definition"
```

---

### Task 2: Create @agent-analyzer Subagent

**Files:**
- Create: `.claude/agents/analyzer.md`

**Step 1: Write the subagent definition**

Run: `cat > .claude/agents/analyzer.md << 'EOF'
# @agent-analyzer

Deep analyzer for individual high-signal items.

## Purpose

Perform comprehensive analysis of a single item that passed signal ranking. Extract insights, assess relevance to Claude ecosystem, and determine actionability.

## Input Format

Single item JSON:

```json
{
  "id": "github_signals_abc123",
  "title": "Item title",
  "source_type": "github_signals",
  "source_url": "https://github.com/...",
  "content": "Full item content (up to 4000 chars)...",
  "signal_score": 7,
  "impact": "tooling",
  "maturity": "growing"
}
```

## Output Format

JSON analysis:

```json
{
  "summary": "2-3 sentence summary of what this item is about",
  "key_insights": [
    "Insight 1 with specific detail",
    "Insight 2 with specific detail",
    "Insight 3 with specific detail"
  ],
  "technical_details": "Specific technical information worth noting (or null)",
  "relevance_to_claude": "How this relates to Claude/Anthropic ecosystem specifically",
  "actionability": "high|medium|low",
  "related_topics": ["topic1", "topic2"],
  "confidence": 0.0-1.0
}
```

## Analysis Guidelines

### summary
- 2-3 sentences maximum
- Focus on what changed, was discovered, or matters
- Avoid generic descriptions

### key_insights
- 3-5 specific, non-obvious observations
- Include concrete details (numbers, names, specific changes)
- Connect to practical implications

### actionability levels

- **high:** Can act on this immediately (specific tool, pattern, fix)
- **medium:** Useful context for future decisions
- **low:** Interesting but no clear action

### confidence

- **0.9+:** Strong evidence, official sources, multiple confirmations
- **0.7-0.9:** Good evidence, some inference needed
- **0.5-0.7:** Limited information, significant inference
- **<0.5:** Speculative, needs verification

## Execution

Always respond with valid JSON. No markdown code blocks.
EOF
```

**Step 2: Verify and commit**

```bash
cat .claude/agents/analyzer.md | head -10
git add .claude/agents/analyzer.md
git commit -m "feat: add @agent-analyzer subagent definition"
```

---

### Task 3: Create @agent-synthesizer Subagent

**Files:**
- Create: `.claude/agents/synthesizer.md`

**Step 1: Write the subagent definition**

Run: `cat > .claude/agents/synthesizer.md << 'EOF'
# @agent-synthesizer

Strategic synthesizer for daily, weekly, and monthly intelligence reports.

## Purpose

Synthesize multiple analyzed items into coherent intelligence reports. Detect patterns, trends, and strategic implications across the Claude/AI ecosystem.

## Modes

### Daily Mode

Input: Up to 50 analyzed items from today
Output: Daily digest with highlights and immediate relevance

### Weekly Mode

Input: Up to 100 analyzed items from the week
Output: Pattern detection, trend emergence, competitive moves

### Monthly Mode

Input: Up to 200 analyzed items from the month
Output: Strategic overview, ecosystem shifts, predictions

## Input Format

```json
{
  "mode": "daily|weekly|monthly",
  "period": "2026-02-18",
  "items": [
    {
      "title": "...",
      "source_type": "...",
      "summary": "...",
      "key_insights": [...],
      "signal_score": N
    }
  ]
}
```

## Output Format

### Daily Synthesis

```json
{
  "relevance_score": 1-10,
  "highlights": ["Top finding 1", "Top finding 2", "Top finding 3"],
  "patterns": ["Pattern detected", "Another pattern"],
  "recommendations": ["Actionable recommendation"],
  "key_changes": ["Change from previous days"],
  "summary": "2-3 paragraph strategic overview"
}
```

### Weekly Synthesis

```json
{
  "relevance_score": 1-10,
  "top_stories": [{"title": "...", "significance": "..."}],
  "trends": ["Major trend with implications"],
  "competitive_moves": ["Competitive development"],
  "emerging_technologies": ["Emerging tech to watch"],
  "recommendations": ["Strategic recommendation"],
  "summary": "Week overview with strategic insights"
}
```

### Monthly Synthesis

```json
{
  "relevance_score": 1-10,
  "major_developments": [{"title": "...", "impact": "...", "timeline": "..."}],
  "trend_analysis": "Analysis of major trends",
  "ecosystem_changes": ["Significant change"],
  "competitive_landscape": "How landscape has shifted",
  "predictions": ["Prediction for next month"],
  "recommendations": ["Strategic recommendation"],
  "summary": "Month strategic overview"
}
```

## Synthesis Guidelines

### relevance_score
- **1-3:** Slow day/week, nothing significant
- **4-6:** Normal activity, some useful items
- **7-8:** Significant developments, multiple high-signal items
- **9-10:** Major shift, breaking changes, critical vulnerabilities

### Pattern Detection
Look for:
- Same issue appearing across multiple sources
- Rapid growth of new tools/libraries
- Changes in official documentation
- Migration patterns between technologies
- Emergence of new terminology or concepts

### Recommendations
- Must be actionable
- Connect to specific items
- Include context for why it matters

## Execution

Always respond with valid JSON matching the requested mode. No markdown code blocks.
EOF
```

**Step 2: Verify and commit**

```bash
cat .claude/agents/synthesizer.md | head -10
git add .claude/agents/synthesizer.md
git commit -m "feat: add @agent-synthesizer subagent definition"
```

---

### Task 4: Create @agent-competitive Subagent

**Files:**
- Create: `.claude/agents/competitive.md`

**Step 1: Write the subagent definition**

Run: `cat > .claude/agents/competitive.md << 'EOF'
# @agent-competitive

Competitive intelligence mapper for the AI-assisted development ecosystem.

## Purpose

Generate weekly competitive landscape analysis comparing Claude Code with alternative tools. Track feature gaps, adoption trends, and strategic positioning.

## Tools Tracked

- **Claude Code** (Anthropic)
- **Cursor** (Anysphere)
- **Windsurf** (Codeium)
- **Cline** (Open source)
- **Aider** (Open source)
- **GitHub Copilot** (Microsoft)
- **Continue** (Open source)

## Input Format

```json
{
  "week": "2026-W07",
  "items": [
    {
      "title": "...",
      "source_type": "...",
      "summary": "...",
      "tool_mentioned": "cursor|windsurf|..."
    }
  ],
  "previous_matrix": {
    "tools": [...],
    "feature_gaps": [...]
  }
}
```

## Output Format

```json
{
  "week": "2026-W07",
  "tools": [
    {
      "name": "Claude Code",
      "vendor": "Anthropic",
      "features": {
        "mcp_support": true,
        "multi_file_edit": true,
        "context_aware": true,
        "custom_agents": true,
        "local_execution": false
      },
      "model": "claude-sonnet-4-20250514",
      "extensibility": "mcp",
      "pricing_tier": "usage-based",
      "limitations": ["Requires API key", "No offline mode"]
    }
  ],
  "feature_gaps": [
    "Claude Code lacks local execution capability that Aider provides",
    "Cursor has better IDE integration but limited extensibility"
  ],
  "adoption_trends": {
    "claude-code": "rising",
    "cursor": "stable",
    "aider": "rising"
  },
  "strategic_insights": [
    "MCP ecosystem growing rapidly - competitive moat for Claude Code",
    "Open source alternatives gaining traction for privacy-sensitive use cases"
  ]
}
```

## Competitive Analysis Guidelines

### Feature Comparison Categories

- `mcp_support`: Model Context Protocol extensibility
- `multi_file_edit`: Can edit multiple files in one session
- `context_aware`: Maintains context across conversation
- `custom_agents`: Supports custom agent definitions
- `local_execution`: Can run without cloud API
- `ide_integration`: Native IDE support
- `code_review`: Built-in code review capabilities
- `test_generation`: Automatic test generation

### Adoption Trend Detection

- **rising:** Increasing mentions, positive sentiment, growth metrics
- **stable:** Consistent mentions, no significant change
- **declining:** Decreasing mentions, negative sentiment, migration reports

### Strategic Insights

Focus on:
- New capabilities that differentiate tools
- User pain points being addressed
- Ecosystem lock-in factors
- Enterprise adoption signals

## Execution

Always respond with valid JSON. No markdown code blocks.
EOF
```

**Step 2: Verify and commit**

```bash
cat .claude/agents/competitive.md | head -10
git add .claude/agents/competitive.md
git commit -m "feat: add @agent-competitive subagent definition"
```

---

### Task 5: Create Subagent Invoker Module

**Files:**
- Create: `src/processors/subagent_invoker.py`
- Create: `tests/processors/test_subagent_invoker.py`

**Step 1: Write the failing test**

Run: `cat > tests/processors/test_subagent_invoker.py << 'EOF'
"""Tests for subagent invoker module."""

import json
import pytest
from src.processors.subagent_invoker import (
    SubagentInvoker,
    invoke_ranker,
    invoke_analyzer,
    invoke_synthesizer,
)


class TestSubagentInvoker:
    """Tests for SubagentInvoker class."""

    def test_invoker_initialization(self):
        """Test invoker initializes correctly."""
        invoker = SubagentInvoker(agent_name="ranker")
        assert invoker.agent_name == "ranker"
        assert invoker.agent_path.endswith("ranker.md")

    def test_prepare_ranker_input(self):
        """Test input preparation for ranker."""
        invoker = SubagentInvoker("ranker")
        items = [
            {"title": "Test", "source_type": "blog", "content": "Content here"}
        ]
        prepared = invoker._prepare_input(items)
        data = json.loads(prepared)
        assert len(data) == 1
        assert data[0]["title"] == "Test"
        assert "index" in data[0]

    def test_prepare_analyzer_input(self):
        """Test input preparation for analyzer."""
        invoker = SubagentInvoker("analyzer")
        item = {
            "id": "test_123",
            "title": "Test",
            "source_type": "blog",
            "content": "Content",
            "signal_score": 7,
        }
        prepared = invoker._prepare_input(item)
        data = json.loads(prepared)
        assert data["id"] == "test_123"
        assert data["signal_score"] == 7

    def test_parse_ranker_output(self):
        """Test parsing ranker JSON output."""
        invoker = SubagentInvoker("ranker")
        output = '[{"index": 0, "signal_score": 7, "impact": "tooling", "maturity": "growing"}]'
        parsed = invoker._parse_output(output)
        assert len(parsed) == 1
        assert parsed[0]["signal_score"] == 7

    def test_parse_output_with_markdown_blocks(self):
        """Test parsing output wrapped in markdown."""
        invoker = SubagentInvoker("ranker")
        output = '''```json
[{"index": 0, "signal_score": 7}]
```'''
        parsed = invoker._parse_output(output)
        assert len(parsed) == 1


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_invoke_ranker_function_exists(self):
        """Test invoke_ranker function is callable."""
        assert callable(invoke_ranker)

    def test_invoke_analyzer_function_exists(self):
        """Test invoke_analyzer function is callable."""
        assert callable(invoke_analyzer)

    def test_invoke_synthesizer_function_exists(self):
        """Test invoke_synthesizer function is callable."""
        assert callable(invoke_synthesizer)
EOF
```

**Step 2: Run test to verify it fails**

Run: `cd /home/martialarcon/developer/projects/claude-code-expert && python -m pytest tests/processors/test_subagent_invoker.py -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

**Step 3: Write minimal implementation**

Run: `cat > src/processors/subagent_invoker.py << 'EOF'
"""
AI Architect v2 - Subagent Invoker

Invokes Claude Code subagents for ranking, analysis, synthesis, and competitive mapping.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger

log = get_logger("processor.subagent_invoker")


class SubagentError(Exception):
    """Error during subagent invocation."""
    pass


class SubagentInvoker:
    """
    Invokes Claude Code subagents.

    Handles:
    - Input preparation (JSON formatting)
    - Subagent execution via Claude CLI
    - Output parsing (JSON extraction)
    """

    def __init__(self, agent_name: str, agents_dir: Path | None = None):
        """
        Initialize invoker.

        Args:
            agent_name: Name of the agent (ranker, analyzer, synthesizer, competitive)
            agents_dir: Directory containing agent definitions
        """
        self.agent_name = agent_name
        if agents_dir is None:
            # Default to .claude/agents relative to project root
            project_root = Path(__file__).parent.parent.parent
            agents_dir = project_root / ".claude" / "agents"
        self.agents_dir = agents_dir
        self.agent_path = str(agents_dir / f"{agent_name}.md")

    def invoke(self, input_data: Any, timeout: int = 120) -> Any:
        """
        Invoke the subagent with input data.

        Args:
            input_data: Data to pass to the agent (will be JSON serialized)
            timeout: Timeout in seconds

        Returns:
            Parsed JSON response from the agent
        """
        # Prepare input
        input_json = self._prepare_input(input_data)

        log.debug(
            "invoking_subagent",
            agent=self.agent_name,
            input_length=len(input_json),
        )

        try:
            # For now, return a structured response without actual CLI invocation
            # This allows testing the pipeline structure
            # Real implementation would use: claude --agent @agent-name
            result = self._mock_invoke(input_data)
            return result

        except Exception as e:
            log.error("subagent_error", agent=self.agent_name, error=str(e)[:200])
            raise SubagentError(f"Subagent {self.agent_name} failed: {e}") from e

    def _mock_invoke(self, input_data: Any) -> Any:
        """
        Mock invocation for testing.

        In production, this would call the Claude CLI with the agent.
        """
        if self.agent_name == "ranker":
            # Return default rankings
            items = input_data if isinstance(input_data, list) else [input_data]
            return [
                {
                    "index": i,
                    "signal_score": 5,
                    "impact": "ecosystem",
                    "maturity": "growing",
                    "reasoning": "Mock ranking"
                }
                for i in range(len(items))
            ]

        elif self.agent_name == "analyzer":
            return {
                "summary": "Mock analysis summary",
                "key_insights": ["Mock insight 1", "Mock insight 2"],
                "technical_details": None,
                "relevance_to_claude": "Mock relevance",
                "actionability": "medium",
                "related_topics": ["mock"],
                "confidence": 0.7
            }

        elif self.agent_name == "synthesizer":
            return {
                "relevance_score": 5,
                "highlights": ["Mock highlight"],
                "patterns": ["Mock pattern"],
                "recommendations": ["Mock recommendation"],
                "key_changes": [],
                "summary": "Mock synthesis"
            }

        elif self.agent_name == "competitive":
            return {
                "week": input_data.get("week", "2026-W00"),
                "tools": [],
                "feature_gaps": [],
                "adoption_trends": {},
                "strategic_insights": []
            }

        return {}

    def _prepare_input(self, data: Any) -> str:
        """
        Prepare input data for the subagent.

        Args:
            data: Input data (list for ranker, dict for others)

        Returns:
            JSON string
        """
        if isinstance(data, list):
            # Add index to each item for ranker
            prepared = [
                {**item, "index": i} if "index" not in item else item
                for i, item in enumerate(data)
            ]
        else:
            prepared = data

        return json.dumps(prepared, ensure_ascii=False, indent=2)

    def _parse_output(self, output: str) -> Any:
        """
        Parse subagent output.

        Handles:
        - Plain JSON
        - JSON wrapped in markdown code blocks
        - Multi-line responses with JSON embedded

        Args:
            output: Raw output from subagent

        Returns:
            Parsed JSON data
        """
        # Try direct JSON parse first
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', output)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON array or object in output
        for pattern in [r'\[[\s\S]*\]', r'\{[\s\S]*\}']:
            match = re.search(pattern, output)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    continue

        raise SubagentError(f"Could not parse JSON from output: {output[:200]}")


# Convenience functions
def invoke_ranker(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Invoke the ranker agent with a batch of items.

    Args:
        items: List of items to rank

    Returns:
        List of ranking results
    """
    invoker = SubagentInvoker("ranker")
    return invoker.invoke(items)


def invoke_analyzer(item: dict[str, Any]) -> dict[str, Any]:
    """
    Invoke the analyzer agent with a single item.

    Args:
        item: Item to analyze

    Returns:
        Analysis result
    """
    invoker = SubagentInvoker("analyzer")
    return invoker.invoke(item)


def invoke_synthesizer(data: dict[str, Any]) -> dict[str, Any]:
    """
    Invoke the synthesizer agent.

    Args:
        data: Synthesis input with mode and items

    Returns:
        Synthesis result
    """
    invoker = SubagentInvoker("synthesizer")
    return invoker.invoke(data)


def invoke_competitive(data: dict[str, Any]) -> dict[str, Any]:
    """
    Invoke the competitive mapper agent.

    Args:
        data: Competitive analysis input

    Returns:
        Competitive matrix
    """
    invoker = SubagentInvoker("competitive")
    return invoker.invoke(data)
EOF
```

**Step 4: Run test to verify it passes**

Run: `cd /home/martialarcon/developer/projects/claude-code-expert && python -m pytest tests/processors/test_subagent_invoker.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/processors/subagent_invoker.py tests/processors/test_subagent_invoker.py
git commit -m "feat: add subagent invoker module with mock support"
```

---

## Phase 2: New Collectors

### Task 6: Add Reddit Collector

**Files:**
- Create: `src/collectors/reddit.py`
- Create: `tests/collectors/test_reddit.py`

**Step 1: Write the failing test**

Run: `cat > tests/collectors/test_reddit.py << 'EOF'
"""Tests for Reddit collector."""

import pytest
from src.collectors.reddit import RedditCollector, collect_reddit
from src.collectors.base import SourceType


class TestRedditCollector:
    """Tests for RedditCollector."""

    def test_initialization(self):
        """Test collector initializes correctly."""
        collector = RedditCollector({"enabled": True})
        assert collector.source_type == SourceType.REDDIT
        assert collector.enabled is True

    def test_default_subreddits(self):
        """Test default subreddits are set."""
        collector = RedditCollector({})
        assert "LocalLLaMA" in collector.subreddits
        assert "ClaudeAI" in collector.subreddits

    def test_min_comments_filter(self):
        """Test minimum comments filter."""
        collector = RedditCollector({"min_comments": 5})
        assert collector.min_comments == 5

    def test_collect_returns_result(self):
        """Test collect returns CollectionResult."""
        collector = RedditCollector({"enabled": False})
        result = collector.collect()
        assert result.source_type == SourceType.REDDIT
        assert result.items == []


class TestConvenienceFunction:
    """Tests for convenience function."""

    def test_collect_reddit_exists(self):
        """Test collect_reddit function exists."""
        assert callable(collect_reddit)
EOF
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/collectors/test_reddit.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

Run: `cat > src/collectors/reddit.py << 'EOF'
"""
AI Architect v2 - Reddit Collector

Collects posts from relevant subreddits with focus on high discussion ratio.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import BaseCollector, CollectedItem, CollectionResult, SourceType


@dataclass
class RedditPost:
    """Parsed Reddit post."""
    id: str
    title: str
    url: str
    selftext: str
    subreddit: str
    author: str
    score: int
    num_comments: int
    created_utc: datetime
    permalink: str


class RedditCollector(BaseCollector[RedditPost]):
    """
    Collector for Reddit posts.

    Focuses on high comment-to-score ratio (real discussion vs viral content).
    """

    DEFAULT_SUBREDDITS = [
        "LocalLLaMA",
        "ClaudeAI",
        "programming",
        "MachineLearning",
    ]

    # AI keywords for filtering
    AI_KEYWORDS = {
        "claude", "anthropic", "llm", "gpt", "ai", "agent",
        "mcp", "prompt", "llama", "openai", "deepseek",
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize Reddit collector.

        Config options:
            subreddits: List of subreddit names
            min_comments: Minimum comments to include (default: 5)
            min_score: Minimum score (default: 10)
            max_items: Maximum items per run (default: 20)
        """
        super().__init__(SourceType.REDDIT, config)

        self.subreddits = self.config.get("subreddits", self.DEFAULT_SUBREDDITS)
        self.min_comments = self.config.get("min_comments", 5)
        self.min_score = self.config.get("min_score", 10)
        self.max_items = self.config.get("max_items", 20)
        self.timeout = self.config.get("timeout", 30)

    def _fetch(self) -> list[RedditPost]:
        """Fetch posts from configured subreddits."""
        all_posts = []

        for subreddit in self.subreddits:
            try:
                posts = self._fetch_subreddit(subreddit)
                all_posts.extend(posts)
            except Exception as e:
                self._log.warning(
                    "subreddit_fetch_failed",
                    subreddit=subreddit,
                    error=str(e)[:200],
                )

        return all_posts[:self.max_items]

    def _fetch_subreddit(self, subreddit: str) -> list[RedditPost]:
        """Fetch posts from a single subreddit."""
        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        headers = {"User-Agent": "AI-Architect-v2/1.0"}

        posts = []

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            for child in data.get("data", {}).get("children", []):
                post_data = child.get("data", {})

                # Filter by minimum score and comments
                if post_data.get("score", 0) < self.min_score:
                    continue
                if post_data.get("num_comments", 0) < self.min_comments:
                    continue

                # Check relevance
                title = post_data.get("title", "")
                selftext = post_data.get("selftext", "")
                if not self._is_relevant(f"{title} {selftext}"):
                    continue

                post = self._parse_post(post_data, subreddit)
                if post:
                    posts.append(post)

        except Exception as e:
            self._log.error("subreddit_error", subreddit=subreddit, error=str(e)[:200])

        return posts

    def _parse_post(self, data: dict, subreddit: str) -> RedditPost | None:
        """Parse Reddit API response into RedditPost."""
        try:
            created = datetime.fromtimestamp(
                data.get("created_utc", 0),
                tz=timezone.utc
            )

            return RedditPost(
                id=data.get("id", ""),
                title=data.get("title", ""),
                url=f"https://reddit.com{data.get('permalink', '')}",
                selftext=data.get("selftext", "")[:4000],  # Limit content
                subreddit=subreddit,
                author=data.get("author", "[unknown]"),
                score=data.get("score", 0),
                num_comments=data.get("num_comments", 0),
                created_utc=created,
                permalink=data.get("permalink", ""),
            )
        except Exception as e:
            self._log.warning("post_parse_error", error=str(e)[:100])
            return None

    def _is_relevant(self, text: str) -> bool:
        """Check if post is AI-related."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.AI_KEYWORDS)

    def _parse(self, raw_item: RedditPost) -> CollectedItem | None:
        """Convert RedditPost to CollectedItem."""
        content = f"**r/{raw_item.subreddit}** ({raw_item.score} points, {raw_item.num_comments} comments)\n\n{raw_item.selftext}"

        return CollectedItem(
            id=f"reddit_{raw_item.id}",
            source_type=SourceType.REDDIT,
            source_url=raw_item.url,
            title=raw_item.title,
            content=content,
            author=raw_item.author,
            published_at=raw_item.created_utc,
            metadata={
                "subreddit": raw_item.subreddit,
                "score": raw_item.score,
                "num_comments": raw_item.num_comments,
                "comment_score_ratio": raw_item.num_comments / max(1, raw_item.score),
            },
        )


def collect_reddit(config: dict[str, Any] | None = None) -> CollectionResult:
    """
    Convenience function to collect Reddit posts.

    Args:
        config: Collector configuration

    Returns:
        CollectionResult with collected items
    """
    collector = RedditCollector(config)
    return collector.collect()
EOF
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/collectors/test_reddit.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/collectors/reddit.py tests/collectors/test_reddit.py
git commit -m "feat: add Reddit collector with comment ratio filtering"
```

---

### Task 7: Add Hacker News Collector

**Files:**
- Create: `src/collectors/hackernews.py`
- Create: `tests/collectors/test_hackernews.py`

**Step 1: Write the failing test**

Run: `cat > tests/collectors/test_hackernews.py << 'EOF'
"""Tests for Hacker News collector."""

import pytest
from src.collectors.hackernews import HackerNewsCollector, collect_hackernews
from src.collectors.base import SourceType


class TestHackerNewsCollector:
    """Tests for HackerNewsCollector."""

    def test_initialization(self):
        """Test collector initializes correctly."""
        collector = HackerNewsCollector({"enabled": True})
        assert collector.source_type == SourceType.HACKERNEWS
        assert collector.enabled is True

    def test_min_points_default(self):
        """Test default minimum points."""
        collector = HackerNewsCollector({})
        assert collector.min_points == 30

    def test_collect_returns_result(self):
        """Test collect returns CollectionResult."""
        collector = HackerNewsCollector({"enabled": False})
        result = collector.collect()
        assert result.source_type == SourceType.HACKERNEWS


class TestConvenienceFunction:
    """Tests for convenience function."""

    def test_collect_hackernews_exists(self):
        """Test collect_hackernews function exists."""
        assert callable(collect_hackernews)
EOF
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/collectors/test_hackernews.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

Run: `cat > src/collectors/hackernews.py << 'EOF'
"""
AI Architect v2 - Hacker News Collector

Collects posts from Hacker News with revised filtering (lower threshold, special handling for Ask/Show HN).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import BaseCollector, CollectedItem, CollectionResult, SourceType


@dataclass
class HNItem:
    """Parsed Hacker News item."""
    id: int
    title: str
    url: str | None
    text: str | None
    by: str
    score: int
    descendants: int  # Comment count
    time: datetime
    type: str  # story, ask_hn, show_hn, etc.


class HackerNewsCollector(BaseCollector[HNItem]):
    """
    Collector for Hacker News.

    Revised filtering:
    - Lower score threshold (30 vs 50)
    - Special handling for Ask HN (no score filter)
    - Show HN with technical comments
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    AI_KEYWORDS = {
        "claude", "anthropic", "llm", "gpt", "ai", "agent",
        "mcp", "llama", "openai", "deepseek", "machine learning",
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize HN collector.

        Config options:
            min_points: Minimum points for stories (default: 30)
            min_comments: Minimum comments for Ask/Show HN (default: 3)
            max_items: Maximum items per run (default: 20)
        """
        super().__init__(SourceType.HACKERNEWS, config)

        self.min_points = self.config.get("min_points", 30)
        self.min_comments = self.config.get("min_comments", 3)
        self.max_items = self.config.get("max_items", 20)
        self.timeout = self.config.get("timeout", 30)

    def _fetch(self) -> list[HNItem]:
        """Fetch items from Hacker News."""
        items = []

        try:
            # Get top stories
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.BASE_URL}/topstories.json")
                response.raise_for_status()
                story_ids = response.json()[:100]  # Check top 100

                for story_id in story_ids[:50]:  # Process first 50
                    try:
                        item = self._fetch_item(story_id, client)
                        if item and self._should_include(item):
                            items.append(item)
                    except Exception as e:
                        self._log.debug("item_fetch_error", id=story_id, error=str(e)[:100])

                    if len(items) >= self.max_items:
                        break

        except Exception as e:
            self._log.error("hn_fetch_error", error=str(e)[:200])

        return items

    def _fetch_item(self, item_id: int, client: httpx.Client) -> HNItem | None:
        """Fetch a single HN item."""
        response = client.get(f"{self.BASE_URL}/item/{item_id}.json")
        response.raise_for_status()
        data = response.json()

        if not data:
            return None

        # Determine type
        title = data.get("title", "")
        if title.lower().startswith("ask hn:"):
            item_type = "ask_hn"
        elif title.lower().startswith("show hn:"):
            item_type = "show_hn"
        else:
            item_type = data.get("type", "story")

        return HNItem(
            id=data.get("id", 0),
            url=data.get("url"),
            text=data.get("text", ""),
            title=title,
            by=data.get("by", "[unknown]"),
            score=data.get("score", 0),
            descendants=data.get("descendants", 0),
            time=datetime.fromtimestamp(data.get("time", 0), tz=timezone.utc),
            type=item_type,
        )

    def _should_include(self, item: HNItem) -> bool:
        """Determine if item should be included."""
        # Check relevance first
        if not self._is_relevant(item.title):
            return False

        # Ask HN: include if relevant (no score filter)
        if item.type == "ask_hn":
            return True

        # Show HN: include if has comments
        if item.type == "show_hn":
            return item.descendants >= self.min_comments

        # Regular stories: check score
        return item.score >= self.min_points

    def _is_relevant(self, text: str) -> bool:
        """Check if item is AI-related."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.AI_KEYWORDS)

    def _parse(self, raw_item: HNItem) -> CollectedItem | None:
        """Convert HNItem to CollectedItem."""
        hn_url = f"https://news.ycombinator.com/item?id={raw_item.id}"
        display_url = raw_item.url or hn_url

        content = f"**{raw_item.type}** ({raw_item.score} points, {raw_item.descendants} comments)\n\n"
        if raw_item.text:
            content += raw_item.text[:3000]

        return CollectedItem(
            id=f"hn_{raw_item.id}",
            source_type=SourceType.HACKERNEWS,
            source_url=display_url,
            title=raw_item.title,
            content=content,
            author=raw_item.by,
            published_at=raw_item.time,
            metadata={
                "hn_id": raw_item.id,
                "type": raw_item.type,
                "score": raw_item.score,
                "num_comments": raw_item.descendants,
            },
        )


def collect_hackernews(config: dict[str, Any] | None = None) -> CollectionResult:
    """
    Convenience function to collect Hacker News posts.

    Args:
        config: Collector configuration

    Returns:
        CollectionResult with collected items
    """
    collector = HackerNewsCollector(config)
    return collector.collect()
EOF
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/collectors/test_hackernews.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/collectors/hackernews.py tests/collectors/test_hackernews.py
git commit -m "feat: add Hacker News collector with revised filtering"
```

---

### Task 8: Update main.py to Include New Collectors

**Files:**
- Modify: `main.py:161-168`

**Step 1: Update imports**

In `main.py`, add imports for new collectors after line 26:

```python
from src.collectors.hackernews import collect_hackernews
from src.collectors.reddit import collect_reddit
```

**Step 2: Add collectors to the collectors list**

In `_collect()` method, update the collectors list (around line 161):

```python
collectors = [
    ("docs", collect_docs),
    ("github_signals", collect_github_signals),
    ("github_emerging", collect_github_emerging),
    ("github_repos", collect_github_repos),
    ("blogs", collect_blogs),
    ("stackoverflow", collect_stackoverflow),
    ("reddit", collect_reddit),
    ("hackernews", collect_hackernews),
]
```

**Step 3: Verify the change**

Run: `python -c "from main import AIArchitect; print('OK')"`
Expected: "OK"

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: integrate Reddit and HackerNews collectors into pipeline"
```

---

## Phase 3: Update Config

### Task 9: Update config.yaml with New Collector Settings

**Files:**
- Modify: `config.yaml`

**Step 1: Add Reddit configuration**

Add after the stackoverflow section (around line 72):

```yaml
  reddit:
    enabled: true
    subreddits:
      - "LocalLLaMA"
      - "ClaudeAI"
    min_comments: 5
    max_items: 20

  hackernews:
    enabled: true
    min_points: 30
    min_comments: 3
    max_items: 20
```

**Step 2: Verify config is valid**

Run: `python -c "from src.utils.config import get_config; c = get_config(); print('OK')"`
Expected: "OK"

**Step 3: Commit**

```bash
git add config.yaml
git commit -m "feat: add Reddit and HackerNews configuration"
```

---

## Phase 4: Integration Testing

### Task 10: Run End-to-End Test

**Step 1: Run the full pipeline in daily mode**

Run: `python main.py --mode daily --verbose 2>&1 | head -50`
Expected: Pipeline starts, collectors run, processing begins

**Step 2: Check output files**

Run: `ls -la output/daily/ | head -5`
Expected: At least one daily digest file exists

**Step 3: Verify no errors in logs**

Run: `python main.py --mode daily 2>&1 | grep -i error | head -10`
Expected: No critical errors

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete AI Architect v2 Phase 1 - subagents and new collectors"
```

---

## Summary

After completing this plan:

- [x] 4 subagent definitions created
- [x] Subagent invoker module with mock support
- [x] Reddit collector with comment ratio filtering
- [x] Hacker News collector with revised thresholds
- [x] main.py updated with new collectors
- [x] config.yaml updated
- [x] End-to-end pipeline tested

**Next phases** (to be planned separately):
- Phase 2: Podcasts, PyPI/npm, Jobs collectors
- Phase 3: YouTube, Engineering Blogs, ArXiv, Conferences
- Phase 4: Competitive Mapper implementation
