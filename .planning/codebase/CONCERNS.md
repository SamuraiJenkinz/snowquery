# Concerns

**Analysis Date:** 2026-05-19

Technical debt, fragility, and risk areas in the codebase. Cited with `file:line` where applicable.

## 🚨 Critical

### Multi-app sprawl — four parallel entry points

Four Streamlit apps coexist with overlapping purpose and unclear authority:

- `app.py` — committed, likely the canonical entry point
- `app_brutalist.py` — **untracked** in git (per `git status`)
- `fixedapp.py` — **untracked** in git
- `designui.py` — **untracked** in git

**Why it's a concern:**
- No README authority — unclear which app a new user should run
- Changes to shared `src/` modules can break any of them silently
- The untracked apps may contain in-progress work or abandoned experiments
- Git history shows `Revert to stable version from 3 days ago` twice (`8877128`, `df545e7`) — suggests churn on the UI surface

**Recommendation:** Decide which app is canonical. Either delete the others, or move them to an `experiments/` folder and commit/git-ignore explicitly.

### Untracked changes in working tree

`git status` shows many untracked files at the project root, including code (`app_brutalist.py`, `designui.py`, `fixedapp.py`, `deploy/build_python_311.ps1`), docs (`TECHFEST_*.md`, `docs/`), and binary/image assets (`cur.jpg`, `lar.jpg`, `mo.jpg`, `FestT.pdf`, `FirstRun.pdf`, `Marsh Brasil - Health Intelligence Report.html`, `CTMSG MOQ Messaging.xlsx`, `nul`).

**Why it's a concern:**
- Mixing committed code with untracked working copies makes "what's deployed" ambiguous
- The `nul` file is a Windows artifact (likely from `command > nul`) — should be deleted
- Binary assets without LFS will inflate the repo when committed

**Recommendation:** Triage. Anything intentionally untracked → add to `.gitignore`. Anything intended → commit. Delete `nul`.

## ⚠️ Security

### LLM-driven SQL with regex-only validation (`src/sql_generator.py`)

The system prompt instructs Azure OpenAI to "Only generate SELECT statements — never UPDATE, DELETE, INSERT, DROP" (`src/sql_generator.py:38`), but enforcement relies on prompt obedience plus a downstream check. An adversarial user input (prompt injection through the natural-language query) could try to subvert this.

**Why it's a concern:**
- Prompt injection is a known LLM risk class — "ignore previous instructions" attacks are well-documented
- Even with a downstream `SELECT`-only regex, edge cases exist (stacked statements, comments, CTEs that wrap mutating CALLs, DuckDB-specific syntax like `COPY ... TO`)
- DuckDB allows `INSTALL`/`LOAD extension` and `COPY TO 'file'` which can read/write the local filesystem

**Recommendation:** Validate the generated SQL with a real parser (e.g., `sqlglot.parse`, walk the AST, reject non-SELECT roots). Additionally, run the DuckDB connection in read-only mode for query execution (`duckdb.connect(path, read_only=True)`).

### Recent CVE-driven dependency pins

`requirements.txt` documents three CVEs requiring patched versions:
- `torch>=2.6.0` — CVE-2025-32434 (RCE via `torch.load()`)
- `transformers>=4.51.0` — CVE-2025-14927, CVE-2025-14924 (code injection via checkpoint files)

**Status:** Pinned and addressed (commit `e8594b8`). Good. Keep watching for further advisories in this dependency chain.

### CSV upload protection

Recent commit `46f2cef`: "add password protection to CSV file upload". This suggests the app accepts arbitrary user-uploaded CSVs and previously did so without auth.

**Why it's still a concern:**
- Password-protection at upload doesn't prevent malicious CSV content (formula injection if results are exported to Excel, encoding-based attacks on the parser)
- Where is the password stored? If hardcoded or env-var compared in plaintext, it's a soft control
- Quality mapper noted "CSV encoding fallbacks" as untested — a malformed CSV could throw in pandas with sensitive data in the error

**Recommendation:** Audit how the password is stored/checked. Add CSV size limits, content-type checks, and a parse-error path that doesn't leak file content.

### Azure OpenAI credentials in environment

API key lives in `.env` (per `STACK.md`). This is standard, but:
- No detection of accidental commit (no `git-secrets` or pre-commit hook visible)
- `python-certifi-win32` suggests deployment behind a corporate proxy — credentials may end up in proxy logs

**Recommendation:** Add a pre-commit hook to scan for `AZURE_OPENAI_API_KEY=` patterns. Document key rotation procedure.

## 🐛 Fragility

### No tests at all

See `TESTING.md`. Recent history shows two reverts in 8 commits — the regression-detection mechanism is human eyeballs. Any non-trivial refactor of `src/query_router.py` or `src/sql_generator.py` is high-risk without a safety net.

### `__pycache__` and other generated artifacts may be tracked

Worth verifying `.gitignore` excludes `__pycache__/`, `.pyc`, `db/`, `data/`, `.env`, model caches (`~/.cache/huggingface/`).

### Model download on first run

`sentence-transformers` downloads `all-MiniLM-L6-v2` on first use (~80MB). On a corporate network or air-gapped environment this can fail silently or hang. No pre-flight check is visible.

**Recommendation:** Add a startup check: model exists locally → proceed; missing → clear error + download progress, not a Streamlit crash.

### Single `incidents` table assumed

`src/sql_generator.py:31` hard-codes `"Table name is 'incidents'"` in the system prompt. Schema changes or multi-table support require prompt edits in addition to code changes.

## 🐢 Performance

### Synchronous LLM calls on UI thread

Streamlit's execution model runs the script top-to-bottom on each interaction. Azure OpenAI calls in `query_router.py` and `sql_generator.py` are made via `requests` (sync). For each user query, the UI blocks until the API responds (typical 1-5s; longer on cold paths). 

**Mitigation already present:** None visible. `st.spinner()` likely used but doesn't prevent thread blocking.

**Recommendation:** Acceptable for low-concurrency demo use. Document as a limitation. If scaled, move to async + a worker.

### torch + transformers cold start

These libraries take 5-15 seconds to import. Every Streamlit script rerun re-evaluates imports. `@st.cache_resource` should be used aggressively for model loading — confirm it is (not verified in this pass).

### ChromaDB persistence on local disk

`db/chroma` is file-based. Fine for single-user, but multiple Streamlit sessions hitting the same files can hit lock contention.

## 📦 Operational

### No `pyproject.toml` or lockfile

`requirements.txt` uses `>=` pins (e.g., `streamlit>=1.40.0`). This means a fresh `pip install` on a different day can produce a different working set. For a tool destined for any kind of repeatable deploy, add a lockfile (`pip-tools`, `uv lock`, or `poetry lock`).

### `deploy/build_python_311.ps1` is untracked

A deploy script that's not in version control is a deploy script that doesn't exist. Commit it or delete it.

### `BUILD_PYTHON_FROM_SOURCE.md` suggests an air-gapped or restricted environment

Untracked file `deploy/BUILD_PYTHON_FROM_SOURCE.md` implies a corporate/restricted target environment (likely Marsh given `Marsh Brasil - Health Intelligence Report.html` artifact in working tree). This is important context for any future deploy/install work — should be documented in the project README.

## TODOs Found in Code

`grep TODO|FIXME|HACK|XXX` across all `.py` files returned **no matches**. Either the code is exceptionally clean of inline debt markers, or implicit debt is hidden in comments without standard keywords.

---

*Concerns analysis: 2026-05-19 — written by orchestrator after concerns mapper sandbox-write failure.*
