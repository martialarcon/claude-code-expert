# Anthropic SDK Client Design

**Date:** 2026-02-17
**Status:** Approved
**Author:** Claude Code

## Overview

Replace the current Claude CLI subprocess client with the official Anthropic Python SDK, configured to use the GLM proxy (`api.z.ai`) as a compatible backend.

## Problem

- Current `claude_client.py` uses subprocess to call Claude CLI, which doesn't work in Docker
- `glm_client.py` uses ZhipuAI native API, which requires separate account/billing
- User has a GLM proxy that's 100% compatible with Anthropic API

## Solution

Use Anthropic Python SDK with custom `base_url` pointing to GLM proxy.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Architect                          │
├─────────────────────────────────────────────────────────┤
│  signal_ranker.py ─┐                                    │
│  analyzer.py ──────┼──► client_factory.py ──► ClaudeClient│
│  synthesizer.py ───┘           │              (SDK)      │
│                                 │                         │
│                                 ▼                         │
│                        ANTHROPIC_BASE_URL                 │
│                        https://api.z.ai/api/anthropic    │
└─────────────────────────────────────────────────────────┘
```

## Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `ANTHROPIC_API_KEY` | GLM token | Token from GLM proxy |
| `ANTHROPIC_BASE_URL` | `https://api.z.ai/api/anthropic` | GLM proxy endpoint |
| `API_TIMEOUT_MS` | `3000000` | 50 minutes timeout |

## Code Changes

### 1. requirements.txt
```diff
+ anthropic>=0.40.0
```

### 2. claude_client.py
- Remove `subprocess` imports
- Use `anthropic.Anthropic(base_url=os.environ.get("ANTHROPIC_BASE_URL"))`
- Keep interface: `complete()`, `complete_json()`
- Keep error classes: `ClaudeClientError`, `ClaudeTimeoutError`, `ClaudeAPIError`, `ClaudeParseError`

### 3. client_factory.py
- Simplify to single client selection
- Remove provider logic
- Return `ClaudeClient` instance

### 4. glm_client.py
- Delete file (no longer needed)

### 5. docker-compose.yml
```yaml
environment:
  - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
  - ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-https://api.z.ai/api/anthropic}
  - API_TIMEOUT_MS=${API_TIMEOUT_MS:-3000000}
```

### 6. config.yaml
```yaml
models:
  provider: "anthropic"
  analysis: "glm-5"
  synthesis: "glm-5"
```

## Files to Modify

| File | Action |
|------|--------|
| `requirements.txt` | Add anthropic SDK |
| `src/processors/claude_client.py` | Rewrite with SDK |
| `src/processors/client_factory.py` | Simplify |
| `src/processors/glm_client.py` | Delete |
| `docker-compose.yml` | Add env vars |
| `config.yaml` | Update provider |
| `.env.example` | Document new vars |

## Testing

1. Unit tests for ClaudeClient with mocked Anthropic SDK
2. Integration test: call GLM proxy with test prompt
3. E2E test: run daily cycle and verify output

## Risks

- GLM proxy availability: Mitigated by retry logic
- API compatibility: Already confirmed 100% compatible

## Rollback

If issues arise:
1. Revert to previous `claude_client.py` (CLI-based)
2. Restore `glm_client.py`
3. Set `provider: "glm"` in config.yaml
