"""Two-pass fuzzy deduplication engine for job listings.

Pass 1: Exact ``dedup_key()`` match (fast path, catches ~90% of duplicates).
Pass 2: Fuzzy company-name matching within same-title groups using
``rapidfuzz.fuzz.token_sort_ratio`` with a conservative threshold.

When merging, the most recent posting (by ``posted_date``) is kept and
aliases are recorded in ``job.company_aliases``.
"""

from rapidfuzz import fuzz

from core.models import Job

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Conservative threshold -- only merge very close variants.
# "Google" vs "Google LLC" -> 100 after suffix stripping (exact).
# "Google" vs "Alphabet"   -> 0   after suffix stripping (no match).
FUZZY_COMPANY_THRESHOLD = 90

# Suffixes to strip before comparison (lowercase, order: longest first).
_COMPANY_SUFFIXES = (
    " incorporated",
    " corporation",
    " company",
    " corp.",
    " corp",
    " inc.",
    " inc",
    " llc",
    " ltd.",
    " ltd",
    " co.",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fuzzy_deduplicate(jobs: list[Job]) -> list[Job]:
    """Deduplicate *jobs* in two passes: exact key, then fuzzy company name.

    Returns a new list with duplicates merged.  The winner of each merge
    has ``company_aliases`` populated with the names of merged variants.
    """
    if not jobs:
        return []

    # -- Pass 1: exact dedup_key match (fast) ------------------------------
    by_key: dict[str, Job] = {}
    for job in jobs:
        key = job.dedup_key()
        if key in by_key:
            existing = by_key[key]
            if _prefer(job, existing):
                # Carry over aliases from the one being replaced
                aliases = set(existing.company_aliases)
                if existing.company != job.company:
                    aliases.add(existing.company)
                job.company_aliases = list(aliases)
                by_key[key] = job
            else:
                # Record the new one as an alias on the existing winner
                if job.company != existing.company and job.company not in existing.company_aliases:
                    existing.company_aliases.append(job.company)
        else:
            by_key[key] = job

    unique = list(by_key.values())

    # -- Pass 2: fuzzy company match within same-title groups --------------
    by_title: dict[str, list[Job]] = {}
    for job in unique:
        title_key = job.title.lower().strip()
        by_title.setdefault(title_key, []).append(job)

    result: list[Job] = []
    for group in by_title.values():
        if len(group) == 1:
            result.append(group[0])
        else:
            result.extend(_fuzzy_merge_group(group))

    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _prefer(candidate: Job, existing: Job) -> bool:
    """Return True if *candidate* is a better representative than *existing*.

    Prefers: more recent posting, longer description, has salary data.
    """
    # More recent posting wins
    c_date = candidate.posted_date or ""
    e_date = existing.posted_date or ""
    if c_date > e_date:
        return True
    if c_date < e_date:
        return False

    # Longer description wins
    if len(candidate.description) > len(existing.description):
        return True

    # Has salary wins
    return candidate.salary_min is not None and existing.salary_min is None


def _fuzzy_merge_group(jobs: list[Job]) -> list[Job]:
    """Within a group of same-title jobs, merge fuzzy company matches."""
    merged: list[Job] = []
    used: set[int] = set()

    for i, job in enumerate(jobs):
        if i in used:
            continue

        cluster = [job]
        norm_i = _normalize_company(job.company)

        for j in range(i + 1, len(jobs)):
            if j in used:
                continue
            norm_j = _normalize_company(jobs[j].company)

            # Fast path: exact match after normalization
            if norm_i == norm_j:
                cluster.append(jobs[j])
                used.add(j)
                continue

            # Fuzzy match
            score = fuzz.token_sort_ratio(norm_i, norm_j)
            if score >= FUZZY_COMPANY_THRESHOLD:
                cluster.append(jobs[j])
                used.add(j)

        # Keep most recent posting, record merge trail
        winner = max(cluster, key=lambda j: j.posted_date or "")
        if len(cluster) > 1:
            aliases: set[str] = set(winner.company_aliases)
            for j in cluster:
                if j.company != winner.company:
                    aliases.add(j.company)
                # Also include any aliases from merged jobs
                for alias in j.company_aliases:
                    if alias != winner.company:
                        aliases.add(alias)
            winner.company_aliases = sorted(aliases)

        merged.append(winner)

    return merged


def _normalize_company(name: str) -> str:
    """Strip common corporate suffixes for comparison."""
    lower = name.lower().strip()
    for suffix in _COMPANY_SUFFIXES:
        if lower.endswith(suffix):
            lower = lower[: -len(suffix)]
    return lower.strip().rstrip(",")
