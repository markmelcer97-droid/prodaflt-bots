"""
Basic tests for the soul prompt loader.
Run with: pytest tests/test_loader.py
"""

import pytest
from pathlib import Path

from src.loader import SoulPromptLoader, get_prompt, list_agents, AGENTS


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class TestSoulPromptLoader:
    def test_load_router(self):
        loader = SoulPromptLoader(PROMPTS_DIR)
        prompt = loader.load("router")
        assert prompt.agent_key == "router"
        assert prompt.agent_name == "Router"
        assert "Router PRODAFLT" in prompt.content
        assert prompt.version == "1.0.0"

    def test_load_all(self):
        loader = SoulPromptLoader(PROMPTS_DIR)
        all_prompts = loader.load_all()
        assert len(all_prompts) == 7
        assert set(all_prompts.keys()) == set(AGENTS.keys())

    def test_render_for_claw(self):
        loader = SoulPromptLoader(PROMPTS_DIR)
        rendered = loader.render_for_claw("data_analyst", extra_context="Test context")
        assert "PRODAFLT Agent: Data Analyst" in rendered
        assert "Test context" in rendered
        assert "Data Analyst PRODAFLT" in rendered

    def test_unknown_agent_raises(self):
        loader = SoulPromptLoader(PROMPTS_DIR)
        with pytest.raises(KeyError):
            loader.load("nonexistent")

    def test_list_agents(self):
        agents = list_agents()
        assert len(agents) == 7
        keys = {a["key"] for a in agents}
        assert "router" in keys
        assert "creative" in keys

    def test_get_prompt_singleton(self):
        prompt = get_prompt("tech_lead")
        assert prompt.agent_name == "Tech Lead"
        assert "Tech Lead PRODAFLT" in prompt.content
