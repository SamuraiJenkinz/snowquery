"""Provider-agnostic LLM client interface (ABS-02).

The ABC enforces the two-method contract at construction time — instantiating
a subclass missing either method raises TypeError. This is the Phase 1 seam:
Phase 2 introduces AzureOpenAIClient, Phase 3 introduces AnthropicMGTIClient,
both implementing this interface.

Method signatures are chosen so that:
  - `complete` accepts `messages: list[dict]` (Azure-native shape including
    {"role": "system", ...} entries) for zero-diff Phase 2 parity. The
    Anthropic adapter (Phase 3) is responsible for extracting the system
    message and promoting it to the top-level `system` field internally.
  - `max_tokens` is a per-call kwarg (the only difference between the two
    duplicated `_call_azure_openai` definitions today is max_tokens 500 vs
    1000 — see RESEARCH.md "Codebase Reconnaissance").
"""
from __future__ import annotations

import abc
from typing import Any

from src.llm.types import ToolCall, ToolSchema


class LLMClient(abc.ABC):
    """Abstract LLM provider interface.

    Concrete adapters (AzureOpenAIClient, AnthropicMGTIClient) implement
    both methods. Adapters return only `str` or `ToolCall` — raw HTTP JSON
    never crosses this boundary (ABS-05).
    """

    @abc.abstractmethod
    def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        """Send a chat-completion request and return the assistant text.

        Args:
            messages: List of {"role", "content"} dicts; the first entry
                may have role "system" (Azure-native shape). The Anthropic
                adapter extracts/promotes system internally.
            max_tokens: Per-call ceiling; default 500 (query_router.py),
                callers override to 1000 for SQL generation (sql_generator.py).
            temperature: Sampling temperature; current code uses 0.1.
            **kwargs: Reserved for adapter-specific overrides.

        Returns:
            The raw assistant text content (caller may JSON-parse it).
        """

    @abc.abstractmethod
    def classify_with_tool(
        self,
        messages: list[dict],
        tool: ToolSchema,
        *,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolCall:
        """Invoke the provider's tool/function-calling path for intent classification.

        Phase 2: Azure adapter uses prompt-based JSON parsing (existing pattern).
        Phase 4: Anthropic adapter uses native strict-tools.
        Both wrap the validated result in `ToolCall`.

        Args:
            messages: Same shape as `complete`.
            tool: Tool schema definition.
            tool_name: Name of the tool to invoke (used for `tool_choice`).
            **kwargs: Reserved for adapter-specific overrides.

        Returns:
            A `ToolCall` carrying the validated tool input dict.

        Raises:
            LLMSchemaError: If the provider returns a malformed/missing
                tool_use response (Phase 4 raises this).
        """
