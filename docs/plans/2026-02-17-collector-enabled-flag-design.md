# Design: Respect Collector Enabled Flag

**Date:** 2026-02-17
**Status:** Approved

## Problem

`config.yaml` has `enabled: true/false` per collector, but `main.py` ignores it and always executes all collectors. This causes GitHub collectors to fail when no `GITHUB_TOKEN` is available.

## Solution

Add enabled check in `main.py:_collect()` before calling each collector.

## Implementation

1. In `main.py:_collect()`, check `collector_config.enabled` before calling collector
2. Skip disabled collectors with a log message
3. Update `config.yaml` to disable GitHub collectors by default (no token)

## Code Change

```python
for name, collector_func in collectors:
    # Check if collector is enabled
    collector_config = getattr(self.config.collectors, name, None)
    if collector_config and not getattr(collector_config, "enabled", True):
        log.info("collector_disabled", source=name)
        continue

    try:
        result = collector_func(self.config.collectors.model_dump())
        ...
```

## User Impact

Users can now disable collectors by setting `enabled: false` in `config.yaml`.
