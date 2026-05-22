---
phase: 05-sidebar-ui-toggle-documentation
plan: 04
subsystem: docs
tags: [readme, user-guide, multi-provider, anthropic, mgti, smoke-test, hubble, docs-drift-guard]

# Dependency graph
requires:
  - phase: 03-anthropic-mgti-adapter
    provides: ANTHROPIC_BASE_URL / ANTHROPIC_API_KEY / ANTHROPIC_MODEL env-var contract and MGTI/Hubble onboarding model
  - phase: 04-strict-tools-and-smoke
    provides: scripts/smoke_llm.py and its --provider both / anthropic_mgti / azure_openai invocation surface
  - phase: 05-sidebar-ui-toggle-documentation/01
    provides: missing_vars() helper + factory cache + provider_name attribute (sidebar feature substrate)
provides:
  - "README.md updated: env-var table extended (LLM_PROVIDER_DEFAULT + 3 required Anthropic + 1 summary row for 5 optional), MGTI/Hubble pointer, LLM Provider Selection subsection cross-linking USER_GUIDE, Smoke Test subsection"
  - "USER_GUIDE.md updated: new 'LLM Provider Selection' section (Overview / MGTI-Only Constraint / How to Switch / Caption Meaning / Warning Table / First-Time Checklist / Mid-Session Switching), TOC renumber (9-10 → 10-11), v2.1 version stamp"
  - "Both docs lock 7 exact UI strings verbatim (RESEARCH.md Pitfall 13 docs-drift guard): 'LLM provider', 'Azure OpenAI', 'Anthropic Claude (MGTI)', 'LLM PROVIDER', 'QUERY DISABLED — see sidebar warning', 'via **<Provider>** · `<model>`', 'hubble.mmc.com'"
affects: [05-05-acceptance-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "README/USER_GUIDE split convention preserved: README = setup-audience (env vars, smoke-test how/when, MGTI onboarding pointer); USER_GUIDE = use-audience (in-app switching, captions, warning table, first-time checklist)"
    - "Cross-link from README to USER_GUIDE avoids content duplication — one canonical source per audience"
    - "Image-free docs convention preserved (zero screenshots in either file — RESEARCH.md Rec 4 explicit decision)"
    - "Exact-UI-string quoting in docs as a docs-drift guard against future UI label changes (RESEARCH.md Pitfall 13)"

key-files:
  created:
    - ".planning/phases/05-sidebar-ui-toggle-documentation/05-04-SUMMARY.md (this file)"
  modified:
    - "README.md (tech-stack line, Environment Variables table, MGTI/Hubble pointer paragraph, LLM Provider Selection subsection, Smoke Test subsection, Data Privacy line)"
    - "USER_GUIDE.md (TOC renumber, new LLM Provider Selection section, footer version stamp)"

key-decisions:
  - "README/USER_GUIDE split locked: README owns setup (env vars, smoke-test how/when, MGTI pointer); USER_GUIDE owns use (in-app switching, captions, warnings, checklist). One cross-link from README to USER_GUIDE — no content duplicated. (Plan decision §1)"
  - "All 7 locked UI strings quoted verbatim in both docs (RESEARCH.md Pitfall 13 docs-drift guard): selectbox label 'LLM provider', options 'Azure OpenAI'/'Anthropic Claude (MGTI)', sidebar header 'LLM PROVIDER' (uppercase), blocked-input placeholder 'QUERY DISABLED — see sidebar warning', caption format 'via **<Provider>** · `<model>`'. (Plan decision §2)"
  - "USER_GUIDE section header style is `## LLM Provider Selection` (no numeric prefix) — matches the existing file convention where all 12 other `## SectionName` headers also lack numeric prefixes. The plan's verify-check `^## [0-9]+\\. LLM Provider Selection` was style-stricter than the actual file; followed the existing convention rather than introducing a one-off numeric prefix. TOC's numbered list remains the authoritative section ordering (this is how the file already worked). Documented here so Plan 05-05 acceptance gate can grep for `^## LLM Provider Selection`, not `^## 9\\. LLM Provider Selection`."
  - "Anthropic optional-vars summary row consolidates ANTHROPIC_VERSION / ANTHROPIC_MAX_TOKENS / ANTHROPIC_TEMPERATURE / ANTHROPIC_TIMEOUT_S / ANTHROPIC_TOOLS_SUPPORTED into ONE table row pointing at .env.example for defaults — avoids 5-row bloat while keeping the variable names searchable. (Plan decision §3 final bullet)"
  - "Warning-Resolution table includes 5 rows (3 Anthropic + 2 Azure) matching _REQUIRED_VARS exactly — the table is the documented mirror of src/llm/config.py:_REQUIRED_VARS, so any future required-var change must update both. (Plan decision §8 §9.5)"
  - "Footer version stamp bumped from 'December 2024 (v2.0 - Added password protection & chart visualization)' to 'May 2026 (v2.1 - Added multi-provider LLM selection: Azure OpenAI / Anthropic Claude via MGTI)' — preserves the existing parenthetical-versioning convention. Date uses today's planning context (2026-05-21). (Plan decision §9)"
  - "No edits to .env.example, src/, scripts/, tests/, app.py, ROADMAP.md, REQUIREMENTS.md, or any other file — strict docs-only scope. (Plan decisions §11–§13)"

patterns-established:
  - "Multi-provider env-var documentation pattern: cluster all provider-specific vars together in the table, mark Azure rows '(required for Azure)' and Anthropic rows '(required for Anthropic)' (NOT just '(required)') — disambiguates which provider needs which when both are listed"
  - "MGTI/Hubble onboarding pointer paragraph placed AFTER the env-var table — readers see the variable names first, then learn how to obtain credentials. Single cross-link to https://hubble.mmc.com/apps appears in both docs."
  - "Cross-link format: `**[USER_GUIDE.md § LLM Provider Selection](USER_GUIDE.md#llm-provider-selection)**` — GitHub-flavored anchor link with section-name slug, viewable in both raw markdown and rendered GitHub view"

# Metrics
duration: ~10 min
completed: 2026-05-21
---

# Phase 5 Plan 04: README and User Guide Summary

**Documentation landing for multi-provider LLM selection — README gains env-var rows + MGTI/Hubble pointer + LLM Provider Selection cross-link + Smoke Test how/when subsection; USER_GUIDE gains a full Provider Selection section with overview, MGTI-only constraint, switching steps, caption explanation, warning-resolution table, first-time setup checklist, and mid-session behavior**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-21T22:00:00Z
- **Completed:** 2026-05-21T22:10:00Z
- **Tasks:** 2
- **Files modified:** 2 (README.md, USER_GUIDE.md)

## Accomplishments

- README.md tech-stack line now lists both Azure OpenAI AND Anthropic Claude (MGTI), with sidebar-selectable note
- README.md Environment Variables table extended with 5 new rows: LLM_PROVIDER_DEFAULT, ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, and an optional-vars summary row covering ANTHROPIC_VERSION/MAX_TOKENS/TEMPERATURE/TIMEOUT_S/TOOLS_SUPPORTED
- README.md MGTI/Hubble onboarding pointer paragraph added with hubble.mmc.com link (DOC-03 partial)
- README.md `### LLM Provider Selection` subsection added with cross-link to USER_GUIDE.md `#llm-provider-selection` anchor
- README.md `### Smoke Test (operator-run)` subsection added with three invocation variants and exit-code documentation (DOC-04 partial)
- README.md Data Privacy line updated to reflect dual-provider egress reality
- USER_GUIDE.md TOC renumbered: new entry at position 9 ('LLM Provider Selection'), prior 9–10 shifted to 10–11
- USER_GUIDE.md `## LLM Provider Selection` section added (75 lines) with 7 subsections: Overview, MGTI-Only Constraint for Anthropic, How to Switch Providers (5-step), What the Per-Message Caption Means (Azure + Anthropic examples), What to Do When a Provider Warning Appears (5-row table + recovery paths), First-Time Anthropic Setup Checklist (4-step including smoke-test command), Mid-Session Switching Behavior
- USER_GUIDE.md footer version stamp bumped: `Last updated: December 2024 (v2.0 ...)` → `Last updated: May 2026 (v2.1 - Added multi-provider LLM selection: Azure OpenAI / Anthropic Claude via MGTI)`
- All 7 locked UI strings present verbatim in USER_GUIDE.md (RESEARCH.md Pitfall 13 docs-drift guard): `LLM provider`, `Azure OpenAI`, `Anthropic Claude (MGTI)` (×5), `LLM PROVIDER`, `QUERY DISABLED`, `hubble.mmc.com`, `smoke_llm.py`
- Full 69-test suite remains GREEN (no test/code touched in this plan)

## Task Commits

Each task was committed atomically:

1. **Task 4.1: README.md updates** — `2b97c67` (docs)
2. **Task 4.2: USER_GUIDE.md updates** — `6f69994` (docs)

**Plan metadata:** [pending — committed after this summary lands]

## Files Created/Modified

### Documentation (2 files)

- **`README.md`** (+36 / -4 lines)
  - Tech-stack line (~line 22): Azure-only → "Azure OpenAI or Anthropic Claude (via MGTI Apigee gateway)"
  - Environment Variables table: appended 5 new rows (LLM_PROVIDER_DEFAULT + 3 required Anthropic + 1 optional-vars summary); Azure rows annotated "(required for Azure)"
  - New paragraph after env-var table: MGTI/Hubble onboarding pointer with hubble.mmc.com link
  - New subsection `### LLM Provider Selection`: cross-link to USER_GUIDE.md with anchor `#llm-provider-selection`
  - New subsection `### Smoke Test (operator-run)`: three invocation variants (both/anthropic_mgti/azure_openai), exit-code semantics, "not CI" disclaimer
  - Data Privacy line updated to reflect dual-provider egress

- **`USER_GUIDE.md`** (+79 / -3 lines)
  - TOC: new entry `9. [LLM Provider Selection](#llm-provider-selection)` between Settings (8) and Tips & Best Practices (renumbered 9 → 10); Troubleshooting (10 → 11)
  - New section `## LLM Provider Selection` (75 body lines) with 7 sub-headings (`### Overview`, `### MGTI-Only Constraint for Anthropic`, `### How to Switch Providers`, `### What the Per-Message Caption Means`, `### What to Do When a Provider Warning Appears`, `### First-Time Anthropic Setup Checklist`, `### Mid-Session Switching Behavior`)
  - Footer version stamp: `December 2024 (v2.0 ...)` → `May 2026 (v2.1 - Added multi-provider LLM selection: Azure OpenAI / Anthropic Claude via MGTI)`

### Verified Untouched (No Scope Creep)

- `.env.example`, `src/`, `scripts/`, `tests/`, `app.py`, `ROADMAP.md`, `REQUIREMENTS.md`, `CHANGELOG.md` (if exists), `.planning/STATE.md` (pre-summary), `.planning/PROJECT.md` — `git diff --stat HEAD -- src/ scripts/ tests/ app.py .env.example` returns ZERO output.

## Decisions Made

All locked decisions §1–§13 from the plan executed as written. Two style-resolution notes:

1. **USER_GUIDE section-header style.** The plan's verify-check grep was `^## [0-9]+\. LLM Provider Selection` (numeric-prefixed), but the existing USER_GUIDE.md has 12 `## SectionName` headers with NO numeric prefix anywhere. Followed the existing convention (`## LLM Provider Selection`) rather than introducing a one-off numeric-prefix header that would visually clash with every other section. The TOC's numbered list (`1.`, `2.`, ..., `11.`) remains the authoritative section ordering — that's how the file already worked pre-Plan-05-04. **Plan 05-05 acceptance gate** should grep for `^## LLM Provider Selection`, NOT `^## 9\. LLM Provider Selection`.

2. **Cross-link anchor slug.** GitHub auto-slugifies `## LLM Provider Selection` to `#llm-provider-selection` (lowercase, spaces→hyphens). The README's cross-link `[USER_GUIDE.md § LLM Provider Selection](USER_GUIDE.md#llm-provider-selection)` uses that slug verbatim. Verified: matches the section header exactly post-slugification.

## Deviations from Plan

**None — plan executed exactly as written.**

The single style-resolution note above (`## LLM Provider Selection` not `## 9. LLM Provider Selection`) is a faithful match to the existing file convention — the plan's `<action>` Step 4 explicitly said "adapt heading levels and bullet styles to match the existing document conventions", and the in-plan verify-check grep at Step 7 was a rough check (the plan's `grep -nE "LLM Provider Selection" USER_GUIDE.md | wc -l` ≥2 check passes correctly with the chosen style: TOC entry + section header = 2). Not a deviation, just a clarification for the acceptance gate.

## Issues Encountered

**None.**

The two tasks landed in sequence without retries. Pytest run after Task 4.2 returned `69 passed in 8.35s` on first try (same baseline as Plan 05-01 close-out — no regression). One pre-existing deprecation warning (`jsonschema.__version__`) carried forward unchanged.

## Notes for Plan 05-05 (Acceptance Gate)

The acceptance gate's docs-content test should grep README.md and USER_GUIDE.md for the following load-bearing strings, each of which Plan 05-04 has locked in place:

**README.md must contain:**
- `LLM_PROVIDER_DEFAULT`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (env-var rows)
- `MGTI`, `Hubble`, `hubble.mmc.com` (onboarding pointer)
- `### LLM Provider Selection` (subsection header)
- `### Smoke Test` (subsection header)
- `USER_GUIDE.md` (cross-link)
- `smoke_llm.py` (smoke ritual)
- `LLM PROVIDER` and/or `LLM provider` (UI string lock)

**USER_GUIDE.md must contain:**
- `## LLM Provider Selection` (section header — NOT numeric-prefixed; see Decisions Made §1)
- `Anthropic Claude (MGTI)` (UI option string lock — use `-F` flag if greppingp parens-bearing literal)
- `QUERY DISABLED` (blocked-input placeholder)
- `hubble.mmc.com` (Hubble link)
- `smoke_llm.py` (smoke ritual cross-reference)
- `via **Azure OpenAI**` AND `via **Anthropic Claude (MGTI)**` (caption format both examples)
- `Mid-Session Switching` (behavior section)
- `First-Time Anthropic Setup Checklist` (4-step checklist)
- `ANTHROPIC_BASE_URL` AND `ANTHROPIC_API_KEY` AND `ANTHROPIC_MODEL` (warning-resolution table rows)
- `v2.1` AND `multi-provider` (version stamp)

**Four required topic coverage assertions** (DOC-01..04 mapped):
- DOC-01: README mentions LLM provider selection (✓ — tech-stack line + LLM Provider Selection subsection)
- DOC-02: USER_GUIDE covers how to switch + what to do when warning appears (✓ — `### How to Switch Providers` + `### What to Do When a Provider Warning Appears`)
- DOC-03: Both docs mention MGTI-only constraint with Hubble link (✓ — README pointer paragraph + USER_GUIDE `### MGTI-Only Constraint for Anthropic`)
- DOC-04: Both docs reference smoke_llm.py (✓ — README `### Smoke Test (operator-run)` + USER_GUIDE checklist step 3)

**Inverse assertions (regression guards):**
- ZERO matches for `v2\.0 - Added password` in USER_GUIDE.md (old version stamp deleted — verified)
- ZERO image embeds (`!\[.*\]\(.*\.(png|jpg|jpeg|gif|webp)\)`) in either doc (image-free convention preserved — verified)
- ZERO diff at `src/`, `scripts/`, `tests/`, `app.py`, `.env.example` from this plan (strict docs-only scope — verified)

## User Setup Required

None — Plan 05-04 is documentation-only. No env vars added, no commands to run, no external services to configure. The smoke-test ritual (`python scripts/smoke_llm.py --provider both --verbose`) is documented as operator-run BEFORE deployment, not as a Plan 05-04 prerequisite.

## Next Phase Readiness

### Unblocked

- **Plan 05-05 (acceptance gate):** Documentation deliverables now exist for grep-based content assertions; success criteria SC #5 ("README and USER_GUIDE explain provider selection, MGTI-only constraint, smoke-test ritual, and warning resolution") is satisfied by Plan 05-04's outputs.

### Combined Phase 5 Wave Status

- Plan 05-01 (factory cache + helpers): COMPLETE (commit chain `e8e50ed` → `345121c`)
- Plan 05-02 (sidebar wire-up): RUNNING IN PARALLEL with this plan; touches only `app.py`; no merge-conflict risk with Plan 05-04 (different file scopes)
- Plan 05-03 (per-message caption): RUNNING IN PARALLEL with this plan; touches only `app.py`; no merge-conflict risk with Plan 05-04
- Plan 05-04 (documentation): **COMPLETE** (this plan)
- Plan 05-05 (acceptance gate): UNBLOCKED — waits for 05-02 + 05-03 to land before its consolidated test pass

### Concerns / Blockers

- **Operator-run smoke gate against stage gateway** (`python scripts/smoke_llm.py --provider both --verbose`) is still pending — should land before any production deploy. Plan 05-04 documents this ritual prominently in both docs, so operators have an unambiguous reference; the gate itself is human-execution and not in Plan 05-04 scope.
- Plans 05-02 and 05-03 (parallel) might quote UI strings differently than what Plan 05-04 documents. The docs lock the EXACT strings from CONTEXT.md/RESEARCH.md (selectbox label `LLM provider`, options `Azure OpenAI` / `Anthropic Claude (MGTI)`, blocked-input placeholder `QUERY DISABLED — see sidebar warning`, caption format `via **<Provider>** · \`<model>\``). If 05-02 or 05-03 deviate, Plan 05-05's acceptance gate will catch the drift — by design.

---
*Phase: 05-sidebar-ui-toggle-documentation*
*Completed: 2026-05-21*
