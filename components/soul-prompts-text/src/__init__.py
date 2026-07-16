"""
PRODAFLT Soul Prompts Text Component

Manages versioned soul prompts for all 7 PRODAFLT agents.
Provides file-based storage with optional database persistence.
"""

__version__ = "1.0.0"
__all__ = ["SoulPromptLoader", "get_prompt", "list_agents", "AGENTS"]

from .loader import SoulPromptLoader, get_prompt, list_agents, AGENTS
