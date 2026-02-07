# Requirements: JobFlow

**Defined:** 2026-02-07
**Core Value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Configuration

- [ ] **CFG-01**: User configures all settings via single YAML file (profile, queries, scoring weights, timing, platform toggles)
- [ ] **CFG-02**: Pipeline runs on a schedule (cron/systemd/launchd) without manual CLI invocation
- [ ] **CFG-03**: All salary data normalized to comparable USD annual figures across platforms
- [ ] **CFG-04**: User selects apply mode per job or globally: full-auto (with approval gate), semi-auto (review before submit), Easy Apply only

### Discovery & Scoring

- [ ] **DISC-01**: Pipeline detects and highlights new jobs not seen in previous runs
- [ ] **DISC-02**: Fuzzy deduplication catches company name variants ("Google" vs "Google LLC" vs "Alphabet")
- [ ] **DISC-03**: Score breakdown shows point-by-point explanation (title +2, tech overlap +2, remote +1, salary +1)

### Dashboard

- [ ] **DASH-01**: Text search across job title, company, and description
- [ ] **DASH-02**: Extended status workflow: Saved, Applied, Phone Screen, Technical Interview, Final Interview, Offer, Rejected, Withdrawn, Ghosted
- [ ] **DASH-03**: Bulk status actions -- select multiple jobs, update status in one click
- [ ] **DASH-04**: Export filtered results to CSV or JSON from dashboard
- [ ] **DASH-05**: Activity log per job -- timeline of discovery, status changes, notes, applications
- [ ] **DASH-06**: Enhanced stats -- jobs per day/week, response rate, time-in-stage, platform effectiveness
- [ ] **DASH-07**: Kanban board view with drag-and-drop between status columns

### AI & Resume

- [ ] **AI-01**: AI-generated tailored resume per job description using LLM (reorder skills, adjust summary, emphasize relevant experience)
- [ ] **AI-02**: AI-generated targeted cover letter per application
- [ ] **AI-03**: Multi-resume management -- store versions, track which resume sent to which company

### Application

- [ ] **APPLY-01**: One-click apply from dashboard -- triggers browser automation from web UI with status updates

### Platform

- [ ] **PLAT-01**: Pluggable platform architecture -- add new job boards without modifying core pipeline code

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Discovery

- **DISC-04**: Company blacklist -- permanently exclude specified companies from results
- **DISC-05**: Job description diff/change tracking between scraping runs

### AI

- **AI-04**: LLM-based semantic scoring (understand "container orchestration" = Kubernetes)

### Notifications

- **NOTF-01**: Notification after scheduled run (email, Slack, or desktop) about new high-scoring jobs

### Analytics

- **ANLY-01**: Application funnel visualization (Discovered -> Applied -> Interview -> Offer with conversion rates)

### Enrichment

- **ENRI-01**: Auto-fetch company info (Glassdoor rating, funding, tech stack) on job detail page

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-user / multi-tenant support | Single-user tool, configured per clone |
| Mobile app / PWA | Web dashboard is sufficient, job apps happen at a desk |
| LinkedIn integration | Aggressive anti-automation, permanent account ban risk |
| CAPTCHA/Cloudflare bypass | Arms race, legally grey, current detect-and-notify approach is correct |
| Chrome extension | Separate product, tangential to core |
| AI chatbot interface | LLM latency per interaction, slower than clicking filters |
| Contact/networking CRM | Separate problem domain, notes field is sufficient |
| Payment/subscription features | Open-source portfolio project, no monetization |
| Fully autonomous mass-apply | ATS blacklisting risk, destroys candidate reputation |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CFG-01 | Phase 1: Config Externalization | Complete |
| CFG-02 | Phase 4: Scheduled Automation | Pending |
| CFG-03 | Phase 3: Discovery Engine | Pending |
| CFG-04 | Phase 8: One-Click Apply | Pending |
| DISC-01 | Phase 3: Discovery Engine | Pending |
| DISC-02 | Phase 3: Discovery Engine | Pending |
| DISC-03 | Phase 3: Discovery Engine | Pending |
| DASH-01 | Phase 5: Dashboard Core | Pending |
| DASH-02 | Phase 5: Dashboard Core | Pending |
| DASH-03 | Phase 5: Dashboard Core | Pending |
| DASH-04 | Phase 5: Dashboard Core | Pending |
| DASH-05 | Phase 5: Dashboard Core | Pending |
| DASH-06 | Phase 6: Dashboard Analytics | Pending |
| DASH-07 | Phase 6: Dashboard Analytics | Pending |
| AI-01 | Phase 7: AI Resume & Cover Letter | Pending |
| AI-02 | Phase 7: AI Resume & Cover Letter | Pending |
| AI-03 | Phase 7: AI Resume & Cover Letter | Pending |
| APPLY-01 | Phase 8: One-Click Apply | Pending |
| PLAT-01 | Phase 2: Platform Architecture | Complete |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-02-07*
*Last updated: 2026-02-07 after roadmap creation*
