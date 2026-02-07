# Phase 2: Platform Architecture - Context

**Gathered:** 2026-02-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Adding a new job board requires creating one file that implements a protocol -- no changes to the orchestrator, config, or scoring pipeline. Existing Indeed, Dice, and RemoteOK adapters migrate from BasePlatform ABC inheritance to Protocol-based contracts with a decorator-driven registry.

</domain>

<decisions>
## Implementation Decisions

### Protocol contracts
- Two separate protocols: BrowserPlatform and APIPlatform -- browser ones handle login/sessions, API ones handle HTTP clients
- Core method contract: search(query) returns raw cards, extract(card) returns Job model, apply(job) handles application flow
- Platforms return Pydantic Job models from extract -- orchestrator gets clean typed data
- apply() is part of the platform protocol -- each platform owns its own apply flow (Indeed Easy Apply, Dice Easy Apply, RemoteOK external redirect)

### Registry & discovery
- Decorator-based registration: @register_platform('indeed') on the class definition -- importing the module auto-registers it
- Config controls active platforms via explicit enable list: `enabled_platforms: [indeed, dice, remoteok]` in config.yaml -- only listed ones run
- Registry validates protocol compliance at registration time -- missing methods cause an import error immediately (fail fast)
- Decorator supports metadata: @register_platform('indeed', name='Indeed', type='browser', capabilities=['easy_apply']) -- useful for dashboard and CLI output

### Platform lifecycle
- Shared Playwright browser instance, each platform gets its own BrowserContext with isolated cookies/sessions
- If one platform fails (e.g., login failure), log the error, skip it, continue with remaining platforms -- partial results are still valuable
- Explicit init phase: orchestrator calls platform.init() upfront for all platforms, then runs searches -- fails early if auth is broken
- Context manager pattern: platforms implement __enter__/__exit__ -- orchestrator uses `with platform:` to ensure cleanup

### Migration strategy
- Big bang: build protocols + registry, then migrate all three adapters at once in one plan -- clean break, no dual support
- Remove BasePlatform ABC immediately once all adapters use protocols -- no dead code, no deprecated shims
- Adapter migration and orchestrator refactor happen in the same plan -- one coherent change, avoids intermediate states
- No end-to-end verification run required -- code review is sufficient

### Claude's Discretion
- Exact protocol method signatures and type hints
- How the decorator internally stores and validates registrations
- BrowserContext configuration details (viewport, user agent inheritance)
- Error logging format and platform skip reporting

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches. The roadmap's success criteria (Protocol-based contracts, auto-discovery via decorator, no if/elif branching in orchestrator, identical adapter behavior after migration) define the target clearly.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 02-platform-architecture*
*Context gathered: 2026-02-07*
