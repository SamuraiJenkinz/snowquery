"""Azure OpenAI adapter — Phase 1 stub.

Real implementation lands in Phase 2 (Azure Extraction + Parity Gate).
Existing here so src/llm/__init__.py's get_llm factory can register it
without a circular import.
"""
from __future__ import annotations

from typing import Any

from src.llm.base import LLMClient
from src.llm.types import ToolCall, ToolSchema


class AzureOpenAIClient(LLMClient):
    """Phase 1 stub. Real implementation in Phase 2."""

    def __init__(self) -> None:
        # No-op constructor; Phase 2 will read AZURE_* env vars via
        # src.llm.config.load_settings(). Construction must NOT raise in
        # Phase 1 so the factory cache can store the instance.
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
            "AzureOpenAIClient.complete is implemented in Phase 2"
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
            "AzureOpenAIClient.classify_with_tool is implemented in Phase 2"
        )
