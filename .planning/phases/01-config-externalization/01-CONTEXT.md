# Phase 1: Config Externalization - Context

**Gathered:** 2026-02-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace all hardcoded Python settings with a single YAML config file. User configures their search queries, scoring weights, platform toggles, and timing in `config.yaml` — no Python files touched. Personal profile info and credentials stay in `.env`. Existing pipeline behavior is unchanged; only the configuration source changes.

</domain>

<decisions>
## Implementation Decisions

### Config structure
- Single `config.yaml` file at project root (next to `orchestrator.py`)
- Organized by domain: `search:`, `scoring:`, `platforms:`, `schedule:` (not by pipeline phase)
- No overrides mechanism — one file, edit it directly
- No config splitting — everything non-sensitive in one YAML

### Sensitive values
- Credentials stay in `.env` (gitignored) — `DICE_EMAIL`, `DICE_PASSWORD`, `INDEED_EMAIL`
- Personal profile info (name, email, phone, location, GitHub, etc.) also moves to `.env` — keeps `config.yaml` free of personal data
- `config.yaml` is committable to git — safe to share as a template
- `config.example.yaml` provided alongside with placeholder values
- Claude's discretion on whether config references env vars explicitly or code handles it implicitly

### Defaults & validation
- Strict validation — every field must be present, error on missing
- All validation errors reported at once (not fail-on-first) with specific field-level messages (e.g., "scoring.weights.title_match must be 0-10, got 15")
- `--validate` flag on orchestrator for dry-run config check without running the pipeline
- `config.example.yaml` is heavily commented — inline YAML comments explain every field and valid values

### Search query format
- Structured queries with explicit fields (title, keywords, location) — not plain strings
- Each query can optionally specify `platforms: [indeed, dice]` to limit which platforms run it; defaults to all enabled platforms if omitted
- Scoring weights are configurable in YAML (title_match, tech_overlap, remote, etc.) — user can tune what matters
- All scored jobs are saved regardless of score — no minimum threshold in config; filtering happens in the dashboard

### Claude's Discretion
- Whether `.env` vars are referenced explicitly in config.yaml (e.g., `${DICE_PASSWORD}`) or handled implicitly by code
- Exact pydantic-settings model structure and field naming
- How structured queries are assembled into platform-specific search URLs
- Validation error formatting details

</decisions>

<specifics>
## Specific Ideas

- config.example.yaml should be comprehensive enough that a new user can fill it in and run the pipeline immediately
- The `--validate` flag should check both config.yaml and .env completeness (missing credentials = warning per platform, not a hard error)
- Scoring weights in config should map to the existing 1-5 rubric categories from CLAUDE.md

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-config-externalization*
*Context gathered: 2026-02-07*
