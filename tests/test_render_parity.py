"""Regression test locking assistant-message render parity in app.py.

The assistant message content is HTML (route-badge / results-count <span>s
built in process_query). It is rendered in TWO places:

  1. The live path in render_main_content:
       st.markdown(response["content"], unsafe_allow_html=True)
  2. The history re-render path in render_chat_history (runs on every
     Streamlit rerun after the first):
       st.markdown(message["content"], unsafe_allow_html=True)

If either call omits unsafe_allow_html=True, the <span> tags render as
literal text. This bit the history path once already (it was missing the
flag), so the badges looked correct when first produced and turned into raw
markup on the next rerun. This test parses app.py's AST and asserts EVERY
st.markdown(...) call whose first argument is `<name>["content"]` (name in
{message, response}) passes unsafe_allow_html=True.

Run with: PYTHONPATH=. python -m pytest tests/test_render_parity.py -q
Or with the full suite: PYTHONPATH=. python -m pytest tests/ -q
"""
from __future__ import annotations

import ast
from pathlib import Path

APP_PY = Path(__file__).resolve().parent.parent / "app.py"


def _is_content_subscript(node: ast.AST) -> bool:
    """True if node is `message["content"]` or `response["content"]`."""
    if not isinstance(node, ast.Subscript):
        return False
    value = node.value
    if not (isinstance(value, ast.Name) and value.id in {"message", "response"}):
        return False
    key = node.slice
    return isinstance(key, ast.Constant) and key.value == "content"


def _collect_content_markdown_calls() -> list[ast.Call]:
    """Find every st.markdown(<name>['content'], ...) call in app.py."""
    tree = ast.parse(APP_PY.read_text(encoding="utf-8"))
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_markdown = (
            isinstance(func, ast.Attribute)
            and func.attr == "markdown"
            and isinstance(func.value, ast.Name)
            and func.value.id == "st"
        )
        if not is_markdown or not node.args:
            continue
        if _is_content_subscript(node.args[0]):
            calls.append(node)
    return calls


def test_content_render_sites_exist():
    """Sanity: both the live and history render sites are present (2 calls)."""
    calls = _collect_content_markdown_calls()
    assert len(calls) >= 2, (
        f"Expected at least 2 st.markdown(<name>['content']) calls "
        f"(live + history render sites); found {len(calls)}."
    )


def test_all_content_render_sites_pass_unsafe_allow_html_true():
    """Every assistant-content st.markdown call MUST pass unsafe_allow_html=True.

    Omitting it renders the route-badge / results-count <span>s as literal
    text on history re-render (the original bug).
    """
    calls = _collect_content_markdown_calls()
    for call in calls:
        kw = {k.arg: k.value for k in call.keywords if k.arg}
        assert "unsafe_allow_html" in kw, (
            f"st.markdown(...content...) at app.py line {call.lineno} is missing "
            f"unsafe_allow_html — HTML spans will render as literal text."
        )
        flag = kw["unsafe_allow_html"]
        assert isinstance(flag, ast.Constant) and flag.value is True, (
            f"st.markdown(...content...) at app.py line {call.lineno} must pass "
            f"unsafe_allow_html=True (got a non-True value)."
        )
