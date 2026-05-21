---
phase: 03-anthropic-mgti-adapter
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .env.example
  - src/llm/azure_openai.py
autonomous: true

must_haves:
  truths:
    - "`.env.example` lists all 9 Anthropic-related variables (LLM_PROVIDER_DEFAULT, ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_VERSION, ANTHROPIC_MAX_TOKENS, ANTHROPIC_TEMPERATURE, ANTHROPIC_TIMEOUT_S, ANTHROPIC_TOOLS_SUPPORTED) each followed by a non-empty default-value or descriptive comment line so SC #4's `.env.example` test can grep both the var name AND find a documented default (CFG-02, CFG-04)"
    - "Existing Azure variables (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, API_VERSION) remain present and unchanged in `.env.example` — file is APPENDED to, not replaced (locked from Phase 2)"
    - "AzureOpenAIClient.__init__ emits exactly one logger.info('llm_provider_loaded', extra={'provider': 'azure_openai', 'base_url': self._endpoint}) event at construction time (SC #5: 'App startup logs the configured base URL for each loadable provider exactly once'); the factory cache in src/llm/__init__.py guarantees one log per provider per process — calling get_llm('azure_openai') twice still emits exactly one llm_provider_loaded event (OBS-01, OBS-04)"
    - "Phase 2 acceptance gate (tests/test_phase2_parity.py) still passes 12/12 after the AzureOpenAIClient.__init__ edit — the startup log line is additive and does NOT touch the existing complete()/classify_with_tool() bodies, the __repr__ override, the no-op pre-flight pattern, or any of the existing logger.info('llm_call', ...) event shape"
  artifacts:
    - path: ".env.example"
      provides: "Documented config template covering all 9 Anthropic vars + the 4 existing Azure entries + LOG_LEVEL"
      contains: "ANTHROPIC_BASE_URL"
      min_lines: 30
    - path: "src/llm/azure_openai.py"
      provides: "AzureOpenAIClient with added llm_provider_loaded startup log in __init__; everything else from Phase 2 unchanged"
      contains: "llm_provider_loaded"
  key_links:
    - from: "src/llm/azure_openai.py"
      to: "src.utils.logger"
      via: "logger.info('llm_provider_loaded', extra={'provider': 'azure_openai', 'base_url': self._endpoint}) called inside __init__ AFTER settings are loaded"
      pattern: "logger\\.info.*llm_provider_loaded"
    - from: ".env.example"
      to: "src/llm/config.py LLMSettings (the 8 anthropic_* fields + provider_default)"
      via: "every LLMSettings env-var the adapter reads has a documented default in .env.example"
      pattern: "ANTHROPIC_(BASE_URL|API_KEY|MODEL|VERSION|MAX_TOKENS|TEMPERATURE|TIMEOUT_S|TOOLS_SUPPORTED)|LLM_PROVIDER_DEFAULT"
---

<objective>
Lay the two foundational pieces Phase 3's acceptance gate (Plan 04) will assert against: (a) extend `.env.example` with the 9 new Anthropic-related variables required by SC #4, and (b) add a one-line "provider loaded" startup log to `AzureOpenAIClient.__init__` so SC #5 ("App startup logs the configured base URL for each loadable provider exactly once") works for BOTH providers without needing to edit `src/llm/__init__.py`. Plan 03 mirrors the same `__init__` startup log in `AnthropicMGTIClient`; together they satisfy the "for each loadable provider" language verbatim.

Purpose: These two changes are independent of the Anthropic adapter rewrite (Plan 03) and the compat-layer dispatch (Plan 02) — they sit in Wave 1 so they run in parallel with `_compat.py` work, shortening the critical path. They are also additive: Phase 2 tests stay green, and Plan 04's acceptance gate can read the new `.env.example` and assert the Azure startup log fires once per process.

Output: One config file extended (`.env.example`, 4 vars + LOG_LEVEL → 4 vars + LOG_LEVEL + 9 Anthropic vars + section comments), one source file with a single 1-line addition inside `__init__` (`src/llm/azure_openai.py`).

DO NOT: rewrite `src/llm/azure_openai.py`. Touch ONLY `__init__`. Leave `__repr__`, `complete()`, `classify_with_tool()`, `_log_llm_call`, `_extract_model_from_endpoint`, and the module docstring exactly as Phase 2 produced them.
</objective>

<execution_context>
@C:\Users\taylo\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\taylo\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-anthropic-mgti-adapter/03-CONTEXT.md
@.planning/phases/03-anthropic-mgti-adapter/03-RESEARCH.md

# The Azure adapter this plan minimally edits — Phase 2 locked code
@src/llm/azure_openai.py

# The current .env.example this plan extends
@.env.example

# The settings dataclass that drives which env vars matter
@src/llm/config.py

# Phase 2's acceptance gate — must still pass after this plan
@tests/test_phase2_parity.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend .env.example with the 9 Anthropic-related variables (SC #4)</name>
  <files>.env.example</files>
  <action>
APPEND to `.env.example` (do NOT rewrite the existing 4 lines — Phase 2 locked them). After the existing `LOG_LEVEL=INFO` line, add a blank line and then the Anthropic block. Final file structure:

```
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-endpoint.com/openai/v1/deployments/your-deployment/chat/completions
AZURE_OPENAI_API_KEY=your-api-key-here
API_VERSION=2023-05-15

# Logging
LOG_LEVEL=INFO

# Anthropic MGTI (Claude 4.5+ via MMC Apigee gateway)
# Provider selector — set to anthropic_mgti to route to Claude
LLM_PROVIDER_DEFAULT=azure_openai

# Full URL up to /v1. Adapter appends /model/{name}/messages.
# Prod:     https://int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1
# Non-prod: https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1
ANTHROPIC_BASE_URL=https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1

# Issued via Hubble (https://hubble.mmc.com/apps) after coreapi-infrastructure merge
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Must be Claude 4.5+ with eu. prefix (EU Bedrock region)
ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-4-5-20250929-v1:0

# Bedrock-required constant — do not change
ANTHROPIC_VERSION=bedrock-2023-05-31

# Max tokens per response (required by Anthropic API, unlike OpenAI)
ANTHROPIC_MAX_TOKENS=1024

# Sampling temperature (omitted automatically for opus-4-7 models)
ANTHROPIC_TEMPERATURE=0.0

# HTTP timeout in seconds
ANTHROPIC_TIMEOUT_S=30

# Set to false if proxy regresses on tools support (escape hatch for Phase 4)
ANTHROPIC_TOOLS_SUPPORTED=true
```

Requirements drawn from CONTEXT.md / RESEARCH.md "`.env.example` — Required Additions":

- **All 9 variables MUST be present** as `NAME=value` assignments (not just comment mentions). The SC #4 test (Plan 04) reads the file and asserts `f"{var}=" in content` for every var.
- **Every variable MUST have a non-empty default or placeholder value** to the right of `=`. The test asserts `len(value) > 0` on the right-hand side after split.
- **Documented defaults**: `ANTHROPIC_VERSION=bedrock-2023-05-31`, `ANTHROPIC_MAX_TOKENS=1024`, `ANTHROPIC_TEMPERATURE=0.0`, `ANTHROPIC_TIMEOUT_S=30`, `ANTHROPIC_TOOLS_SUPPORTED=true`, `LLM_PROVIDER_DEFAULT=azure_openai` MUST match the defaults declared in `src/llm/config.py` (see `LLMSettings` and `load_settings`).
- **`LLM_PROVIDER_DEFAULT=azure_openai`** — locked from Phase 5 decision in PROJECT.md ("Default provider stays `azure_openai` so upgrade is byte-identical for existing deployments").
- **`ANTHROPIC_BASE_URL` placeholder** is the staging URL (not prod) — operator must change to prod URL on deploy. Comment lines above the var document both URLs per RESEARCH.md "MGTI Proxy Contract → Endpoint".
- **`ANTHROPIC_MODEL` placeholder** is a concrete `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` so a fresh-clone developer can `cp .env.example .env` and the adapter constructs without `LLMConfigError` (it would only raise at `complete()` time for the dummy API key, which is the expected developer behavior).
- **Order of additions**: section comment first (`# Anthropic MGTI ...`), then `LLM_PROVIDER_DEFAULT` (the selector), then the 8 ANTHROPIC_* vars in the same order they appear in `LLMSettings`. Each var is preceded by a one-line `#`-comment explaining its purpose. The SC #4 test does NOT assert comment text — but reviewers (and the operator running `cp .env.example .env`) will read these.

Why these specific defaults (each item maps to a locked decision in CONTEXT.md):
- `LLM_PROVIDER_DEFAULT=azure_openai`: PROJECT.md Phase 5 decision; Phase 3 must not flip the default.
- `ANTHROPIC_BASE_URL=<stage>`: prod URL would be live; non-prod is the safer template for a dev clone.
- `ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-4-5-20250929-v1:0`: passes the `eu.anthropic.claude-` prefix check (SC #2) so `AnthropicMGTIClient()` does NOT raise at construction with the sample env.
- `ANTHROPIC_VERSION=bedrock-2023-05-31`: CONTEXT.md ("Bedrock-required constant per MGTI quickstart"), also matches `LLMSettings.anthropic_version` default.
- `ANTHROPIC_TEMPERATURE=0.0`: matches `LLMSettings.anthropic_temperature` default; opus-4-7 models will omit it anyway (Plan 03 implements that), but the value should still be valid.
- `ANTHROPIC_TOOLS_SUPPORTED=true`: matches `LLMSettings.anthropic_tools_supported` default; Phase 4 owns the escape hatch.
  </action>
  <verify>
Run from project root (PowerShell or Bash):

```
python -c "
content = open('.env.example').read()
required = [
    'LLM_PROVIDER_DEFAULT',
    'ANTHROPIC_BASE_URL',
    'ANTHROPIC_API_KEY',
    'ANTHROPIC_MODEL',
    'ANTHROPIC_VERSION',
    'ANTHROPIC_MAX_TOKENS',
    'ANTHROPIC_TEMPERATURE',
    'ANTHROPIC_TIMEOUT_S',
    'ANTHROPIC_TOOLS_SUPPORTED',
]
# 1. Every var present as NAME=...
for var in required:
    assert f'{var}=' in content, f'MISSING: {var}= not found in .env.example'

# 2. Every var has a non-empty value after the =
for line in content.splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    if '=' not in line:
        continue
    name, _, value = line.partition('=')
    if name in required:
        assert len(value) > 0, f'{name} has empty value: {line!r}'

# 3. Defaults match LLMSettings (the adapter reads these defaults at runtime)
expected_defaults = {
    'LLM_PROVIDER_DEFAULT': 'azure_openai',
    'ANTHROPIC_VERSION': 'bedrock-2023-05-31',
    'ANTHROPIC_MAX_TOKENS': '1024',
    'ANTHROPIC_TEMPERATURE': '0.0',
    'ANTHROPIC_TIMEOUT_S': '30',
    'ANTHROPIC_TOOLS_SUPPORTED': 'true',
}
for line in content.splitlines():
    line = line.strip()
    if '=' not in line or line.startswith('#'):
        continue
    name, _, value = line.partition('=')
    if name in expected_defaults:
        assert value == expected_defaults[name], (
            f'{name} default mismatch: got {value!r}, expected {expected_defaults[name]!r}'
        )

# 4. ANTHROPIC_MODEL placeholder passes the eu.anthropic.claude- prefix check (SC #2)
for line in content.splitlines():
    if line.startswith('ANTHROPIC_MODEL='):
        model = line.split('=', 1)[1]
        assert model.startswith('eu.anthropic.claude-'), (
            f'ANTHROPIC_MODEL placeholder fails SC #2 prefix check: {model!r}'
        )
        break
else:
    raise AssertionError('ANTHROPIC_MODEL line not found')

# 5. Existing Phase 2 lines preserved (not deleted by accident)
for var in ('AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY', 'API_VERSION', 'LOG_LEVEL'):
    assert f'{var}=' in content, f'REGRESSION: Phase 2 line {var}= got deleted'

print('TASK 1 OK')
"
```

Must print `TASK 1 OK`. If any assertion fails, fix the file and re-run.
  </verify>
  <done>
- `.env.example` contains all 9 Phase 3 variables (`LLM_PROVIDER_DEFAULT` + 8 `ANTHROPIC_*`) as `NAME=value` assignments with non-empty defaults.
- Defaults match `LLMSettings` in `src/llm/config.py` for the optional vars (`ANTHROPIC_VERSION`, `ANTHROPIC_MAX_TOKENS`, `ANTHROPIC_TEMPERATURE`, `ANTHROPIC_TIMEOUT_S`, `ANTHROPIC_TOOLS_SUPPORTED`).
- `LLM_PROVIDER_DEFAULT=azure_openai` (Phase 5 locked decision — Phase 3 does NOT flip the default).
- `ANTHROPIC_MODEL` placeholder starts with `eu.anthropic.claude-` so SC #2's prefix check does not fire when an operator runs `cp .env.example .env` with the placeholder model.
- The 4 existing Phase 2 lines (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `API_VERSION`, `LOG_LEVEL`) are preserved verbatim.
- Section comments document each var's purpose for the operator.
- Satisfies SC #4 (`.env.example` lists every new Anthropic variable with documented defaults).
  </done>
</task>

<task type="auto">
  <name>Task 2: Add llm_provider_loaded startup log to AzureOpenAIClient.__init__ (SC #5 — Azure half)</name>
  <files>src/llm/azure_openai.py</files>
  <action>
Edit ONLY the `__init__` method of `AzureOpenAIClient` in `src/llm/azure_openai.py`. DO NOT touch any other part of the file (the existing `_extract_model_from_endpoint`, `_log_llm_call`, `__repr__`, `complete`, `classify_with_tool`, the module docstring, imports — all Phase 2 locked code, must remain byte-identical).

Why this lives in `__init__` (per RESEARCH.md OQ-1 / "SC #5 Startup Logging" Option 3):
- The factory cache in `src/llm/__init__.py` (`_cache: dict[str, LLMClient]`) guarantees an adapter is constructed at most once per provider per process. Logging inside `__init__` therefore satisfies "exactly once per loadable provider" without modifying `__init__.py`.
- Symmetric with Plan 03's edit to `AnthropicMGTIClient.__init__` — both adapters log on first construction, both satisfy SC #5 with a uniform pattern.
- Phase 2's acceptance gate does NOT assert log absence — it captures `llm_call` events only. Adding a separate `llm_provider_loaded` event does not break any existing test.

**Current __init__** (azure_openai.py:76-84, Phase 2 locked):
```python
def __init__(self) -> None:
    # No-op pattern preserved from Phase 1: construction must NOT raise so
    # the factory cache can store the instance. Missing config is caught at
    # HTTP time in complete() with provider-specific remediation text.
    settings = load_settings()
    self._endpoint: str = settings.azure_endpoint
    self._api_key: str = settings.azure_api_key
    self._api_version: str = settings.azure_api_version
    self._model: str = _extract_model_from_endpoint(self._endpoint)
```

**New __init__** (single 4-line addition at the end of the existing body — do NOT reorder or reword existing lines):
```python
def __init__(self) -> None:
    # No-op pattern preserved from Phase 1: construction must NOT raise so
    # the factory cache can store the instance. Missing config is caught at
    # HTTP time in complete() with provider-specific remediation text.
    settings = load_settings()
    self._endpoint: str = settings.azure_endpoint
    self._api_key: str = settings.azure_api_key
    self._api_version: str = settings.azure_api_version
    self._model: str = _extract_model_from_endpoint(self._endpoint)

    # SC #5: log the configured base URL once per loadable provider. The
    # factory cache (src/llm/__init__.py _cache dict) ensures __init__ runs
    # at most once per provider per process — so this emits exactly one
    # llm_provider_loaded event per provider, even if get_llm() is called
    # repeatedly. Symmetric with AnthropicMGTIClient.__init__ (Phase 3 Plan 03).
    logger.info(
        "llm_provider_loaded",
        extra={"provider": "azure_openai", "base_url": self._endpoint},
    )
```

Notes:
- `logger` is already imported at the top of the file (`from src.utils import logger`) — no new import needed.
- The log message tag `"llm_provider_loaded"` is distinct from `"llm_call"` so existing log handlers / dashboards do not confuse the two.
- The `extra` dict has exactly two fields: `provider` (string, fixed value `"azure_openai"`) and `base_url` (string, from `settings.azure_endpoint` — may be empty if the user has not configured Azure; that is acceptable, the log line still fires with `base_url=""`, which is information the operator wants to see).
- `extra` uses raw key names (`provider`, `base_url`) NOT the `llm_*` prefix used by `_log_llm_call`. These are different event types; cross-contamination of field names would make filtering ambiguous. (Reviewer cross-check: the Plan 04 acceptance test asserts `ev.provider == "azure_openai"` and `ev.base_url == _DUMMY_ENDPOINT`, not `ev.llm_provider`.)
- The log line is emitted UNCONDITIONALLY — even if `self._endpoint` is empty. The operator wants to know "I tried to load azure_openai and got base_url='' " just as much as "...got base_url='https://...'".

LOCKED — do NOT change in this task:
- `_extract_model_from_endpoint` (helper function, lines ~35-49)
- `_log_llm_call` (helper function, lines ~52-64)
- `__repr__` (lines ~86-88) — Phase 1's `test_no_api_keys_in_repr` still asserts this returns `"AzureOpenAIClient()"`.
- `complete` (lines ~90-212) — Phase 2 parity tests depend on byte-exact behavior.
- `classify_with_tool` (lines ~214-285) — same reason.
- Module docstring and imports.
  </action>
  <verify>
Run from project root:

```
python -c "
import os
# Strip Azure env to confirm log still fires with empty base_url (SC #5 requires logging even when config is missing — the OPERATOR wants to see this).
for k in ('AZURE_OPENAI_API_KEY','AZURE_OPENAI_ENDPOINT','API_VERSION'):
    os.environ.pop(k, None)

import logging
captured = []
class _H(logging.Handler):
    def emit(self, record):
        captured.append(record)

import src.utils as u
u.logger.addHandler(_H())

# Construct fresh — should fire llm_provider_loaded exactly once.
from src.llm.azure_openai import AzureOpenAIClient
client = AzureOpenAIClient()

# Construct AGAIN directly — no cache here, so it fires AGAIN. This confirms
# the log lives in __init__ (the cache idempotence is provided by get_llm(),
# not by the adapter itself).
client2 = AzureOpenAIClient()

events = [r for r in captured if r.getMessage() == 'llm_provider_loaded']
assert len(events) == 2, f'expected 2 events from 2 constructions, got {len(events)}'

# Both events MUST have provider + base_url fields with correct types/values.
for ev in events:
    assert ev.provider == 'azure_openai', f'unexpected provider: {ev.provider!r}'
    assert ev.base_url == '', f'expected empty base_url (no env), got {ev.base_url!r}'

# Now exercise the cache idempotence path — get_llm() must produce exactly ONE
# llm_provider_loaded event even if called twice.
import src.llm as llm_pkg
llm_pkg._cache.clear()
captured.clear()

from src.llm import get_llm
c1 = get_llm('azure_openai')
c2 = get_llm('azure_openai')
assert c1 is c2, 'factory cache not idempotent — c1 is not c2'
events2 = [r for r in captured if r.getMessage() == 'llm_provider_loaded']
assert len(events2) == 1, f'expected 1 event for 2 get_llm() calls (cache should dedupe), got {len(events2)}'
assert events2[0].provider == 'azure_openai'

# Confirm __repr__ override still works (Phase 1 OBS-03 guard)
assert repr(client) == 'AzureOpenAIClient()', f'__repr__ regressed: {repr(client)!r}'

print('TASK 2 OK')
"
```

Must print `TASK 2 OK`. Then run the FULL Phase 2 acceptance gate to confirm zero regression:

```
python -m pytest tests/test_phase2_parity.py tests/test_llm_seam.py -v
```

Expected: 18 tests pass (6 Phase 1 + 12 Phase 2). If any test fails, the `__init__` edit broke a locked invariant — revert and rework.
  </verify>
  <done>
- `AzureOpenAIClient.__init__` emits exactly one `logger.info("llm_provider_loaded", extra={"provider": "azure_openai", "base_url": <endpoint>})` event per construction.
- The factory cache (`src/llm/__init__.py _cache`) ensures `__init__` runs at most once per provider per process, so `get_llm("azure_openai")` called N times produces exactly ONE `llm_provider_loaded` event.
- The event has TWO extra fields: `provider` (string, value `"azure_openai"`) and `base_url` (string, from `settings.azure_endpoint`).
- Event tag is `"llm_provider_loaded"` (distinct from `"llm_call"`).
- All Phase 2 / Phase 1 tests (18 total) still pass.
- LOCKED methods (`__repr__`, `complete`, `classify_with_tool`, helpers) are byte-identical to Phase 2 — `git diff src/llm/azure_openai.py` shows changes ONLY inside `__init__`.
- Satisfies SC #5 for the Azure half ("App startup logs the configured base URL for each loadable provider exactly once"). The Anthropic half is delivered in Plan 03.
  </done>
</task>

</tasks>

<verification>
End-of-plan verification:

```
# 1. .env.example contains all 9 new variables with documented defaults (Task 1)
python -c "
content = open('.env.example').read()
for var in ('LLM_PROVIDER_DEFAULT','ANTHROPIC_BASE_URL','ANTHROPIC_API_KEY','ANTHROPIC_MODEL','ANTHROPIC_VERSION','ANTHROPIC_MAX_TOKENS','ANTHROPIC_TEMPERATURE','ANTHROPIC_TIMEOUT_S','ANTHROPIC_TOOLS_SUPPORTED'):
    assert f'{var}=' in content
print('env.example: 9 vars present')
"

# 2. azure_openai.py contains exactly the new log line, all other Phase 2 code intact (Task 2)
grep -n "llm_provider_loaded" src/llm/azure_openai.py
grep -n "def __init__\|def __repr__\|def complete\|def classify_with_tool" src/llm/azure_openai.py

# 3. Phase 1 + Phase 2 acceptance gates both still green (18 tests)
python -m pytest tests/test_llm_seam.py tests/test_phase2_parity.py -v
```

The third command MUST show 18 passing. If anything fails, this plan introduced a regression — revert the `__init__` edit and re-do.

Files this plan MUST NOT touch (verify diff is empty):
```
git diff --name-only HEAD src/llm/__init__.py src/llm/_compat.py src/llm/config.py src/llm/anthropic_mgti.py src/llm/base.py src/llm/errors.py src/llm/types.py src/query_router.py src/sql_generator.py app.py config.py tests/ 2>&1 | head
```

Must produce no output. This plan's surface is exactly TWO files: `.env.example` and `src/llm/azure_openai.py` (the `__init__` block only).
</verification>

<success_criteria>
- `.env.example` contains all 9 Phase 3 variables as `NAME=value` assignments with documented defaults; defaults match `LLMSettings` for the optional vars; existing Phase 2 lines preserved (SC #4 — fully satisfied for `.env.example` shape; Plan 04 acceptance test grep-confirms).
- `AzureOpenAIClient.__init__` emits one `llm_provider_loaded` event at construction with `extra={"provider": "azure_openai", "base_url": <endpoint>}`; factory cache idempotence guarantees at-most-once per process (SC #5 — Azure half).
- Phase 1 + Phase 2 tests (18 total) still pass.
- Files modified: exactly `.env.example` and `src/llm/azure_openai.py`. No other source file touched.

Maps to: SC #4 (full — `.env.example` shape; the assertion test is owned by Plan 04). SC #5 (half — Azure adapter logs; the Anthropic half lands in Plan 03; the assertion test is owned by Plan 04). Requirements: CFG-02, CFG-04, OBS-01, OBS-04.
</success_criteria>

<output>
After completion, create `.planning/phases/03-anthropic-mgti-adapter/03-01-SUMMARY.md` documenting:
- Total line count of `.env.example` before vs after; list of the 9 newly added `NAME=value` pairs.
- `AzureOpenAIClient.__init__` diff: a 4-6 line snippet showing the added `logger.info("llm_provider_loaded", ...)` call inside `__init__`.
- Confirmation that Phase 1 + Phase 2 tests (18 total) still pass — paste the pytest summary line (`==== N passed in Xs ====`).
- Confirmation that LOCKED Phase 2 code (`__repr__`, `complete`, `classify_with_tool`, `_log_llm_call`, `_extract_model_from_endpoint`) is byte-identical to HEAD — paste `git diff src/llm/azure_openai.py` showing only the `__init__` block change.
- Confirmation that this plan modified ONLY `.env.example` + `src/llm/azure_openai.py` — paste `git diff --name-only HEAD` output.
- A one-line note that SC #4 is now wholly satisfied at the file level (Plan 04's pytest assertion will confirm) and SC #5 is half-satisfied (Plan 03 delivers the Anthropic half).
</output>
