"""Anthropic MGTI adapter — Phase 1 stub.

Real implementation lands in Phase 3 (Anthropic MGTI Adapter), with strict-tools
wired in Phase 4. Existing here so src/llm/__init__.py's get_llm factory can
register it without a circular import.
"""
from __future__ import annotations

from typing import Any

from src.llm.base import LLMClient
from src.llm.types import ToolCall, ToolSchema


class AnthropicMGTIClient(LLMClient):
    """Phase 1 stub. Real implementation in Phase 3, tools in Phase 4."""

    def __init__(self) -> None:
        # No-op constructor; Phase 3 reads ANTHROPIC_* env vars via
        # src.llm.config.load_settings() and validates the model name
        # (must start with eu.anthropic.claude-). For Phase 1, construction
        # must NOT raise so the factory cache can store the instance.
        pass

    def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError(
            "AnthropicMGTIClient.complete is implemented in Phase 3"
        )

    def classify_with_tool(
        self,
        messages: list[dict],
        tool: ToolSchema,
        *,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolCall:
        raise NotImplementedError(
            "AnthropicMGTIClient.classify_with_tool is implemented in Phase 4"
        )
