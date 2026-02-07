# Domain Pitfalls

**Domain:** Job search automation -- automated application submission, AI resume tailoring, pluggable platform architecture
**Researched:** 2026-02-07
**Confidence:** HIGH (grounded in existing codebase analysis, open-source project patterns, and verified platform behavior)

---

## Critical Pitfalls

Mistakes that cause rewrites, account bans, or render the tool useless.

---

### Pitfall 1: Account Ban from Behavioral Fingerprinting (Not Just Technical Detection)

**What goes wrong:** The tool applies to jobs at machine speed with perfectly uniform timing, identical mouse paths, and zero scroll variation. Indeed's anomaly detection flags the account within days. The account gets permanently suspended with no appeal path.

**Why it happens:** Developers focus entirely on *technical* anti-detection (stealth plugins, UA spoofing, disabling automation flags) and ignore *behavioral* fingerprinting. Indeed explicitly uses "anomaly detection and machine learning solutions to distinguish between human users and bots" (per their DSA transparency report). The existing `human_delay()` with random 2-5s pauses is necessary but insufficient -- real humans also scroll erratically, hover over elements before clicking, sometimes go back and re-read, and have session-level patterns (time of day, session length, breaks).

**Consequences:** Permanent Indeed account ban. All cached sessions invalidated. Must create new account, potentially from new IP/device. Employer blacklist if flagged mid-application.

**Prevention:**
1. Rate-limit applications to 5-10 per day maximum (not 5-10 per hour). The commercial tool Wonsulting shut down its bulk-send feature in August 2025 after clients averaged only 2% callback rates from mass applications.
2. Add session-level behavioral modeling: vary session duration, include "idle" periods, sometimes navigate to non-job pages.
3. Randomize mouse movement paths, not just timing. Use Bezier curves, not straight lines.
4. Never apply to more than 2-3 jobs in a single browser session. Close and reopen between batches.
5. Implement a daily application budget with hard enforcement in the orchestrator.
6. Monitor for ban signals: unexpected redirects to captcha, "unusual activity" emails, sudden 403s.

**Detection (warning signs):**
- Cloudflare challenges appearing more frequently than on first use
- Session cookies invalidated despite no expiry
- Indeed showing "something went wrong" on apply pages that worked before
- Application confirmations stop arriving by email

**Phase:** Must be addressed in Phase 1 (apply infrastructure) before any automated submissions happen. The daily budget and behavioral guardrails are prerequisites for the entire apply pipeline.

**Confidence:** HIGH -- verified against Indeed's DSA report and Wonsulting's public shutdown announcement.

---

### Pitfall 2: ATS Form Diversity is Exponentially Harder Than It Looks

**What goes wrong:** The tool is built to handle Indeed Easy Apply and Dice Easy Apply (both platform-native, predictable forms). Then RemoteOK `apply_url` redirects land on Greenhouse, Lever, Ashby, Workday, Workable, BambooHR, JazzHR, iCIMS, SmartRecruiters, Taleo, and dozens of custom company career pages. Each has completely different DOM structure, field names, validation behavior, and multi-step flows. The "generic form filler" handles maybe 30% of forms correctly.

**Why it happens:** The current `FormFiller` uses keyword matching on field attributes (`name`, `id`, `placeholder`, `aria-label`) to identify fields. This works for standardized fields (name, email, phone) but fails on:
- **Custom questions** that are unique per job posting (e.g., "Are you comfortable with on-call rotations?", "Describe your experience with distributed systems")
- **Multi-step forms** where fields appear across multiple pages/modals
- **Iframe-embedded forms** (Greenhouse default is an iframe embed)
- **Shadow DOM components** (Workday uses Web Components extensively)
- **Dynamic form fields** that appear based on previous answers
- **File upload variations** (some accept PDF only, some want DOCX, some have drag-and-drop, some have hidden file inputs)
- **Dropdown menus** with values that don't match your data format (country picker expecting "US" vs "United States" vs "USA")

**Consequences:** Partial form submissions with missing fields. Applications that get rejected by ATS validation. Wrong data in wrong fields (salary in phone field). Wasted applications that count against your daily budget.

**Prevention:**
1. Do NOT attempt a single universal form filler. Instead, build explicit handlers for the top 5 ATS platforms (Greenhouse, Lever, Workday, Ashby, Workable) plus a generic fallback.
2. Greenhouse has a public Job Board API (`POST https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{id}`) that accepts applications without browser automation. Use the API where possible -- it is documented, stable, and has known field names. Query `?questions=true` to get dynamic custom fields per job.
3. For Lever, use the public Postings API (`POST https://api.lever.co/v0/postings/{company}/{postingId}?key={api_key}`) -- also documented.
4. For browser-based forms, detect the ATS first (check URL patterns: `boards.greenhouse.io`, `jobs.lever.co`, `*.workday.com/*/job-apply/`) and route to the appropriate handler.
5. For custom questions that cannot be auto-filled, queue them for human review rather than guessing. A blank custom answer is better than a wrong one.
6. Build an "ATS detection confidence" metric: if the form filler identifies fewer than 3 standard fields, abort and flag for manual application.

**Detection (warning signs):**
- Form filler `filled` dict returns fewer than 4 fields on a page with 10+ visible inputs
- Application confirmation page never loads after submit
- ATS responds with validation errors
- Resume upload silently fails (no file attached)

**Phase:** This is the hardest engineering problem in the entire project. Should be Phase 2 or 3 (after apply infrastructure is stable). Start with Greenhouse API + Lever API (no browser needed), then add Workday/Ashby browser handlers. Generic form filler is last resort, not first approach.

**Confidence:** HIGH -- Greenhouse and Lever APIs verified via official documentation. ATS diversity is well-documented in the industry.

---

### Pitfall 3: AI Resume Tailoring Fabricates Experience

**What goes wrong:** The LLM is asked to "tailor this resume for the job description" and it invents quantified metrics ("increased deployment frequency by 340%"), fabricates technologies you have not used ("extensive experience with Terraform CDK"), or inflates job titles. The fabricated resume passes ATS but fails at the interview stage, or worse, gets you blacklisted from the company for dishonesty.

**Why it happens:** LLMs are designed to generate plausible-sounding text. When given a sparse resume and a demanding job description, the model fills gaps with plausible fabrications. AI hallucination rates remain at 0.7-5% even in frontier models (Vectara study, 2025). In resume context, even one hallucinated skill or metric is unacceptable. The problem is amplified when the LLM prompt says "optimize for this job description" without explicit guardrails.

**Consequences:** Blacklisted by employer. Caught in interview when asked about fabricated experience. Legal risk if the fabrication constitutes fraud (especially for roles requiring specific certifications). Destroyed credibility -- recruiters talk to each other.

**Prevention:**
1. The LLM must NEVER generate new facts. Provide it with a structured "source of truth" document containing all verifiable experience, metrics, and skills (the `CandidateProfile` model is a start but needs expansion to include specific achievements with real metrics).
2. Use a constrained prompt pattern: "Reorder and rephrase the following REAL experience to emphasize relevance to this job description. Do NOT add skills, metrics, or experience not present in the source document."
3. Implement a post-generation verification step: diff the tailored resume against the source document. Any skill, technology, or metric that appears in the output but not the input must be flagged and removed automatically.
4. Use structured output (JSON) for the LLM response, not free-form text. Define exact fields: summary, skills_to_highlight (must be subset of known skills), experience_order, emphasis_keywords. This constrains the generation space.
5. Keep a "never claim" list: technologies and skills the candidate explicitly does not have. Check output against this list.
6. Human review checkpoint: display a diff between base resume and tailored version before any submission.

**Detection (warning signs):**
- Tailored resume contains technology names not in `CandidateProfile.tech_keywords`
- Quantified metrics appear that were not in the source material
- Job titles or company names differ from source
- "Extensive experience with X" where X is not in the known skill set

**Phase:** Must be addressed when building the AI tailoring module (likely Phase 2). The verification step is non-negotiable and should be built simultaneously with generation, not retrofitted.

**Confidence:** HIGH -- hallucination rates verified via published research. Resume fabrication consequences well-documented in HR industry.

---

### Pitfall 4: Duplicate Applications Destroy Credibility

**What goes wrong:** The tool applies to the same job twice (or to the same company for the same role posted on Indeed AND Dice). The recruiter sees duplicate applications, which signals either desperation or bot usage. Some ATS systems auto-reject duplicate applicants.

**Why it happens:** The current dedup logic (`dedup_key = f"{company}::{title}"`) only operates within a single pipeline run. It does not persist across runs. If the tool is run on Monday and again on Wednesday, it will rediscover and potentially re-apply to the same jobs. The `jobs.db` SQLite database tracks discovered jobs but the `apply` flow does not check it before submitting. Additionally, the dedup key uses simple string normalization that can miss variants ("Google LLC" vs "Google" vs "Alphabet - Google").

**Consequences:** Recruiter marks candidate as spam. ATS auto-rejects future applications. Wastes daily application budget on already-applied jobs.

**Prevention:**
1. Before ANY application submission, query `jobs.db` for the dedup_key with `status = 'applied'`. If found, skip.
2. Record application attempts immediately (before waiting for confirmation), not just successful ones. Use status `'applying'` during submission, `'applied'` on success, `'apply_failed'` on failure.
3. Expand the dedup key to be more aggressive: normalize company names more thoroughly (strip "Inc", "LLC", "Corp", "Technologies", "Labs", common suffixes), and use fuzzy title matching (Levenshtein distance < 3 or token overlap > 80%).
4. Add a cross-platform dedup check: before applying on Dice, check if already applied on Indeed for the same company+title.
5. Store the exact URL applied through (not just platform), so manual applications can also be tracked via the web dashboard.

**Detection (warning signs):**
- The `discovered_jobs.json` file contains entries with `status: "applied"` that get re-scored in the next run
- Recruiter emails mention "we already received your application"
- Application count in tracker exceeds expectation

**Phase:** Must be addressed in Phase 1 (apply infrastructure) as part of the state management layer. The apply function must be idempotent by design.

**Confidence:** HIGH -- based on direct analysis of existing codebase (`orchestrator.py` and `db.py`).

---

### Pitfall 5: Session Expiry Mid-Application Causes Partial Submissions

**What goes wrong:** The tool starts filling a multi-step application form. Partway through, the session cookie expires server-side (Indeed sessions typically last 24 hours, Dice sessions vary). The form submit fails silently or redirects to a login page. The tool records "applied" status because it clicked submit, but the application never went through.

**Why it happens:** Persistent browser contexts cache cookies, but server-side sessions expire independently. The current code checks `is_logged_in()` only at startup (Phase 1), not before each application. If Phase 2 (search) takes 30+ minutes and Phase 4 (apply) happens afterward, the session may be stale.

**Consequences:** Phantom "applied" entries in the database. Candidate thinks they applied but didn't. Missed opportunities on high-scoring jobs.

**Prevention:**
1. Check `is_logged_in()` immediately before each application attempt, not just at pipeline start.
2. After form submission, verify the confirmation page actually loaded (look for "application received", "thank you", confirmation number). Do NOT assume submit button click equals successful application.
3. Implement a post-submit verification: check email for confirmation within 5 minutes, or check the ATS for application status.
4. Use `storageState` file modification time to detect stale sessions (if > 20 hours old, force re-login before apply phase).
5. If login is needed mid-pipeline, do it transparently rather than failing the entire run.

**Detection (warning signs):**
- Submit button click is followed by redirect to `/login` or `/auth`
- No confirmation page or confirmation email
- Page title changes to "Sign In" after submit

**Phase:** Phase 1 (apply infrastructure). Session management must be robust before any automated submissions.

**Confidence:** HIGH -- verified against Playwright GitHub issues (session cookie persistence is a known problem with `launch_persistent_context`).

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or degraded quality.

---

### Pitfall 6: God Object BasePlatform When Adding Apply Logic

**What goes wrong:** The `BasePlatform` abstract class currently has a clean interface: `login()`, `search()`, `get_job_details()`, `apply()`. When adding AI resume tailoring, custom question handling, multi-step form navigation, error recovery, and ATS-specific logic, everything gets stuffed into the platform subclass. `IndeedPlatform` grows from 200 lines to 2000 lines. Apply logic for Greenhouse (via RemoteOK redirects) gets tangled with Indeed-specific code.

**Why it happens:** The existing architecture couples "platform where job was discovered" with "platform where application is submitted." A job discovered on RemoteOK might need to be applied to via Greenhouse, Lever, or a custom career page. The current `BasePlatform.apply()` assumes the same browser context used for search is used for apply, but external ATS systems are entirely different websites.

**Prevention:**
1. Separate discovery from application. Create two interface hierarchies:
   - `SearchPlatform` (login, search, get_details) -- Indeed, Dice, RemoteOK
   - `ApplyHandler` (detect, can_handle, fill_form, submit) -- IndeedEasyApply, DiceEasyApply, GreenhouseAPI, LeverAPI, GenericBrowserForm
2. Use an `ApplyRouter` that examines the job's `apply_url` and routes to the correct `ApplyHandler`. This is the plugin extension point.
3. Keep `ApplyHandler` implementations small and focused: one handler per ATS, each under 200 lines.
4. Resist the urge to add apply logic to `BasePlatform`. The apply path is fundamentally different from the search path.

**Phase:** Phase 1 (architecture refactor) before building any apply handlers. Getting the interface boundaries right first prevents a costly refactor later.

**Confidence:** HIGH -- based on direct analysis of `base.py` and `orchestrator.py` architecture.

---

### Pitfall 7: Hardcoded Selectors Rot Within Weeks

**What goes wrong:** The tool works perfectly on day 1. Two weeks later, Indeed deploys a frontend update. The `div.job_seen_beacon` selector no longer matches. The `data-testid` attributes on Dice change to different naming conventions. Every external ATS updates independently. The tool silently returns zero results or fills wrong fields.

**Why it happens:** Web scraping against third-party sites is inherently fragile. The existing codebase already isolates selectors into separate files (`indeed_selectors.py`, `dice_selectors.py`), which is good practice. But the failure mode is silent: if a selector doesn't match, `query_selector_all` returns an empty list and the pipeline reports "0 jobs found" with no error.

**Prevention:**
1. Add selector health checks at the start of each search/apply session: verify at least one expected element exists on a known page. If zero matches, raise immediately with screenshot.
2. Implement a "selector confidence" system: if a page loads but key selectors return 0 results, try fallback selectors (CSS class, XPath, text content) and log which one worked.
3. For apply forms, never rely solely on selectors. Use the accessible label text, ARIA attributes, and surrounding text as fallbacks.
4. Add monitoring: track selector match rates over time. A sudden drop from 20 matches to 0 is a selector rot event.
5. Consider a selector versioning system: date-stamp each selector set so you know when they were last verified.

**Phase:** Ongoing concern. The selector isolation pattern is already in place. Add health checks in Phase 1 and monitoring in Phase 2.

**Confidence:** HIGH -- the MEMORY.md already documents multiple selector updates (Indeed and Dice), confirming this is an active problem.

---

### Pitfall 8: PDF Resume Generation Fails ATS Parsing

**What goes wrong:** The AI tailors the resume content perfectly, but the PDF generation process produces a file that ATS systems cannot parse. Images are embedded instead of text. Complex layouts with columns get scrambled. Headers/footers are invisible to parsers. The tailored resume scores lower in ATS than the original hand-crafted one.

**Why it happens:** Most Python PDF libraries (ReportLab, FPDF2, WeasyPrint) are designed for visual output, not ATS compatibility. They can produce beautiful PDFs that are unreadable by ATS parsers. Specific problems:
- Multi-column layouts are read left-to-right across both columns, scrambling chronology
- Tables in skills sections are parsed as random text fragments
- Custom fonts may not embed properly, becoming invisible
- Headers/footers are in separate PDF content streams that many parsers skip
- Workday specifically loses "more than half of content" during parsing of complex PDFs (per Resumly research)

**Prevention:**
1. Use single-column layout only. Never generate multi-column resumes.
2. Use standard system fonts only (Calibri, Arial, Times New Roman). Embed them explicitly.
3. No tables for skills sections. Use plain text with category labels and comma separation.
4. No images, logos, or decorative elements. Zero graphical content.
5. Contact info in body text, not headers/footers.
6. Generate DOCX as primary format (using `python-docx`), then convert to PDF. DOCX is better parsed by most ATS systems.
7. Validate generated PDFs: extract text with `PyPDF2` or `pdfminer.six` and verify all content is present and in correct order.
8. The existing ATS resume (`Patryk_Golabek_Resume_ATS.pdf`) was hand-optimized. Use its structure as the template for generated resumes, not a new design.

**Phase:** Phase 2 (AI resume tailoring). Build the validation step alongside generation.

**Confidence:** MEDIUM -- ATS parsing behavior sourced from Resumly and Indeed career advice; specific parser behavior varies by ATS vendor.

---

### Pitfall 9: LLM Cost Explosion from Per-Application Tailoring

**What goes wrong:** The tool calls an LLM to tailor the resume for every single application. At 10 applications/day with a 5-page resume + 2-page job description, each call is ~4K tokens input + ~2K tokens output. With GPT-4-class models at ~$30/1M input tokens, this seems cheap ($0.12/day). But then you add: cover letter generation, custom question answering (3-5 per application), retry logic for poor outputs, and the cost multiplies. More importantly, LLM latency (2-5 seconds per call) adds up when applying to 10 jobs with 5 custom questions each = 60 LLM calls = 2-5 minutes of just waiting.

**Why it happens:** Naive implementation calls the LLM for every piece of text that needs generation. No caching, no batching, no tiered model strategy.

**Prevention:**
1. Use a tiered model strategy: fast/cheap model (GPT-4o-mini, Claude Haiku) for custom question answers and field classification. Expensive model (GPT-4o, Claude Sonnet) only for resume tailoring.
2. Cache resume tailoring results by job-description-cluster, not individual job. If 5 jobs at different companies all want "Kubernetes platform engineer," the tailored resume is the same.
3. Batch custom questions: collect all questions for a job, send as one LLM call with structured output, not one call per question.
4. Pre-compute answers to common custom questions ("years of experience with X", "are you authorized to work in Y", "willing to relocate?") and store in a lookup table. Only use LLM for truly novel questions.
5. Set a per-application LLM budget (max 4 calls: resume tailor, cover letter, custom questions batch, retry). If exceeded, queue for manual review.

**Phase:** Phase 2 (AI integration). Design the caching and tiering strategy before implementing any LLM calls.

**Confidence:** MEDIUM -- cost estimates based on published pricing; actual costs depend on model choice and volume.

---

### Pitfall 10: Pluggable Architecture Becomes Plugin Graveyard

**What goes wrong:** The team builds an elaborate plugin system with abstract base classes, plugin discovery via `importlib`, registration decorators, and configuration YAML. Then only 3 plugins are ever written (Indeed, Dice, RemoteOK) -- the same three that existed before the refactor. The plugin infrastructure adds complexity without providing value. New contributors are confused by the indirection. Bug fixes require understanding 4 layers of abstraction instead of 1.

**Why it happens:** Over-engineering driven by "what if we need to add 20 platforms later." In practice, job search platforms are few, each requires deep customization, and the interfaces between them are not as uniform as imagined. Scrapy's architecture provides a good counter-example: it uses a signal/event system for loose coupling rather than deep class hierarchies.

**Prevention:**
1. Start with simple, explicit code. Three concrete implementations with shared utility functions beats an abstract plugin framework that serves three implementations.
2. The right abstraction is a protocol (Python `Protocol`), not an abstract base class. Define `SearchPlatform` and `ApplyHandler` as Protocols. Implementations don't need to inherit -- they just need to match the interface.
3. Only introduce plugin discovery (importlib, entry_points) when there are more than 5 implementations. Until then, an explicit registry dict is fine: `{"indeed": IndeedPlatform, "dice": DicePlatform}`.
4. The real extension point is `ApplyHandler` for ATS systems, not `SearchPlatform` for job boards. Focus pluggability effort there.
5. Keep the configuration simple: platform configs in a single YAML/TOML file, not per-plugin config files.

**Phase:** Phase 1 (architecture). Make the architecture decision before building apply handlers. Err on the side of simplicity.

**Confidence:** HIGH -- common software engineering anti-pattern, well-documented in plugin architecture literature.

---

## Minor Pitfalls

Mistakes that cause annoyance but are recoverable.

---

### Pitfall 11: Config Drift Between .env, CLAUDE.md, and CandidateProfile

**What goes wrong:** Candidate information lives in three places: `.env` (credentials), `CLAUDE.md` (full profile reference), and `models.py` `CandidateProfile` (runtime defaults). When the phone number changes, it gets updated in `CandidateProfile` but not in `CLAUDE.md`. When a new skill is added, it goes in `CLAUDE.md` but not in `tech_keywords`. The tool fills forms with stale data.

**Prevention:**
1. Single source of truth for candidate data: a `candidate.yaml` or `candidate.toml` file that `CandidateProfile` loads at runtime. `CLAUDE.md` references it, not duplicates it.
2. Add a validation step in Phase 0 that compares the loaded profile against the resume file (extract text, check that name/email/phone match).
3. Version the candidate profile: include a `last_updated` date field.

**Phase:** Phase 1 (externalized config). Low effort, high value.

---

### Pitfall 12: Screenshot Debug Folder Grows Unbounded

**What goes wrong:** The `debug_screenshots/` directory accumulates PNG files from every failed selector, every CAPTCHA encounter, every form fill verification. After a month of daily runs, it contains thousands of 1-3 MB files consuming gigabytes of disk space.

**Prevention:**
1. Auto-purge screenshots older than 7 days.
2. Compress screenshots to JPEG at 60% quality for debug purposes.
3. Include retention policy in the orchestrator's Phase 0 setup.

**Phase:** Minor housekeeping. Address in Phase 1 setup.

---

### Pitfall 13: Timezone and Date Format Mismatches in Application Forms

**What goes wrong:** Application forms ask "When can you start?" with a date picker expecting MM/DD/YYYY format. The tool fills "2026-02-15" (ISO format). Or a form asks "Available Date" and the current `start_date` value ("Available immediately / 2 weeks notice") doesn't match the expected date input type. Date pickers implemented as custom JavaScript widgets fail with `elem.fill()`.

**Prevention:**
1. Detect input type before filling: `type="date"` needs ISO format, text inputs need human-readable format, custom date pickers need click-based interaction.
2. For "start date" fields, compute an actual date (today + 14 days) rather than using the free-text value.
3. Test date filling against the three most common date picker libraries (native HTML, Flatpickr, Material UI).

**Phase:** Phase 2 (form filling improvements).

---

### Pitfall 14: Cover Letter Tone Mismatch Across Roles

**What goes wrong:** The LLM generates a cover letter optimized for a "Principal Engineer" role with heavy technical emphasis. The same template is used for an "Engineering Manager" role, which needs leadership/people emphasis. Both use identical tone, making applications feel generic.

**Prevention:**
1. Classify the role type before generating the cover letter: IC (individual contributor) vs. management vs. hybrid. Adjust emphasis accordingly.
2. Maintain 2-3 cover letter templates as prompts (technical IC, people leader, hybrid) and select based on job title classification.
3. Include specific company/role details in every cover letter (not just skills matching). "I noticed Company X recently launched Y" shows genuine interest.

**Phase:** Phase 2 (AI resume/cover letter generation).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Apply infrastructure (Phase 1) | Account ban from aggressive apply rate | Daily budget (5-10/day), session-level behavioral variation |
| Apply infrastructure (Phase 1) | Duplicate applications across runs | Pre-apply DB check, idempotent apply with status tracking |
| Apply infrastructure (Phase 1) | Session expiry mid-application | Pre-apply login check, post-submit confirmation verification |
| Architecture refactor (Phase 1) | Over-engineered plugin system | Use Protocols, explicit registry, defer plugin discovery |
| Architecture refactor (Phase 1) | God object platform classes | Separate SearchPlatform from ApplyHandler |
| AI resume tailoring (Phase 2) | Fabricated experience/skills | Source-of-truth constraint, post-generation diff, human review |
| AI resume tailoring (Phase 2) | PDF fails ATS parsing | Single-column, standard fonts, no tables/images, validation |
| AI resume tailoring (Phase 2) | LLM cost/latency explosion | Tiered models, caching by job cluster, batch custom questions |
| ATS form handlers (Phase 2-3) | Form diversity overwhelms generic filler | API-first (Greenhouse, Lever), then ATS-specific handlers |
| Ongoing | Selector rot (DOM changes) | Health checks, fallback selectors, monitoring |
| Ongoing | Config drift between profile sources | Single source of truth in YAML, validation in Phase 0 |

---

## Sources

### Verified (HIGH confidence)
- [Greenhouse Job Board API](https://developers.greenhouse.io/job-board.html) -- application submission endpoints and custom question structure
- [Lever Postings API](https://github.com/lever/postings-api) -- public application submission API
- [Playwright persistent context issues](https://github.com/microsoft/playwright/issues/36139) -- session cookie persistence bugs
- Direct codebase analysis: `base.py`, `models.py`, `orchestrator.py`, `form_filler.py`, `db.py`, `stealth.py`

### Cross-referenced (MEDIUM confidence)
- [GrackerAI: AI Job Hunting Automation 2025](https://gracker.ai/blog/ai-job-apply-bots-2025) -- Wonsulting shutdown, application rate data
- [Scale.jobs: ATS Rejects Most AI-Applied Resumes](https://scale.jobs/blog/ats-rejects-most-ai-applied-resumes) -- ATS parsing failure modes
- [Resumly: Formatting Resume PDFs](https://www.resumly.ai/blog/formatting-resume-pdfs-best-practices-to-avoid-ats-errors) -- PDF formatting pitfalls including Workday parsing losses
- [ScrapeOps: Make Playwright Undetectable](https://scrapeops.io/playwright-web-scraping-playbook/nodejs-playwright-make-playwright-undetectable/) -- behavioral fingerprinting detection
- [The Register: LLM Prompt Injection in Job Applications](https://www.theregister.com/2024/08/13/who_uses_llm_prompt_injection/) -- resume fabrication and ATS gaming risks
- [Vectara hallucination study](https://medium.com/@markus_brinsa/hallucination-rates-in-2025-accuracy-refusal-and-liability-aa0032019ca1) -- LLM hallucination rate benchmarks (0.7-25%)

### Single-source (LOW confidence -- needs validation)
- Indeed DSA transparency report claim about "anomaly detection and machine learning" for bot detection -- verified the report exists but specific detection methods are not public
- Workday "loses more than half of content" during PDF parsing -- single source (Resumly), may be version/config dependent
