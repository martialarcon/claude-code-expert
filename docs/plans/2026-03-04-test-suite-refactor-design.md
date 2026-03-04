# Test Suite Refactor + Comprehensive Coverage Design

**Date:** 2026-03-04
**Status:** Approved
**Approach:** Option B - Refactor + Comprehensive Suite

## Overview

Refactor test structure with shared fixtures and comprehensive coverage for all identified gaps from code review.

## Problem Statement

Code review identified 9 issues:
- **Critical (2):** E2E test failures, untested retry logic
- **Important (7):** Weak factory assertions, missing error path tests, untested JSON parsing edge cases

## Solution Architecture

### Directory Structure

```
tests/
├── conftest.py              # Shared fixtures (NEW)
├── fixtures/
│   └── claude_mocks.py      # ClaudeClient mock utilities (NEW)
├── processors/
│   ├── test_client_factory.py      # ENHANCED
│   ├── test_claude_client.py       # ENHANCED
│   └── test_subagent_invoker.py    # ENHANCED
└── utils/
    └── test_chroma_query.py        # ENHANCED

scripts/
└── test_e2e.py              # FIXED + REFACTORED
```

### Components

#### 1. conftest.py - Shared Fixtures

Global fixtures for all test files:

| Fixture | Purpose |
|---------|---------|
| `mock_env_api_key` | Sets ANTHROPIC_API_KEY in environment |
| `mock_claude_response` | Factory to create mock API responses |
| `mock_claude_client` | Fully mocked ClaudeClient instance |
| `reset_config` | Resets config singleton between tests |

#### 2. fixtures/claude_mocks.py - Mock Utilities

Reusable mock builders:

```python
def create_mock_response(text: str) -> MagicMock
def create_mock_error(error_class: type) -> MagicMock
def create_mock_client_with_response(response_text: str) -> ClaudeClient
```

#### 3. E2E Test Fixes

| Test | Issue | Fix |
|------|-------|-----|
| `test_config` | Silent error | Add try/except with full traceback |
| `test_markdown_generator` | `NoneType.__format__` | Validate synthesis.date before format |

#### 4. New Tests by Module

**test_client_factory.py:**
- `test_get_analysis_client_uses_config_model`
- `test_get_synthesis_client_has_300_timeout`
- `test_fallback_to_glm5_on_invalid_model`

**test_claude_client.py:**
- `test_retry_on_api_error`
- `test_parse_json_without_language_specifier`
- `test_analyze_with_expect_json`
- `test_claude_parse_error_on_invalid_json`

**test_chroma_query.py:**
- `test_query_chromadb_error_handling`
- `test_graceful_degradation_on_collection_failure`

**test_subagent_invoker.py:**
- `test_production_cli_command_construction`

## Implementation Notes

- Use pytest fixtures for DRY principle
- Mock at API boundary (Anthropic SDK), not internal methods
- Each test file can import from conftest.py automatically
- E2E tests remain independent (no fixture dependency)

## Success Criteria

- [ ] All 67 existing tests still pass
- [ ] 2 E2E test failures fixed
- [ ] ~15 new tests added
- [ ] Total test count: ~82
- [ ] No test interdependencies
- [ ] Clear test naming conventions maintained
