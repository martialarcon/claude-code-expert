"""
AI Architect v2 - Subagent Invoker

Module to invoke Claude Code subagents for ranking, analysis,
synthesis, and competitive mapping.

In production, this would invoke Claude CLI with --agent flag.
For testing, provides mock responses.
"""

import copy
import json
import logging
import re
from pathlib import Path
from typing import Any

# Use standard logging as fallback for environments without structlog
try:
    from ..utils.logger import get_logger
    log = get_logger("processor.subagent_invoker")
except ImportError:
    log = logging.getLogger("processor.subagent_invoker")


class SubagentError(Exception):
    """Exception raised when subagent invocation fails."""

    def __init__(self, message: str, agent_name: str | None = None):
        super().__init__(message)
        self.agent_name = agent_name


class SubagentInvoker:
    """
    Invokes Claude Code subagents for specialized processing tasks.

    Supports:
    - agent-ranker: Signal ranking with impact/maturity classification
    - agent-analyzer: Deep content analysis
    - agent-synthesizer: Daily/weekly/monthly synthesis
    - agent-competitive: Competitive landscape mapping
    """

    def __init__(self, agent_name: str, agents_dir: Path | None = None):
        """
        Initialize subagent invoker.

        Args:
            agent_name: Name of the agent (e.g., "agent-ranker")
            agents_dir: Directory containing agent definitions (default: .claude/agents)
        """
        self.agent_name = agent_name
        if agents_dir is None:
            # Default to .claude/agents relative to project root
            project_root = Path(__file__).parent.parent.parent
            agents_dir = project_root / ".claude" / "agents"
        self.agents_dir = agents_dir

    def invoke(self, input_data: Any, timeout: int = 120) -> Any:  # noqa: ARG002 - timeout for future production use
        """
        Invoke the subagent with input data.

        In production, this would call Claude CLI with --agent flag.
        For testing, returns mock responses.

        Args:
            input_data: Data to process (list or dict)
            timeout: Timeout in seconds for the invocation

        Returns:
            Processed result from the agent

        Raises:
            SubagentError: If invocation fails or output cannot be parsed
        """
        # For now, use mock invocation for testing
        # In production, this would be:
        # input_str = self._prepare_input(input_data)
        # result = subprocess.run(
        #     ["claude", "-p", input_str, "--agent", self.agent_name],
        #     capture_output=True, text=True, timeout=timeout
        # )
        # return self._parse_output(result.stdout)
        return self._mock_invoke(input_data)

    def _prepare_input(self, data: Any) -> str:
        """
        Prepare input data for the agent.

        Serializes to JSON, adding index field for lists when using ranker.

        Args:
            data: Input data (list or dict)

        Returns:
            JSON string ready for agent input
        """
        if isinstance(data, list):
            # Only add index for ranker agent
            if self.agent_name == "agent-ranker":
                # Create a copy to avoid modifying original
                data_copy = []
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        item_copy = copy.deepcopy(item)
                        # Add index for ranker to track items
                        if "index" not in item_copy:
                            item_copy["index"] = i
                        data_copy.append(item_copy)
                    else:
                        data_copy.append(item)
                return json.dumps(data_copy, ensure_ascii=False, indent=2)

            # For non-ranker agents, serialize as-is
            return json.dumps(data, ensure_ascii=False, indent=2)

        return json.dumps(data, ensure_ascii=False, indent=2)

    def _parse_output(self, output: str) -> Any:
        """
        Parse agent output to extract JSON result.

        Handles:
        - Plain JSON
        - JSON in markdown code blocks
        - JSON embedded in text

        Args:
            output: Raw output string from agent

        Returns:
            Parsed JSON data (dict or list)

        Raises:
            SubagentError: If output cannot be parsed as JSON
        """
        output = output.strip()

        # Try direct JSON parse first
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code block
        code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        match = re.search(code_block_pattern, output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find JSON embedded in text using a more robust approach
        # First try to find arrays (they start with '[' and end with ']')
        # Use a simple bracket-matching approach
        try:
            # Find potential JSON array start
            start_idx = output.find('[')
            if start_idx != -1:
                bracket_count = 0
                end_idx = start_idx
                for i, char in enumerate(output[start_idx:], start_idx):
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i
                            break
                if end_idx > start_idx:
                    json_str = output[start_idx:end_idx + 1]
                    return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        try:
            # Find potential JSON object start
            start_idx = output.find('{')
            if start_idx != -1:
                brace_count = 0
                end_idx = start_idx
                in_string = False
                escape_next = False
                for i, char in enumerate(output[start_idx:], start_idx):
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\' and in_string:
                        escape_next = True
                        continue
                    if char == '"' and not escape_next:
                        in_string = not in_string
                    elif not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i
                                break
                if end_idx > start_idx:
                    json_str = output[start_idx:end_idx + 1]
                    return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        raise SubagentError(
            f"Could not parse JSON from agent output",
            agent_name=self.agent_name
        )

    def _mock_invoke(self, input_data: Any) -> Any:
        """
        Generate mock response for testing.

        Returns reasonable default responses based on agent type.

        Args:
            input_data: Input data (used to determine response structure)

        Returns:
            Mock response appropriate for the agent type
        """
        if self.agent_name == "agent-ranker":
            return self._mock_ranker_response(input_data)
        elif self.agent_name == "agent-analyzer":
            return self._mock_analyzer_response(input_data)
        elif self.agent_name == "agent-synthesizer":
            return self._mock_synthesizer_response(input_data)
        elif self.agent_name == "agent-competitive":
            return self._mock_competitive_response(input_data)
        else:
            # Generic mock response
            return {"status": "mocked", "agent": self.agent_name}

    def _mock_ranker_response(self, items: list[dict]) -> list[dict]:
        """Generate mock ranking response."""
        if not isinstance(items, list):
            items = [items]

        result = []
        for i, _ in enumerate(items):
            result.append({
                "index": i,
                "signal_score": 5,
                "impact": "ecosystem",
                "maturity": "growing",
                "reasoning": f"Mock ranking for item {i}"
            })
        return result

    def _mock_analyzer_response(self, item: dict) -> dict:
        """Generate mock analysis response."""
        title = item.get("title", "Unknown") if isinstance(item, dict) else "Unknown"
        return {
            "summary": f"Mock analysis summary for: {title}",
            "key_insights": [
                "This is a mock insight for testing purposes",
                "Another mock insight demonstrating the expected structure"
            ],
            "implications": [
                "Mock architectural implication",
                "Mock production consideration"
            ],
            "actionability": "medium",
            "confidence": 0.7,
            "competitive_notes": "Mock competitive analysis notes"
        }

    def _mock_synthesizer_response(self, data: dict) -> dict:
        """Generate mock synthesis response."""
        mode = data.get("mode", "daily") if isinstance(data, dict) else "daily"
        return {
            "mode": mode,
            "relevance_score": 5,
            "highlights": [
                "Mock highlight 1 for the synthesis",
                "Mock highlight 2 for the synthesis"
            ],
            "patterns": [
                "Mock pattern detected in the data",
                "Another mock pattern"
            ],
            "recommendations": [
                "Mock recommendation 1",
                "Mock recommendation 2"
            ],
            "narrative": "Mock narrative for the synthesis period."
        }

    def _mock_competitive_response(self, data: dict) -> dict:
        """Generate mock competitive analysis response."""
        week = data.get("week", "2026-W07") if isinstance(data, dict) else "2026-W07"
        return {
            "week": week,
            "tools": [
                {"name": "Cursor", "changes": "Mock competitive change"},
                {"name": "GitHub Copilot", "changes": "Mock competitive change"}
            ],
            "feature_gaps": [
                "Mock feature gap 1",
                "Mock feature gap 2"
            ],
            "adoption_trends": [
                "Mock adoption trend 1",
                "Mock adoption trend 2"
            ],
            "strategic_insights": [
                "Mock strategic insight 1",
                "Mock strategic insight 2"
            ]
        }


# Convenience functions for common agent invocations

def invoke_ranker(items: list[dict]) -> list[dict]:
    """
    Invoke the ranker agent to score and classify items.

    Args:
        items: List of items to rank

    Returns:
        List of ranked items with signal_score, impact, maturity
    """
    invoker = SubagentInvoker("agent-ranker")
    return invoker.invoke(items)


def invoke_analyzer(item: dict) -> dict:
    """
    Invoke the analyzer agent for deep content analysis.

    Args:
        item: Item to analyze

    Returns:
        Analysis dict with summary, key_insights, actionability, confidence
    """
    invoker = SubagentInvoker("agent-analyzer")
    return invoker.invoke(item)


def invoke_synthesizer(data: dict) -> dict:
    """
    Invoke the synthesizer agent for period synthesis.

    Args:
        data: Synthesis data including mode (daily/weekly/monthly) and items

    Returns:
        Synthesis dict with relevance_score, highlights, patterns, recommendations
    """
    invoker = SubagentInvoker("agent-synthesizer")
    return invoker.invoke(data)


def invoke_competitive(data: dict) -> dict:
    """
    Invoke the competitive agent for competitive landscape analysis.

    Args:
        data: Competitive analysis data including week and items

    Returns:
        Competitive analysis dict with week, tools, feature_gaps, adoption_trends
    """
    invoker = SubagentInvoker("agent-competitive")
    return invoker.invoke(data)
