# JobFlow — Personal Job Search Automation

## What This Is

A self-hosted, single-user job search automation tool. Clone the repo, drop in your resume and a config file, and the system scrapes job boards, scores matches against your profile, manages listings through a web dashboard, and automates applications with flexible control — from fully automated to manual review. Built for power users who want to replace manual job searching with a reliable daily pipeline.

## Core Value

**From discovery to application in one tool.** The system must reliably find relevant jobs, present them clearly, and make applying as frictionless as the user wants — whether that's one-click auto-apply or careful manual review.

## Requirements

### Validated

- ✓ Multi-platform scraping (Indeed, Dice, RemoteOK) — existing
- ✓ Stealth browser automation with anti-detection (Playwright + playwright-stealth) — existing
- ✓ Session persistence per platform (browser_sessions/) — existing
- ✓ Human-in-the-loop CAPTCHA/verification handling — existing
- ✓ Job scoring engine (1-5 scale against candidate profile) — existing
- ✓ Cross-platform deduplication by normalized company+title — existing
- ✓ CLI orchestrator with 5-phase pipeline (setup → login → search → score → apply) — existing
- ✓ Raw + scored JSON output with per-job description files — existing
- ✓ Web dashboard with SQLite persistence, filtering, status updates — existing
- ✓ Form filling heuristics for application fields — existing
- ✓ Configurable search queries and platform selection — existing
- ✓ Debug screenshot capture on selector failure — existing

### Active

- [ ] Single config file (YAML/JSON) for all user settings — replace hardcoded CLAUDE.md profile
- [ ] Resume directory with original + variant support
- [ ] AI-powered resume tailoring per job description
- [ ] Flexible apply modes: full-auto (with approval gate), semi-auto (review + submit), Easy Apply only
- [ ] Dashboard improvements: polish UI, better job detail views, apply actions from dashboard
- [ ] Pluggable platform architecture — easy to add new job boards
- [ ] Application tracking and status management (applied, interviewing, rejected, etc.)
- [ ] Portfolio-quality README, tests, and code polish

### Out of Scope

- Multi-user / multi-tenant support — this is a single-user tool, configured per clone
- Mobile app — web dashboard is sufficient
- Real-time notifications (email/Slack alerts) — user runs the pipeline on their schedule
- LinkedIn scraping — high legal/ToS risk, complex anti-bot, defer to future consideration
- Guided CLI setup wizard — edit config files directly, keep it simple

## Context

**Existing codebase:** Fully functional 5-phase pipeline with Indeed, Dice, and RemoteOK support. Browser automation uses Playwright with stealth patches. Web dashboard built with FastAPI + Jinja2 + htmx + SQLite. Scoring engine uses weighted criteria (title, tech stack, location, salary). End-to-end tested: 619 raw jobs → 106 unique → 19 scored 3+.

**Current friction:** The pipeline finds jobs reliably, but everything after scraping is manual. Getting from "here are 20 good matches" to "applied to 15 of them" requires too much hand-holding. The apply phase needs the most work.

**User profile:** Currently hardcoded in CLAUDE.md. Needs to move to a standalone config file that any user can populate for themselves.

**Platform stability:** Indeed, Dice, and RemoteOK selectors have been stable as of Feb 2026. Selector breakage is a known risk but not the primary pain point.

## Constraints

- **Tech stack**: Python 3.11+, Playwright, FastAPI — established and working, no reason to change
- **Single user**: All design decisions assume one user per installation. No auth layer needed.
- **Anti-detection**: Must maintain stealth browser approach. System Chrome, no automation flags.
- **Human-in-the-loop**: Application submission always requires human approval (even in "auto" mode, there's an approve step)
- **Credentials**: Always from .env, never committed. Platform credentials stay separate from user profile config.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single config file + resume dir for user profile | Simple, git-friendly, no setup wizard needed | — Pending |
| Pluggable platform architecture | Future-proof for adding boards without touching core | — Pending |
| Three apply modes (auto/semi/manual) | Different comfort levels for different job types | — Pending |
| AI resume tailoring | Competitive advantage — personalized resumes score better | — Pending |
| Keep FastAPI + htmx dashboard | Already built and working, just needs polish | — Pending |

---
*Last updated: 2026-02-07 after initialization*
