---
phase: 5
plan: 4
name: readme-and-user-guide
type: execute
wave: 2
depends_on: []
files_modified:
  - README.md
  - USER_GUIDE.md
autonomous: true

must_haves:
  truths:
    - "README.md is updated with: tech-stack table mention of multi-provider LLM, full env-var rows for the new Anthropic + LLM_PROVIDER_DEFAULT vars, a short LLM Provider Selection subsection cross-linking USER_GUIDE, a Smoke Test subsection (when + how to run scripts/smoke_llm.py), and an MGTI/Hubble onboarding pointer"
    - "USER_GUIDE.md gains a new §9 'LLM Provider Selection' between the existing §8 Settings and the existing §9 (renumbered to §10): overview, MGTI-only constraint, how-to-switch numbered steps, per-message caption explanation, warning-resolution table, first-time-Anthropic 4-step setup checklist, mid-session switching note"
    - "Both docs quote the EXACT UI strings: selectbox label 'LLM provider', options 'Azure OpenAI' / 'Anthropic Claude (MGTI)', placeholder 'QUERY DISABLED — see sidebar warning', caption format 'via **<Provider>** · `<model>`' — RESEARCH.md Pitfall 13 (docs drift) guard"
    - "USER_GUIDE.md TOC reflects the new section number; the existing version-stamp footer is bumped to a new v2.1 entry mentioning multi-provider LLM"
    - "NO screenshots embedded — both docs preserve their existing image-free convention"
    - "DOC-01, DOC-02, DOC-03, DOC-04 requirement coverage is satisfied"
  artifacts:
    - path: "README.md"
      provides: "Setup-audience updates: env-var table, provider-selection subsection, smoke-test subsection, MGTI/Hubble pointer"
      contains: "LLM Provider Selection"
    - path: "USER_GUIDE.md"
      provides: "Use-audience walkthrough: full §9 LLM Provider Selection section with overview, MGTI constraint, how-to, caption explanation, warning table, first-time checklist, mid-session behavior, version stamp bump"
      contains: "LLM Provider Selection"
  key_links:
    - from: "README.md"
      to: "USER_GUIDE.md §LLM Provider Selection"
      via: "explicit cross-link in the new short subsection"
      pattern: "USER_GUIDE\\.md"
    - from: "USER_GUIDE.md warning-resolution table"
      to: "src/llm/config.py::_REQUIRED_VARS"
      via: "table rows enumerate ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, AZURE_OPENAI_* — matching the _REQUIRED_VARS dict"
      pattern: "ANTHROPIC_BASE_URL.*ANTHROPIC_API_KEY.*ANTHROPIC_MODEL"
    - from: "Both docs"
      to: "scripts/smoke_llm.py"
      via: "documented invocation: 'python scripts/smoke_llm.py --provider both --verbose'"
      pattern: "smoke_llm\\.py"
---

<objective>
Update `README.md` (deploy/setup audience) and `USER_GUIDE.md` (in-app use audience) with the Phase 5 multi-provider feature documentation. README gains an env-var table row block for the new variables, a short cross-link subsection pointing at USER_GUIDE for day-to-day use, a Smoke Test subsection (when + how), and an MGTI/Hubble onboarding pointer. USER_GUIDE gains a full new §9 covering the overview, MGTI-only constraint, how-to-switch steps, per-message caption meaning, a warning-resolution table, a first-time-Anthropic setup checklist, and mid-session switching behavior, plus a version-stamp footer bump.

Purpose: This is SC #5 — "README and USER_GUIDE explain provider selection, the MGTI-only constraint, how to run `scripts/smoke_llm.py`, and what to do when a provider warning appears." Requirements DOC-01 through DOC-04 land here. The two docs maintain their existing split (README = how to install + configure; USER_GUIDE = how to use day-to-day) — this plan honors that convention rather than duplicating content. Both docs quote the exact UI strings from Plan 05-02 to lock against future docs-drift (RESEARCH Pitfall 13).

Output: Two files modified (`README.md`, `USER_GUIDE.md`); no other surface touched. Plan runs in parallel with Plan 05-02 and Plan 05-03 (Wave 2) — independent of code changes because docs land "in advance" of operator review and the UI strings are non-discretionary.
</objective>

<execution_context>
@C:\Users\taylo\.claude/get-shit-done/workflows/execute-plan.md
@C:\Users\taylo\.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-CONTEXT.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-RESEARCH.md

# Files modified
@README.md
@USER_GUIDE.md

# Reference: .env.example already lists the Phase 3 variables — pull the variable
# names and defaults from there verbatim
@.env.example

# Reference: scripts/smoke_llm.py for invocation details
@scripts/smoke_llm.py
</context>

<decisions>
## Decisions locked for this plan

1. **Doc split (RESEARCH Recommendation 4 verbatim):** README covers SETUP (env vars, MGTI/Hubble pointer, smoke-test when+how, one-line cross-link to USER_GUIDE). USER_GUIDE covers USE (overview, switching, captions, warnings, first-time checklist, mid-session behavior). NO content duplicated between docs — one cross-link from README to USER_GUIDE.

2. **EXACT UI strings to lock in both docs (RESEARCH Pitfall 13):**
   - Selectbox label: `LLM provider` — appears in USER_GUIDE's "how to switch" steps.
   - Provider options: `Azure OpenAI` and `Anthropic Claude (MGTI)` — appear in both docs.
   - Caption format: `via **Azure OpenAI** · \`<model-name>\`` (or with Anthropic) — appear in USER_GUIDE's caption explanation.
   - Blocked-input placeholder: `QUERY DISABLED — see sidebar warning` — appears in USER_GUIDE warning section.
   - Sidebar section header: `LLM PROVIDER` (uppercase) — appears in USER_GUIDE "how to switch" steps.
   - Warning text fragment: `is not configured. Missing env vars:` — appears in the warning-resolution table.

3. **README env-var table additions** (DOC-01, CFG-02 docs landing): Find the existing "Environment Variables" section / table. Append rows for:
   - `LLM_PROVIDER_DEFAULT` — Description: "Default LLM provider when no session selection has been made. Options: `azure_openai`, `anthropic_mgti`." Default: `azure_openai`. Required: NO.
   - `ANTHROPIC_BASE_URL` — Description: "MGTI Apigee gateway base URL (e.g. `https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1`)." Default: (none). Required: YES for Anthropic.
   - `ANTHROPIC_API_KEY` — Description: "MGTI API key (issued via Hubble — see below)." Default: (none). Required: YES for Anthropic.
   - `ANTHROPIC_MODEL` — Description: "Claude model identifier; MUST start with `eu.anthropic.claude-` (Claude 4.5+ on EU Bedrock region)." Default: (none). Required: YES for Anthropic.
   - Optional Anthropic vars summary row: "`ANTHROPIC_VERSION` / `ANTHROPIC_MAX_TOKENS` / `ANTHROPIC_TEMPERATURE` / `ANTHROPIC_TIMEOUT_S` / `ANTHROPIC_TOOLS_SUPPORTED` — Optional tuning vars; see `.env.example` for defaults." Required: NO.

   Match the existing table format (column headers, alignment). If the existing format is bullets-with-bold (not a table), match THAT — read README.md before writing to confirm.

4. **README "LLM Provider Selection" subsection** — keep it short (≤ 8 lines body), placed AFTER the env-var section and BEFORE the Data Privacy section (so it reads in setup order: install → config → providers → privacy). Content:
   ```markdown
   ### LLM Provider Selection

   This app supports two LLM backends — Azure OpenAI (default) and Anthropic Claude via the MGTI Apigee gateway. The active provider is chosen from the sidebar `LLM PROVIDER` block in the Streamlit UI; the default is `azure_openai` so existing deployments behave identically until an operator opts in.

   For day-to-day switching, what the per-message caption means, and how to resolve provider warnings, see **USER_GUIDE.md § LLM Provider Selection**.
   ```

5. **README "Smoke Test" subsection** — placed after "LLM Provider Selection" subsection. Content (≤ 12 lines):
   ```markdown
   ### Smoke Test (operator-run)

   `scripts/smoke_llm.py` exercises both providers end-to-end against live credentials. Run after any `.env` change to the Anthropic or Azure vars, and before every production deploy.

   ```bash
   # Default — test both providers (skips unconfigured ones)
   python scripts/smoke_llm.py --provider both --verbose

   # Diagnose Anthropic only (FAILs on missing creds rather than SKIPping)
   python scripts/smoke_llm.py --provider anthropic_mgti --verbose

   # Azure only
   python scripts/smoke_llm.py --provider azure_openai --verbose
   ```

   Exit codes: `0` = all configured providers passed; `1` = at least one configured provider failed. The script does NOT run in CI — it uses live credentials and is operator-only.
   ```

6. **README MGTI/Hubble onboarding pointer** (DOC-03): one-line note placed inside or directly after the Anthropic env-var rows. Wording:
   > Anthropic access is restricted to MGTI-enrolled users; request credentials via **Hubble** (https://hubble.mmc.com/apps) after the coreapi-infrastructure onboarding step.

   (If the existing README has a different style for external links, match it.)

7. **USER_GUIDE TOC update** — locate the existing Table of Contents. Find §8 Settings (or whatever section §8 currently is) and §9 (current title). Insert a new entry between them:
   - New §9: "LLM Provider Selection"
   - Renumber subsequent sections — every section currently numbered ≥9 gets +1. If the TOC uses bullet/anchor links, update those too.

   Read USER_GUIDE.md before writing to confirm current section numbers. The roadmap's "between Settings and Tips & Best Practices" is the researcher's read of the doc — confirm by reading the actual file.

8. **USER_GUIDE §9 LLM Provider Selection body** (DOC-02, DOC-03, DOC-04). Approximate length: 60–90 lines. Sub-sections in order:

   **§9.1 Overview** (3-5 lines)
   - What the toggle does (lets you choose Azure OpenAI vs Anthropic Claude per session).
   - Where to find it (sidebar `LLM PROVIDER` block, between EMBEDDINGS and CONFIG).
   - Default behavior (Azure OpenAI; existing deployments unchanged).
   - Why you'd switch (model evaluation, Claude 4.5+ comparison).

   **§9.2 MGTI-Only Constraint for Anthropic** (one paragraph, DOC-03)
   - Anthropic credentials are issued only to MGTI-enrolled users via Hubble.
   - Link: https://hubble.mmc.com/apps
   - Explicit guidance: if you don't have credentials, stay on Azure OpenAI; the app will warn you and disable submission if you select Anthropic without creds.

   **§9.3 How to Switch Providers** (numbered 5-step list, DOC-02)
   1. Locate the **`LLM PROVIDER`** block in the sidebar (between `EMBEDDINGS` and `CONFIG`).
   2. Open the **`LLM provider`** dropdown and choose either `Azure OpenAI` or `Anthropic Claude (MGTI)`.
   3. Confirm the **`MODEL:`** caption beneath the dropdown updates to the new provider's model identifier.
   4. Send a query as usual. The next response will be produced by the new provider.
   5. Look for the `via **<Provider>** · \`<model>\`` caption above the assistant's reply.

   **§9.4 What the Per-Message Caption Means** (one paragraph, SC #4 + DOC-02)
   - Every assistant response carries a small caption naming the provider and model that produced it.
   - Caption format: `via **Azure OpenAI** · \`gpt-4o-mini\`` (Azure example) or `via **Anthropic Claude (MGTI)** · \`eu.anthropic.claude-sonnet-4-5-20250929-v1:0\`` (Anthropic example).
   - Historical messages KEEP their original provenance after a provider switch — captions reflect the provider that originally produced the message, not the currently selected one.

   **§9.5 What to Do When a Provider Warning Appears** (table, DOC-02 + DOC-04 partial). Match USER_GUIDE's existing table style. Rows:
   | Warning text mentions | Cause | Fix |
   |-----------------------|-------|-----|
   | `ANTHROPIC_BASE_URL` | Anthropic proxy URL not set | Add `ANTHROPIC_BASE_URL` to `.env`; restart Streamlit |
   | `ANTHROPIC_API_KEY` | Anthropic API key not set or empty | Request via Hubble; add to `.env`; restart Streamlit |
   | `ANTHROPIC_MODEL` | Claude model identifier not set | Set e.g. `ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-4-5-20250929-v1:0` |
   | `AZURE_OPENAI_ENDPOINT` | Azure endpoint URL not set | Add `AZURE_OPENAI_ENDPOINT` to `.env`; restart Streamlit |
   | `AZURE_OPENAI_API_KEY` | Azure API key not set or empty | Add `AZURE_OPENAI_API_KEY` to `.env`; restart Streamlit |

   When any warning is active, the chat input shows `QUERY DISABLED — see sidebar warning` and submission is blocked. Switching back to a properly-configured provider in the sidebar restores the chat input immediately on the next rerun.

   **§9.6 First-Time Anthropic Setup Checklist** (numbered 4-step list, DOC-04). Place INSIDE §9 (not as a separate section):
   1. **Obtain MGTI access via Hubble.** Visit https://hubble.mmc.com/apps and complete the coreapi-infrastructure onboarding to receive your `ANTHROPIC_API_KEY`.
   2. **Populate `.env`** with the three required Anthropic variables: `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`. See `.env.example` for the template and defaults.
   3. **Run the smoke test:** `python scripts/smoke_llm.py --provider anthropic_mgti --verbose`. Confirm `Exit: 0`. If it fails, the script prints the specific failing check — fix the env or contact MGTI before proceeding.
   4. **Restart Streamlit**, switch the sidebar selector to `Anthropic Claude (MGTI)`, send a test query, and confirm the per-message caption shows the Anthropic model.

   **§9.7 Mid-Session Switching Behavior** (one short paragraph, SC #2)
   - Switches take effect on the **next query only**.
   - In-flight queries finish on the previously selected provider (Streamlit's synchronous execution model means the switch cannot interleave with an in-flight call).
   - Historical messages retain their original provider's caption — switching does NOT re-render historical provenance.

9. **USER_GUIDE version-stamp bump** (RESEARCH Recommendation 4 / current line ~378): the existing footer reads approximately:
   > Last updated: December 2024 (v2.0 - Added password protection & chart visualization)

   Replace with:
   > Last updated: May 2026 (v2.1 - Added multi-provider LLM selection: Azure OpenAI / Anthropic Claude via MGTI)

   (Use today's date; preserve the parenthetical-versioning style.)

10. **No screenshots in either doc.** RESEARCH Recommendation 4 + the existing image-free convention.

11. **No changes to .env.example** — it was already populated in Phase 3. If reading reveals a missing var (e.g. `LLM_PROVIDER_DEFAULT` is somehow absent), STOP and report — that would be a Phase 3 regression, not in Plan 05-04's scope.

12. **No changes to ROADMAP.md or REQUIREMENTS.md from this plan** — those are updated by the orchestrator at the close of Phase 5.

13. **No changes to other docs** (e.g. CHANGELOG.md if present) — out of scope. If a CHANGELOG exists and convention demands an entry, leave a TODO comment in the SUMMARY for follow-up rather than editing here.
</decisions>

<tasks>

<task type="auto">
  <name>Task 4.1: README.md updates — env-var rows, LLM Provider Selection subsection, Smoke Test subsection, MGTI/Hubble pointer</name>
  <files>README.md</files>
  <action>
**Step 1 — Read `README.md` end-to-end.** Note current structure: section headers, env-var table/list format, where the Data Privacy section starts. Match the existing style for each new addition.

**Step 2 — Tech-Stack table update (DOC-01 high-level mention).** If the README has a "Tech Stack" table or list, find the line mentioning "Azure OpenAI" as the LLM. Replace with something like:

> **Azure OpenAI or Anthropic Claude (via MGTI Apigee gateway)** — Query routing, SQL generation, executive summaries; selectable per session in the sidebar (default: Azure OpenAI).

If there is NO tech-stack mention of the LLM, skip this step — but verify with grep before declaring skipped.

**Step 3 — Environment Variables additions.** Find the existing env-var section. Match its format (table with `| Variable | Description | Default | Required |` columns OR a bulleted list with bold variable names — whichever is used). Append the following rows AFTER the existing Azure-related rows:

```
| `LLM_PROVIDER_DEFAULT` | Default LLM provider for new sessions. Options: `azure_openai`, `anthropic_mgti` | `azure_openai` | No |
| `ANTHROPIC_BASE_URL`   | MGTI Apigee gateway base URL (e.g. `https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1`) | — | Yes (for Anthropic) |
| `ANTHROPIC_API_KEY`    | MGTI API key (issued via Hubble — see below) | — | Yes (for Anthropic) |
| `ANTHROPIC_MODEL`      | Claude model identifier; MUST start with `eu.anthropic.claude-` (Claude 4.5+, EU Bedrock) | — | Yes (for Anthropic) |
| `ANTHROPIC_VERSION` / `ANTHROPIC_MAX_TOKENS` / `ANTHROPIC_TEMPERATURE` / `ANTHROPIC_TIMEOUT_S` / `ANTHROPIC_TOOLS_SUPPORTED` | Optional tuning vars — see `.env.example` for defaults | (defaults vary) | No |
```

(Adapt the format if README uses bullets-with-bold instead of a table. The CONTENT is what matters; the FORMAT must match the existing convention.)

**Step 4 — MGTI/Hubble pointer.** Immediately AFTER the env-var table/list, add one paragraph:

> **MGTI onboarding (Anthropic only):** Anthropic access is restricted to MGTI-enrolled users; request credentials via **Hubble** at https://hubble.mmc.com/apps after the coreapi-infrastructure onboarding step. Without an MGTI-issued `ANTHROPIC_API_KEY`, stay on the Azure OpenAI default.

**Step 5 — New "LLM Provider Selection" subsection.** Place AFTER the env-var section + MGTI pointer (so the reading order is install → env config → provider choice → smoke test → privacy). Content per locked decision §4:

```markdown
### LLM Provider Selection

This app supports two LLM backends — Azure OpenAI (default) and Anthropic Claude via the MGTI Apigee gateway. The active provider is chosen from the sidebar `LLM PROVIDER` block in the Streamlit UI; the default is `azure_openai` so existing deployments behave identically until an operator opts in.

Switching providers takes effect on the next query (no retroactive recompute). Each assistant message displays a small caption naming the provider and model that produced it.

For day-to-day switching, what the per-message caption means, and how to resolve provider warnings, see **USER_GUIDE.md § LLM Provider Selection**.
```

**Step 6 — New "Smoke Test" subsection.** Place AFTER "LLM Provider Selection" and BEFORE Data Privacy. Content per locked decision §5:

````markdown
### Smoke Test (operator-run)

`scripts/smoke_llm.py` exercises both providers end-to-end against live credentials. Run after any `.env` change to the Anthropic or Azure vars, and before every production deploy.

```bash
# Default — test both providers (skips unconfigured ones)
python scripts/smoke_llm.py --provider both --verbose

# Diagnose Anthropic only (FAILs on missing creds rather than SKIPping)
python scripts/smoke_llm.py --provider anthropic_mgti --verbose

# Azure only
python scripts/smoke_llm.py --provider azure_openai --verbose
```

Exit codes: `0` = all configured providers passed; `1` = at least one configured provider failed. The script does NOT run in CI — it uses live credentials and is operator-only.
````

**Step 7 — Verify nothing else in README has been disturbed.** Read the diff:

```bash
git diff README.md
```

Only the additions described above should appear. Do NOT reformat surrounding sections, do NOT touch the Quick Start or Project Structure sections.
  </action>
  <verify>
```bash
# Env vars present in README
for v in LLM_PROVIDER_DEFAULT ANTHROPIC_BASE_URL ANTHROPIC_API_KEY ANTHROPIC_MODEL; do
  grep -nE "\\\`${v}\\\`" README.md > /dev/null && echo "OK ${v}" || echo "MISSING ${v}"
done
# Expected: 4 OK lines

# MGTI / Hubble pointer present (DOC-03)
grep -nE "MGTI|Hubble|hubble\.mmc\.com" README.md
# Expected: ≥1 match each

# LLM Provider Selection subsection present
grep -nE "^### LLM Provider Selection" README.md
# Expected: 1 match

# Cross-link to USER_GUIDE
grep -nE "USER_GUIDE\.md" README.md
# Expected: ≥1 match (the cross-link in the new subsection)

# Smoke Test subsection present and references smoke_llm.py
grep -nE "^### Smoke Test" README.md
grep -nE "smoke_llm\.py" README.md
# Expected: 1 match for the header; ≥1 match for the script reference

# Sidebar label string locked in docs
grep -nE "LLM PROVIDER|LLM provider" README.md
# Expected: ≥1 match (the locked UI string)

# No unrelated edits
git diff README.md --stat
# Expected: ONE file changed; insertions only (or insertions + minor formatting tweaks)

# Suite still green (docs only — no code change)
pytest tests/ -v --tb=short
# Expected: 69 passed
```
  </verify>
  <done>
`README.md` has env-var rows for `LLM_PROVIDER_DEFAULT`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, and the optional-vars summary row. MGTI/Hubble pointer paragraph is present with the https://hubble.mmc.com/apps link. New `### LLM Provider Selection` subsection has a cross-link to `USER_GUIDE.md § LLM Provider Selection`. New `### Smoke Test (operator-run)` subsection documents `scripts/smoke_llm.py` invocation variants, exit codes, and the "operator-only, not CI" constraint. Existing sections (Features, Quick Start, Project Structure, Data Privacy) are untouched. 69-test suite still green.
  </done>
</task>

<task type="auto">
  <name>Task 4.2: USER_GUIDE.md updates — new §9 LLM Provider Selection (full body), TOC update, version-stamp bump</name>
  <files>USER_GUIDE.md</files>
  <action>
**Step 1 — Read `USER_GUIDE.md` end-to-end.** Note:
- Current TOC structure
- Current section numbers and titles
- Existing table style (column widths, header bolding, separator rune)
- Footer / version-stamp format
- Whether emojis appear in section headers

Match the existing style for ALL additions.

**Step 2 — Determine the exact insertion point.** The new section is `LLM Provider Selection`. Per RESEARCH.md it goes between "Settings" (~current §8) and "Tips & Best Practices" (~current §9). Confirm by reading the actual TOC and section headers. If the actual structure differs, the rule is: insert AFTER the "Settings" section and BEFORE the next section; renumber everything that follows.

**Step 3 — Update the Table of Contents.** Insert a new entry between current §8 and current §9. New entry:
- `9. LLM Provider Selection` (with anchor link if existing TOC uses them — `#9-llm-provider-selection` is the natural slug).
- Renumber all subsequent TOC entries: the current §9 becomes §10, §10 becomes §11, etc.

**Step 4 — Insert the new section body.** Place the entire section between current §8 (end) and current §9 (start, post-renumber to §10). Use the structure below — adapt heading levels and bullet styles to match the existing document conventions (`##`/`###` heading depth, table format, etc.):

```markdown
## 9. LLM Provider Selection

### Overview

This app supports two LLM backends, selectable per session in the sidebar:

- **Azure OpenAI** (default) — existing behavior, unchanged.
- **Anthropic Claude (MGTI)** — Claude 4.5+ via the MGTI Apigee gateway.

The active provider is chosen from the sidebar `LLM PROVIDER` block, positioned between `EMBEDDINGS` and `CONFIG`. The currently active model identifier is displayed beneath the dropdown as `MODEL: <model-name>`. Every assistant response is captioned with the provider that produced it.

### MGTI-Only Constraint for Anthropic

Anthropic access in this app is **restricted to MGTI-enrolled users**. Credentials (`ANTHROPIC_API_KEY`) are issued only via the **Hubble** onboarding portal at https://hubble.mmc.com/apps after the coreapi-infrastructure onboarding step. The app does NOT connect to `api.anthropic.com` directly — that endpoint is not authorized in the MMC corporate app context.

If you do not have MGTI credentials, **stay on Azure OpenAI**. Selecting `Anthropic Claude (MGTI)` without credentials will display an inline warning in the sidebar and disable query submission until you switch back or populate the missing variables.

### How to Switch Providers

1. Locate the **`LLM PROVIDER`** block in the sidebar (between `EMBEDDINGS` and `CONFIG`).
2. Open the **`LLM provider`** dropdown and choose either `Azure OpenAI` or `Anthropic Claude (MGTI)`.
3. Confirm the **`MODEL:`** caption beneath the dropdown updates to the new provider's model identifier.
4. Send a query as usual — the next response will be produced by the new provider.
5. Verify the `via **<Provider>** · \`<model>\`` caption above the assistant's reply names the expected provider.

The switch takes effect on the **next query only** — in-flight queries finish on the previously selected provider, and historical messages keep their original provenance caption.

### What the Per-Message Caption Means

Every assistant response carries a small caption naming the provider and model that produced it. Format:

- Azure example: `via **Azure OpenAI** · \`gpt-4o-mini\``
- Anthropic example: `via **Anthropic Claude (MGTI)** · \`eu.anthropic.claude-sonnet-4-5-20250929-v1:0\``

Captions are written at response time and **never recomputed** — if you switch providers, historical messages keep their original captions. This is intentional: the caption reflects which provider actually produced that specific message, not which provider is currently selected.

### What to Do When a Provider Warning Appears

If you select a provider whose required environment variables are missing, the sidebar shows an orange warning naming each missing variable, and the chat input is disabled with the placeholder `QUERY DISABLED — see sidebar warning`. Use the table below to resolve.

| Warning text mentions  | Cause                                | Fix                                                                                          |
|------------------------|--------------------------------------|----------------------------------------------------------------------------------------------|
| `ANTHROPIC_BASE_URL`   | Anthropic proxy URL not set          | Add `ANTHROPIC_BASE_URL` to `.env`; restart Streamlit                                        |
| `ANTHROPIC_API_KEY`    | Anthropic API key not set or empty   | Request via Hubble; add `ANTHROPIC_API_KEY` to `.env`; restart Streamlit                     |
| `ANTHROPIC_MODEL`      | Claude model identifier not set      | Set e.g. `ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-4-5-20250929-v1:0` in `.env`; restart    |
| `AZURE_OPENAI_ENDPOINT`| Azure endpoint URL not set           | Add `AZURE_OPENAI_ENDPOINT` to `.env`; restart Streamlit                                     |
| `AZURE_OPENAI_API_KEY` | Azure API key not set or empty       | Add `AZURE_OPENAI_API_KEY` to `.env`; restart Streamlit                                      |

Recovery paths (either works):

- **Populate the missing variables in `.env` and restart Streamlit.** The warning vanishes and the chat input becomes interactive on the next rerun.
- **Switch back to the other provider** in the sidebar dropdown. The warning is provider-scoped — switching to a configured provider clears it immediately.

### First-Time Anthropic Setup Checklist

If you are switching to Anthropic Claude for the first time, run through these four steps in order:

1. **Obtain MGTI access via Hubble.** Visit https://hubble.mmc.com/apps and complete the coreapi-infrastructure onboarding to receive your `ANTHROPIC_API_KEY`.
2. **Populate `.env`** with the three required Anthropic variables: `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`. See `.env.example` for the template and the optional tuning variables.
3. **Run the smoke test** before opening the UI:
   ```bash
   python scripts/smoke_llm.py --provider anthropic_mgti --verbose
   ```
   Confirm `Exit: 0`. If it fails, the script prints the failing check — fix the env or contact your MGTI sponsor before proceeding.
4. **Restart Streamlit**, switch the sidebar selector to `Anthropic Claude (MGTI)`, send a test query, and confirm the per-message caption shows the Anthropic model.

### Mid-Session Switching Behavior

- Switches take effect on the **next query only**.
- In-flight queries finish on the previously selected provider (Streamlit's synchronous execution model means a switch cannot interleave with an in-flight call).
- Historical messages **retain** their original provider's caption — switching does not re-render historical provenance.
- The active model caption beneath the sidebar dropdown DOES update immediately to reflect the new selection.
```

**Step 5 — Renumber subsequent sections.** Every section header currently numbered ≥9 gets +1. Update both the section header itself and any in-text cross-references (search for `§9`, `§10`, `Section 9`, "see section X" patterns; update each).

**Step 6 — Version stamp bump.** Find the footer (~line 378 in current USER_GUIDE.md). Replace the existing line:
> Last updated: December 2024 (v2.0 - Added password protection & chart visualization)

with:
> Last updated: May 2026 (v2.1 - Added multi-provider LLM selection: Azure OpenAI / Anthropic Claude via MGTI)

(Use today's date in `Month YYYY` format — `May 2026` per the planning context.)

**Step 7 — Verify the EXACT UI strings are present** (RESEARCH Pitfall 13):
- `LLM provider` — at least once (in the how-to-switch steps).
- `Azure OpenAI` — at least once.
- `Anthropic Claude (MGTI)` — at least once.
- `LLM PROVIDER` (uppercase, sidebar header) — at least once.
- `QUERY DISABLED — see sidebar warning` — at least once (in the warning section).
- `via **Azure OpenAI** · \`gpt-4o-mini\`` (or similar) — at least once (in the caption explanation).
- `https://hubble.mmc.com/apps` — at least once.
- `scripts/smoke_llm.py` — at least once.

If any are missing post-edit, fix before declaring done.

**Step 8 — Verify the section content doesn't duplicate README content.** The cross-link in README points HERE for day-to-day use; this section should NOT re-explain "what is LLM_PROVIDER_DEFAULT in env" — that's README's territory. If you find duplication post-write, remove from USER_GUIDE (README is the canonical setup doc).
  </action>
  <verify>
```bash
# New section present with locked title
grep -nE "^## [0-9]+\. LLM Provider Selection" USER_GUIDE.md
# Expected: 1 match

# All locked UI strings present
for s in \
  "LLM provider" \
  "Azure OpenAI" \
  "Anthropic Claude (MGTI)" \
  "LLM PROVIDER" \
  "QUERY DISABLED" \
  "hubble.mmc.com" \
  "smoke_llm.py"; do
  grep -qE "${s}" USER_GUIDE.md && echo "OK '${s}'" || echo "MISSING '${s}'"
done
# Expected: 7 OK lines

# Warning-resolution table present (DOC-02, DOC-04)
grep -nE "ANTHROPIC_BASE_URL.*ANTHROPIC_API_KEY|ANTHROPIC_API_KEY.*ANTHROPIC_MODEL" USER_GUIDE.md
# Expected: ≥1 match (table rows nearby)

# First-time checklist present
grep -nE "First-Time Anthropic Setup Checklist|First.Time.*Setup.*Checklist" USER_GUIDE.md
# Expected: 1 match

# Mid-session switching note
grep -nE "Mid-Session Switching" USER_GUIDE.md
# Expected: 1 match

# Version stamp bumped to v2.1
grep -nE "v2\.1.*multi-provider" USER_GUIDE.md
# Expected: 1 match

# Old version stamp (v2.0) is GONE
grep -nE "v2\.0 - Added password" USER_GUIDE.md
# Expected: 0 matches

# TOC has the new section number (rough check — depends on actual TOC style)
grep -nE "LLM Provider Selection" USER_GUIDE.md | wc -l
# Expected: ≥2 (TOC entry + section header)

# Caption format example present
grep -nE "via \*\*Azure OpenAI\*\*" USER_GUIDE.md
# Expected: ≥1 match

# No unrelated edits (diff sanity)
git diff USER_GUIDE.md --stat
# Expected: USER_GUIDE.md changed; insertions + renumbered headings

# Suite still green
pytest tests/ -v --tb=short
# Expected: 69 passed
```
  </verify>
  <done>
`USER_GUIDE.md` has a new top-level section "LLM Provider Selection" (correctly numbered based on existing structure), inserted between Settings and the prior next section. The new section contains: Overview, MGTI-Only Constraint (with Hubble link), How to Switch Providers (numbered 5-step list), What the Per-Message Caption Means (with both example formats), What to Do When a Provider Warning Appears (full 5-row table + recovery paths), First-Time Anthropic Setup Checklist (numbered 4-step list including smoke-test invocation), Mid-Session Switching Behavior. All subsequent section numbers updated. TOC reflects the new section. Footer version stamp bumped to "v2.1 - Added multi-provider LLM selection: Azure OpenAI / Anthropic Claude via MGTI" with current date (May 2026). All 7 locked UI strings present. No screenshots. 69-test suite still green.
  </done>
</task>

</tasks>

<verification>
Plan-level verification:

1. **Only README.md and USER_GUIDE.md modified:**
   ```bash
   git diff --stat HEAD -- .
   # Expected: README.md and USER_GUIDE.md ONLY
   ```

2. **DOC-01 (README provider feature, sidebar location, default, supported models):**
   ```bash
   grep -nE "LLM Provider Selection|LLM PROVIDER" README.md
   grep -nE "azure_openai|anthropic_mgti|Azure OpenAI|Anthropic Claude" README.md
   # Both: ≥1 match each
   ```

3. **DOC-02 (USER_GUIDE switching + behavior + warnings):**
   ```bash
   grep -nE "How to Switch Providers|What to Do When a Provider Warning" USER_GUIDE.md
   # Expected: ≥2 matches
   ```

4. **DOC-03 (MGTI-only constraint + Hubble link in BOTH docs):**
   ```bash
   grep -nE "MGTI|Hubble|hubble\.mmc\.com" README.md USER_GUIDE.md
   # Expected: ≥1 match in EACH file
   ```

5. **DOC-04 (smoke test docs in BOTH places — README "how/when", USER_GUIDE setup checklist):**
   ```bash
   grep -nE "smoke_llm\.py" README.md USER_GUIDE.md
   # Expected: ≥1 match in EACH file
   ```

6. **Cross-link from README to USER_GUIDE:**
   ```bash
   grep -nE "USER_GUIDE\.md" README.md
   # Expected: ≥1 match
   ```

7. **No screenshots added:**
   ```bash
   grep -nE "!\[.*\]\(.*\.(png|jpg|jpeg|gif|webp)\)" README.md USER_GUIDE.md
   # Expected: ZERO output
   ```

8. **No code edits in this plan:**
   ```bash
   git diff --stat HEAD -- src/ scripts/ tests/ app.py .env.example
   # Expected: ZERO output
   ```

9. **Test suite green (docs only):**
   ```bash
   pytest tests/ -v --tb=short
   # Expected: 69 passed
   ```

10. **Manual reading-flow check (operator):**
    - Open README.md. Read top-to-bottom. Confirm new env-var rows fit the existing table, the LLM Provider Selection subsection has a working cross-link, and the Smoke Test subsection precedes Data Privacy.
    - Open USER_GUIDE.md. Read the new §9 top-to-bottom. Confirm the warning table renders correctly in GitHub/VSCode markdown preview. Confirm subsequent section numbers are consistent.
    - This step is non-blocking for Plan 05-04 done — Plan 05-05's acceptance gate grep-asserts the required phrases.
</verification>

<success_criteria>
- [ ] `README.md` has env-var rows for `LLM_PROVIDER_DEFAULT` + the three required Anthropic vars + the optional-vars summary row
- [ ] `README.md` has the MGTI/Hubble pointer paragraph with the `https://hubble.mmc.com/apps` link
- [ ] `README.md` has the `### LLM Provider Selection` subsection with the cross-link to USER_GUIDE.md
- [ ] `README.md` has the `### Smoke Test (operator-run)` subsection with the three invocation variants and exit-code documentation
- [ ] `USER_GUIDE.md` has a new section `LLM Provider Selection` correctly numbered for the existing TOC; subsequent sections renumbered
- [ ] USER_GUIDE new section covers: Overview, MGTI-Only Constraint, How to Switch (5-step), Caption Meaning (with both example formats), Warning-Resolution table (5 rows + recovery paths), First-Time Anthropic Setup Checklist (4-step including smoke test), Mid-Session Switching Behavior
- [ ] USER_GUIDE footer version stamp bumped to `v2.1` referencing multi-provider LLM with current date
- [ ] All 7 locked UI strings present somewhere in USER_GUIDE.md: `LLM provider`, `Azure OpenAI`, `Anthropic Claude (MGTI)`, `LLM PROVIDER`, `QUERY DISABLED`, `hubble.mmc.com`, `smoke_llm.py`
- [ ] No screenshots embedded in either doc
- [ ] No edits to src/, tests/, scripts/, app.py, or .env.example
- [ ] Full 69-test suite still green
</success_criteria>

<output>
After completion, create `.planning/phases/05-sidebar-ui-toggle-documentation/05-04-SUMMARY.md` documenting:
- Lines added/modified in each file (with section names)
- Confirmation: DOC-01..04 requirement coverage verified by grep
- Confirmation: no code edits in this plan
- 69-test suite still green
- Note for Plan 05-05: the acceptance gate's docs-content test should grep README and USER_GUIDE for: "LLM provider", "Anthropic Claude (MGTI)", "smoke_llm.py", "hubble.mmc.com", and the four required topics (provider selection / MGTI constraint / smoke-test how-to / warning resolution)
</output>
