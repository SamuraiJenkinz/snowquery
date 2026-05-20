---
phase: 02-azure-extraction-parity-gate
plan: 03
type: execute
wave: 2
depends_on: ["02-01", "02-02"]
files_modified:
  - src/query_router.py
  - src/sql_generator.py
autonomous: true

must_haves:
  truths:
    - "`grep -n _call_azure_openai src/query_router.py src/sql_generator.py` returns ZERO hits (success criterion #1, ABS-06)"
    - "All three call sites (classify_intent, generate_sql, generate_executive_summary) consume LLMClient via `client = get_llm()` + `with llm_to_query_error(): client.complete(...)` (success criterion #1, ABS-06)"
    - "max_tokens=500 preserved at classify_intent and generate_executive_summary; max_tokens=1000 preserved at generate_sql (this is the ONLY difference between the two _call_azure_openai duplicates today — must survive extraction)"
    - "The `.strip()` call stays at the call site, not in the adapter — preserves byte-identical post-extraction string (RESEARCH.md Pitfall 1)"
    - "Unused imports removed from both files: `import requests`, and `from config import API_VERSION, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT` — no other code in either file uses them after _call_azure_openai is deleted (RESEARCH.md OQ-5)"
    - "The existing `except QueryError: raise` guards in classify_intent (line 212-213) and generate_sql (line 238-239) are preserved unchanged — `llm_to_query_error()` raises QueryError, and the existing guards correctly pass it through"
    - "generate_executive_summary's broad `except Exception: return None` (line 546) is preserved unchanged — QueryError raised by llm_to_query_error() is a subclass of Exception and is correctly swallowed (RESEARCH.md Pitfall 4 — this is intentional behavior, do NOT add `except QueryError: raise` here)"
  artifacts:
    - path: "src/query_router.py"
      provides: "Two call sites (classify_intent at line ~180, generate_executive_summary at line ~542) routed through get_llm() + llm_to_query_error(); _call_azure_openai definition (lines 105-141) DELETED; unused imports removed"
      contains: "from src.llm import get_llm"
    - path: "src/sql_generator.py"
      provides: "One call site (generate_sql at line ~194) routed through get_llm() + llm_to_query_error(); _call_azure_openai definition (lines 86-133) DELETED; unused imports removed"
      contains: "from src.llm import get_llm"
  key_links:
    - from: "src/query_router.py classify_intent"
      to: "src.llm.get_llm + src.llm._compat.llm_to_query_error"
      via: "client = get_llm(); with llm_to_query_error(): content = client.complete(messages, max_tokens=500)"
      pattern: "with llm_to_query_error\\(\\):"
    - from: "src/sql_generator.py generate_sql"
      to: "src.llm.get_llm + src.llm._compat.llm_to_query_error"
      via: "client = get_llm(); with llm_to_query_error(): content = client.complete(messages, max_tokens=1000)"
      pattern: "max_tokens=1000"
    - from: "src/query_router.py generate_executive_summary"
      to: "src.llm.get_llm + src.llm._compat.llm_to_query_error"
      via: "client = get_llm(); with llm_to_query_error(): summary = client.complete(messages, max_tokens=500)"
      pattern: "with llm_to_query_error\\(\\):"
---

<objective>
Replace the three call sites that currently call `_call_azure_openai(...)` with the new seam — `client = get_llm()` + `with llm_to_query_error(): client.complete(...)` — and DELETE both duplicated `_call_azure_openai` definitions. Also remove the imports that become unused once those helpers are gone.

Purpose: This is the mechanical refactor at the heart of Phase 2. Plan 01 made the adapter real; Plan 02 made the error translation seam exist. This plan rewires the application so the new seam is what actually runs in production. After this plan, `grep _call_azure_openai src/` returns zero hits — that is the headline success criterion #1.

Output: Two existing files edited (`src/query_router.py`, `src/sql_generator.py`). Net change is a deletion (two ~30-line helper definitions removed; three call sites become 3 lines each instead of 1; imports tightened). Expected line-count delta: roughly -45 lines net per file pair.
</objective>

<execution_context>
@C:\Users\taylo\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\taylo\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/02-azure-extraction-parity-gate/02-CONTEXT.md
@.planning/phases/02-azure-extraction-parity-gate/02-RESEARCH.md
@.planning/phases/02-azure-extraction-parity-gate/02-01-SUMMARY.md
@.planning/phases/02-azure-extraction-parity-gate/02-02-SUMMARY.md

# The files this plan edits
@src/query_router.py
@src/sql_generator.py

# The seam pieces being wired in (from Plans 01 and 02)
@src/llm/__init__.py
@src/llm/azure_openai.py
@src/llm/_compat.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewire src/query_router.py — delete _call_azure_openai, migrate classify_intent (CS1) and generate_executive_summary (CS3)</name>
  <files>src/query_router.py</files>
  <action>
Edit `src/query_router.py`. There are four mechanical changes, in order:

**Change 1 — Imports (top of file, lines 1-21).**

Today:
```python
import json
from typing import Any, Optional

import pandas as pd
import requests

from config import (
    API_VERSION,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    TOP_K_SEMANTIC,
)
from src.semantic_search import semantic_query
from src.sql_generator import query_with_sql
from src.utils import QueryError, format_schema_for_llm, logger
```

After this plan:
```python
import json
from typing import Any, Optional

import pandas as pd

from config import TOP_K_SEMANTIC
from src.llm import get_llm
from src.llm._compat import llm_to_query_error
from src.semantic_search import semantic_query
from src.sql_generator import query_with_sql
from src.utils import QueryError, format_schema_for_llm, logger
```

Removed:
- `import requests` — only `_call_azure_openai` used it.
- `API_VERSION`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` from the `config` import — only `_call_azure_openai` used them. Confirm by grepping the file for each name before deletion (must appear ONLY inside the function body of `_call_azure_openai`, which is being deleted in Change 2).

Added:
- `from src.llm import get_llm`
- `from src.llm._compat import llm_to_query_error`

Verify the grep before deleting the config imports — if any are referenced outside `_call_azure_openai`, the plan is wrong and execution must stop:

```
grep -n "API_VERSION\|AZURE_OPENAI_API_KEY\|AZURE_OPENAI_ENDPOINT" src/query_router.py
```

Expected: matches ONLY inside `def _call_azure_openai(...)` body (lines 105-141 in the current file). If matches appear outside that range, stop and flag the assumption violation.

**Change 2 — Delete `_call_azure_openai` entirely (currently lines 105-141 in `query_router.py`).**

Remove the entire function definition including its docstring and trailing blank line. The function is being replaced by `client.complete()` at the call site.

**Change 3 — Rewire `classify_intent` (CS1, currently line 180).**

Today:
```python
        content = _call_azure_openai(messages).strip()
```

After this plan:
```python
        client = get_llm()
        with llm_to_query_error():
            content = client.complete(messages, max_tokens=500).strip()
```

Notes:
- `max_tokens=500` matches the hardcoded value in the old `query_router.py:_call_azure_openai` payload — preserves identical request shape.
- `.strip()` stays at the call site (RESEARCH.md Pitfall 1 — the adapter intentionally does NOT strip; double-strip would still pass tests but breaks the byte-identical guarantee).
- The surrounding `try:` / `except QueryError: raise` / `except Exception as e: ...` structure at lines 166-216 stays exactly as-is. `llm_to_query_error()` raises `QueryError`, which is caught by the existing `except QueryError: raise` at line 212-213 and propagates correctly. The broad `except Exception` at line 214-216 catches downstream JSON parse errors as before — it correctly does NOT catch `QueryError` because the `except QueryError: raise` clause appears first.

**Change 4 — Rewire `generate_executive_summary` (CS3, currently line 542).**

Today:
```python
        summary = _call_azure_openai(messages).strip()
```

After this plan:
```python
        client = get_llm()
        with llm_to_query_error():
            summary = client.complete(messages, max_tokens=500).strip()
```

Notes:
- `max_tokens=500` matches the old `query_router.py:_call_azure_openai` payload.
- The surrounding `try:` / `except Exception as e: ... return None` at lines 511-548 stays exactly as-is. RESEARCH.md Pitfall 4 documents that this silent-failure behavior is INTENTIONAL — the executive summary is optional; the app continues without it on error. The `QueryError` raised by `llm_to_query_error()` IS an `Exception` subclass and IS correctly swallowed by the broad handler here — this is the SAME behavior as today (the old `_call_azure_openai` raised `QueryError` which was also caught by this same broad handler). Do NOT add `except QueryError: raise` to this function.

**Sanity-check after edits:**

```
grep -n "_call_azure_openai" src/query_router.py
```

Expected: NO output (zero hits). If any line still references `_call_azure_openai`, the migration is incomplete.

```
grep -n "API_VERSION\|AZURE_OPENAI_API_KEY\|AZURE_OPENAI_ENDPOINT\|^import requests" src/query_router.py
```

Expected: NO output. These names are gone from the file entirely (no imports, no usages).
  </action>
  <verify>
Run from project root:

```
python -c "
# 1. query_router.py imports cleanly (no syntax errors, no remaining references to deleted names)
import src.query_router as qr
assert hasattr(qr, 'classify_intent')
assert hasattr(qr, 'generate_executive_summary')
assert not hasattr(qr, '_call_azure_openai'), '_call_azure_openai still exists in query_router'

# 2. Specific function bodies contain the new seam
import inspect
src_classify = inspect.getsource(qr.classify_intent)
assert 'get_llm()' in src_classify, 'classify_intent missing get_llm()'
assert 'llm_to_query_error()' in src_classify, 'classify_intent missing llm_to_query_error()'
assert 'max_tokens=500' in src_classify, 'classify_intent missing max_tokens=500'
assert '_call_azure_openai' not in src_classify, 'classify_intent still calls _call_azure_openai'

src_summary = inspect.getsource(qr.generate_executive_summary)
assert 'get_llm()' in src_summary, 'generate_executive_summary missing get_llm()'
assert 'llm_to_query_error()' in src_summary, 'generate_executive_summary missing llm_to_query_error()'
assert 'max_tokens=500' in src_summary, 'generate_executive_summary missing max_tokens=500'
assert '_call_azure_openai' not in src_summary, 'generate_executive_summary still calls _call_azure_openai'

# 3. The file no longer imports requests or the Azure config names at module level
src_module = inspect.getsource(qr)
assert 'import requests' not in src_module, 'requests still imported in query_router'
assert 'AZURE_OPENAI_API_KEY' not in src_module, 'AZURE_OPENAI_API_KEY still referenced in query_router'
assert 'AZURE_OPENAI_ENDPOINT' not in src_module, 'AZURE_OPENAI_ENDPOINT still referenced in query_router'
assert 'API_VERSION' not in src_module, 'API_VERSION still referenced in query_router'

# 4. The .strip() is still at the call site (not in the adapter)
assert '.complete(messages, max_tokens=500).strip()' in src_module, '.strip() missing or in wrong place'

print('TASK 1 OK')
"
```

Must print `TASK 1 OK`.

Also confirm the file still parses and the existing test suite (Phase 1) still passes:

```
python -m py_compile src/query_router.py && echo "syntax OK"
python -m pytest tests/test_llm_seam.py -v
```

Both must succeed.
  </verify>
  <done>
- `src/query_router.py` no longer contains `_call_azure_openai` (deleted at former lines 105-141).
- `classify_intent` (CS1) uses `client = get_llm()` + `with llm_to_query_error(): content = client.complete(messages, max_tokens=500).strip()`.
- `generate_executive_summary` (CS3) uses `client = get_llm()` + `with llm_to_query_error(): summary = client.complete(messages, max_tokens=500).strip()`.
- Imports cleaned: `import requests` removed; `API_VERSION`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` removed from `from config import (...)`; added `from src.llm import get_llm` and `from src.llm._compat import llm_to_query_error`.
- The existing `try/except QueryError: raise/except Exception` structure in `classify_intent` is preserved.
- The existing broad `except Exception: return None` in `generate_executive_summary` is preserved (intentional silent-failure path — RESEARCH.md Pitfall 4).
- File compiles; Phase 1's `tests/test_llm_seam.py` still passes 6/6.
  </done>
</task>

<task type="auto">
  <name>Task 2: Rewire src/sql_generator.py — delete _call_azure_openai, migrate generate_sql (CS2)</name>
  <files>src/sql_generator.py</files>
  <action>
Edit `src/sql_generator.py`. Three mechanical changes:

**Change 1 — Imports (top of file, lines 1-22).**

Today:
```python
import json
from typing import Any, Optional

import duckdb
import pandas as pd
import requests

from config import (
    API_VERSION,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    DEFAULT_QUERY_LIMIT,
    DUCKDB_PATH,
    MAX_QUERY_LIMIT,
)
from src.utils import QueryError, format_schema_for_llm, logger
```

After this plan:
```python
import json
from typing import Any, Optional

import duckdb
import pandas as pd

from config import (
    DEFAULT_QUERY_LIMIT,
    DUCKDB_PATH,
    MAX_QUERY_LIMIT,
)
from src.llm import get_llm
from src.llm._compat import llm_to_query_error
from src.utils import QueryError, format_schema_for_llm, logger
```

Removed: `import requests`, plus the three Azure names from the `config` import block (`API_VERSION`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`). `DEFAULT_QUERY_LIMIT`, `DUCKDB_PATH`, `MAX_QUERY_LIMIT` STAY — they are used by `execute_sql` and `query_with_sql`.

Added: `from src.llm import get_llm` and `from src.llm._compat import llm_to_query_error`.

Verify the grep before deleting:

```
grep -n "API_VERSION\|AZURE_OPENAI_API_KEY\|AZURE_OPENAI_ENDPOINT" src/sql_generator.py
```

Expected: matches ONLY inside `def _call_azure_openai(...)` body (lines 86-133 in the current file).

**Change 2 — Delete `_call_azure_openai` entirely (currently lines 86-133 in `sql_generator.py`).**

Remove the entire function definition. Note: the file's `_call_azure_openai` has `max_tokens: 1000` in the payload — this is the ONLY logic difference between the two duplicates. Plan 01's `complete()` accepts `max_tokens` as a per-call kwarg; the call site uses `max_tokens=1000` to preserve identical behavior.

**Change 3 — Rewire `generate_sql` (CS2, currently line 194).**

Today:
```python
        content = _call_azure_openai(messages).strip()
```

After this plan:
```python
        client = get_llm()
        with llm_to_query_error():
            content = client.complete(messages, max_tokens=1000).strip()
```

Notes:
- `max_tokens=1000` — this preserves the only existing behavioral difference between the two _call_azure_openai duplicates. CONTEXT.md flags this explicitly as the load-bearing parameter for SQL generation (SQL responses need headroom; classification responses don't).
- `.strip()` stays at the call site (same reasoning as query_router.py).
- The surrounding `try:` / `except QueryError: raise` / `except Exception as e: ... raise QueryError(...)` structure at lines 192-245 stays exactly as-is. `llm_to_query_error()` raises `QueryError`, caught by the existing `except QueryError: raise` at line 238-239 (the existing handler at line 240-245 re-wraps any other Exception as `QueryError` — this is correct, the `except QueryError: raise` clause prevents double-wrapping).

**Sanity-check after edits:**

```
grep -n "_call_azure_openai" src/sql_generator.py
```

Expected: NO output.

```
grep -n "API_VERSION\|AZURE_OPENAI_API_KEY\|AZURE_OPENAI_ENDPOINT\|^import requests" src/sql_generator.py
```

Expected: NO output.

**Cross-file sanity check (both files):**

```
grep -rn "_call_azure_openai" src/
```

Expected: NO output. This is success criterion #1 — `grep` returns zero hits across both target files.
  </action>
  <verify>
Run from project root:

```
python -c "
# 1. sql_generator.py imports cleanly and _call_azure_openai is gone
import src.sql_generator as sg
assert hasattr(sg, 'generate_sql')
assert hasattr(sg, 'execute_sql')
assert hasattr(sg, 'query_with_sql')
assert not hasattr(sg, '_call_azure_openai'), '_call_azure_openai still exists in sql_generator'

# 2. generate_sql contains the new seam with max_tokens=1000 preserved
import inspect
src_genSql = inspect.getsource(sg.generate_sql)
assert 'get_llm()' in src_genSql, 'generate_sql missing get_llm()'
assert 'llm_to_query_error()' in src_genSql, 'generate_sql missing llm_to_query_error()'
assert 'max_tokens=1000' in src_genSql, 'generate_sql missing max_tokens=1000 (this is the load-bearing diff!)'
assert '_call_azure_openai' not in src_genSql, 'generate_sql still calls _call_azure_openai'

# 3. File-level: no requests import, no Azure names
src_module = inspect.getsource(sg)
assert 'import requests' not in src_module, 'requests still imported in sql_generator'
assert 'AZURE_OPENAI_API_KEY' not in src_module, 'AZURE_OPENAI_API_KEY still referenced'
assert 'AZURE_OPENAI_ENDPOINT' not in src_module, 'AZURE_OPENAI_ENDPOINT still referenced'
assert 'API_VERSION' not in src_module, 'API_VERSION still referenced'
# DEFAULT_QUERY_LIMIT/DUCKDB_PATH/MAX_QUERY_LIMIT stay — they're used by execute_sql
assert 'DEFAULT_QUERY_LIMIT' in src_module, 'DEFAULT_QUERY_LIMIT should still be imported'

# 4. .strip() stays at the call site
assert '.complete(messages, max_tokens=1000).strip()' in src_module, '.strip() missing or wrong place'

print('TASK 2 OK')
"
```

Must print `TASK 2 OK`.

**Final cross-file grep — success criterion #1 in action:**

```
grep -rn "_call_azure_openai" src/
```

Must produce **NO OUTPUT**. This is the bar set by ROADMAP.md success criterion #1 / ABS-06.

Also confirm both files compile and Phase 1 acceptance gate still passes:

```
python -m py_compile src/query_router.py src/sql_generator.py && echo "syntax OK"
python -m pytest tests/test_llm_seam.py -v
```

Both must succeed.
  </verify>
  <done>
- `src/sql_generator.py` no longer contains `_call_azure_openai` (deleted at former lines 86-133).
- `generate_sql` uses `client = get_llm()` + `with llm_to_query_error(): content = client.complete(messages, max_tokens=1000).strip()` — `max_tokens=1000` preserved.
- Imports cleaned: `import requests` removed; `API_VERSION`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` removed from `from config import (...)`; `DEFAULT_QUERY_LIMIT`, `DUCKDB_PATH`, `MAX_QUERY_LIMIT` PRESERVED; added `from src.llm import get_llm` and `from src.llm._compat import llm_to_query_error`.
- The existing `try/except QueryError: raise/except Exception` structure in `generate_sql` is preserved.
- File compiles; Phase 1 acceptance gate still 6/6 passing.
- `grep -rn _call_azure_openai src/` returns zero hits across both target files — success criterion #1 / ABS-06 met.
  </done>
</task>

</tasks>

<verification>
End-of-plan acceptance bar — these are the success criterion #1 verifications:

```
# 1. _call_azure_openai is gone from both files
grep -rn "_call_azure_openai" src/ ; test $? -ne 0 && echo "PASS: _call_azure_openai eliminated"

# 2. Both files compile
python -m py_compile src/query_router.py src/sql_generator.py && echo "syntax OK"

# 3. The three call sites use the new seam (string-grep proves it)
grep -c "with llm_to_query_error" src/query_router.py   # expect 2
grep -c "with llm_to_query_error" src/sql_generator.py  # expect 1

# 4. max_tokens preservation (the only behavioral difference between the duplicates today)
grep -n "max_tokens=500" src/query_router.py   # expect 2 hits (classify_intent + generate_executive_summary)
grep -n "max_tokens=1000" src/sql_generator.py # expect 1 hit (generate_sql)

# 5. Unused imports removed
grep -n "^import requests$" src/query_router.py src/sql_generator.py  # expect NO output
grep -n "AZURE_OPENAI_API_KEY\|AZURE_OPENAI_ENDPOINT\|API_VERSION" src/query_router.py src/sql_generator.py  # expect NO output

# 6. Phase 1 acceptance gate still passes (we did not break the seam)
python -m pytest tests/test_llm_seam.py -v   # expect 6/6 PASSED
```

LOCKED files NOT modified by this plan: `app.py`, top-level `config.py`, and all files inside `src/llm/` (those are Phase 1 + Plans 01-02 territory):

```
git diff --name-only HEAD app.py config.py src/llm/ 2>&1 | head
```

Must produce no output.
</verification>

<success_criteria>
- `grep -rn "_call_azure_openai" src/` returns ZERO hits — the literal text of ROADMAP.md success criterion #1 / ABS-06.
- All three call sites use `client = get_llm()` + `with llm_to_query_error(): client.complete(messages, max_tokens=X).strip()`.
- `max_tokens=500` at `classify_intent` and `generate_executive_summary`; `max_tokens=1000` at `generate_sql` — the load-bearing per-call-site difference is preserved.
- `.strip()` is applied AT the call site, not in the adapter (RESEARCH.md Pitfall 1).
- Unused imports removed: `import requests` gone from both files; `API_VERSION`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` gone from both `from config import (...)` blocks.
- Existing exception-handling structure (the `try/except QueryError: raise/except Exception` blocks in `classify_intent` and `generate_sql`; the broad `except Exception: return None` in `generate_executive_summary`) is preserved unchanged.
- Both files compile cleanly; Phase 1 acceptance gate (`tests/test_llm_seam.py`) still 6/6 passing.
- LOCKED files (`app.py`, `config.py`, `src/llm/__init__.py`, `src/llm/base.py`, `src/llm/errors.py`, `src/llm/types.py`, `src/llm/config.py`, `src/llm/azure_openai.py`, `src/llm/_compat.py`) NOT modified.

Maps to: Success criterion #1 (full — `_call_azure_openai` eliminated; DI via `get_llm()` at all three call sites); ABS-06 (full).
</success_criteria>

<output>
After completion, create `.planning/phases/02-azure-extraction-parity-gate/02-03-SUMMARY.md` documenting:
- Output of `grep -rn "_call_azure_openai" src/` (must be empty — this is the headline success criterion #1).
- Line counts before/after for both edited files (expected: ~-45 net per file after deleting the helper and tightening imports).
- Confirmation that `max_tokens=500` appears at 2 call sites in `query_router.py` (CS1 + CS3) and `max_tokens=1000` at 1 call site in `sql_generator.py` (CS2).
- Confirmation that the three call-site try/except structures were preserved verbatim.
- Confirmation that Phase 1 acceptance gate (`tests/test_llm_seam.py`) still runs green.
- A note that the silent-failure broad-except in `generate_executive_summary` was intentionally NOT changed (RESEARCH.md Pitfall 4 — preserves byte-identical user-visible behavior on summary failures).
</output>
</content>
</invoke>