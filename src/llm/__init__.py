"""snow_query LLM abstraction package.

Phase 1 (this commit): types, errors, and the LLMClient ABC.
Phase 1 Plan 02: get_llm factory + LLMSettings + adapter stubs.
Phase 2: AzureOpenAIClient real implementation + call-site rewrite.
Phase 3: AnthropicMGTIClient real implementation.
Phase 4: Strict-tools wiring in classify_with_tool.
Phase 5: Streamlit UI toggle and @st.cache_resource integration.
"""
from src.llm.base import LLMClient
from src.llm.errors import (
    LLMAuthError,
    LLMConfigError,
    LLMError,
    LLMGuardrailError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMTransientError,
)
from src.llm.types import (
    ClassificationResultV1,
    IntentResult,
    ToolCall,
    ToolSchema,
)

__all__ = [
    "LLMClient",
    "LLMError",
    "LLMAuthError",
    "LLMTransientError",
    "LLMGuardrailError",
    "LLMSchemaError",
    "LLMTimeoutError",
    "LLMConfigError",
    "ToolSchema",
    "ToolCall",
    "ClassificationResultV1",
    "IntentResult",
]
