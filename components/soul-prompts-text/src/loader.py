"""
Soul Prompt Loader — file-based prompt management with DB sync.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------

AGENTS = {
    "router": {
        "name": "Router",
        "role": "Dispatcher",
        "file": "router_soul.md",
        "heartbeat": "daily 09:17",
    },
    "researcher": {
        "name": "Researcher",
        "role": "Content Researcher",
        "file": "researcher_soul.md",
        "heartbeat": "daily 10:00",
    },
    "compliance": {
        "name": "Compliance",
        "role": "Compliance Officer",
        "file": "compliance_soul.md",
        "heartbeat": "Tue,Thu 12:00",
    },
    "creative": {
        "name": "Creative",
        "role": "Creative Producer",
        "file": "creative_soul.md",
        "heartbeat": "Mon 09:00",
    },
    "meta_master": {
        "name": "Meta Master",
        "role": "Meta Ads Expert",
        "file": "meta_master_soul.md",
        "heartbeat": "Mon 10:00",
    },
    "data_analyst": {
        "name": "Data Analyst",
        "role": "Data Analyst",
        "file": "data_analyst_soul.md",
        "heartbeat": "daily 07:00,18:00",
    },
    "tech_lead": {
        "name": "Tech Lead",
        "role": "Tech Lead",
        "file": "tech_lead_soul.md",
        "heartbeat": "Fri 18:00",
    },
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SoulPrompt:
    agent_key: str
    agent_name: str
    role: str
    version: str
    content: str
    heartbeat: str
    file_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class SoulPromptLoader:
    """
    Loads soul prompts from markdown files and optionally syncs with PostgreSQL.
    """

    VERSION_RE = re.compile(r"Version:\s*([\d.]+)")

    def __init__(self, prompts_dir: Optional[str | Path] = None) -> None:
        if prompts_dir is None:
            # Default: sibling 'prompts/' directory
            self.prompts_dir = Path(__file__).parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")

    def load(self, agent_key: str) -> SoulPrompt:
        """Load a single prompt by agent key."""
        if agent_key not in AGENTS:
            raise KeyError(f"Unknown agent: {agent_key}. Available: {list(AGENTS.keys())}")

        meta = AGENTS[agent_key]
        file_path = self.prompts_dir / meta["file"]

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file missing: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        version = self._extract_version(content) or "1.0.0"

        return SoulPrompt(
            agent_key=agent_key,
            agent_name=meta["name"],
            role=meta["role"],
            version=version,
            content=content,
            heartbeat=meta["heartbeat"],
            file_path=str(file_path),
        )

    def load_all(self) -> dict[str, SoulPrompt]:
        """Load all agent prompts."""
        return {key: self.load(key) for key in AGENTS}

    def _extract_version(self, content: str) -> Optional[str]:
        match = self.VERSION_RE.search(content)
        return match.group(1) if match else None

    def render_for_claw(self, agent_key: str, extra_context: Optional[str] = None) -> str:
        """
        Render a prompt ready for Kimi Claw ingestion.
        Prepends metadata block and optional extra context.
        """
        prompt = self.load(agent_key)
        lines = [
            f"# PRODAFLT Agent: {prompt.agent_name}",
            f"# Role: {prompt.role}",
            f"# Version: {prompt.version}",
            f"# Heartbeat: {prompt.heartbeat}",
            "# ============================================================",
            "",
        ]
        if extra_context:
            lines.extend(["## EXTRA CONTEXT", extra_context, ""])
        lines.append(prompt.content)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

_LOADER: Optional[SoulPromptLoader] = None


def _get_loader() -> SoulPromptLoader:
    global _LOADER
    if _LOADER is None:
        _LOADER = SoulPromptLoader()
    return _LOADER


def get_prompt(agent_key: str) -> SoulPrompt:
    """Load a single prompt (uses singleton loader)."""
    return _get_loader().load(agent_key)


def list_agents() -> list[dict]:
    """Return list of available agents with metadata."""
    return [
        {
            "key": key,
            "name": meta["name"],
            "role": meta["role"],
            "heartbeat": meta["heartbeat"],
        }
        for key, meta in AGENTS.items()
    ]
