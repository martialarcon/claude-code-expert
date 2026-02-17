"""
AI Architect v2 - Client Factory

Factory that creates LLM clients.
Currently uses ClaudeClient with Anthropic SDK (supports GLM proxy via ANTHROPIC_BASE_URL).
"""

from .claude_client import ClaudeClient, ClaudeModel
from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger("processor.client_factory")


def get_analysis_client() -> ClaudeClient:
    """
    Get LLM client configured for analysis tasks.

    Returns ClaudeClient configured with analysis model.
    """
    config = get_config()
    model_str = config.models.analysis or "glm-5"

    try:
        model = ClaudeModel(model_str)
    except ValueError:
        # Default to GLM-5 for proxy setups
        model = ClaudeModel.GLM_5

    log.debug("creating_analysis_client", model=model.value)
    return ClaudeClient(model=model)


def get_synthesis_client() -> ClaudeClient:
    """
    Get LLM client configured for synthesis tasks.

    Returns ClaudeClient with longer timeout for synthesis operations.
    """
    config = get_config()
    model_str = config.models.synthesis or "glm-5"

    try:
        model = ClaudeModel(model_str)
    except ValueError:
        model = ClaudeModel.GLM_5

    log.debug("creating_synthesis_client", model=model.value)
    return ClaudeClient(model=model, timeout=300)
