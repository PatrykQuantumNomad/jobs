"""Unified salary parser -- normalizes salary strings from all platforms.

Replaces the three platform-specific ``_parse_salary()`` functions in
``platforms/indeed.py``, ``platforms/dice.py``, and implicit handling in
``platforms/remoteok.py`` with a single module.

Handles formats:
  - "$150,000 - $200,000"  (Indeed range)
  - "$85/hr" or "$85 an hour"  (Indeed hourly, x2080)
  - "USD 224,400.00 - 283,800.00 per year"  (Dice verbose)
  - "$175000"  (Dice short)
  - "$150K - $200K"  (K notation)
  - "150000-180000 CAD"  (currency suffix)
  - Monthly rates (x12)
  - Raw ints from RemoteOK API
  - None/empty -> NormalizedSalary with all None
"""

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOURLY_MULTIPLIER = 2080  # 40 hrs/wk * 52 wk
MONTHLY_MULTIPLIER = 12

# Currency detection -- order matters: check specific patterns before generic "$"
_CURRENCY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("CAD", re.compile(r"CAD|C\$|CA\$", re.IGNORECASE)),
    ("GBP", re.compile(r"GBP|\u00a3", re.IGNORECASE)),
    ("EUR", re.compile(r"EUR|\u20ac", re.IGNORECASE)),
    # USD last -- "$" alone defaults to USD
    ("USD", re.compile(r"USD|US\$|\$", re.IGNORECASE)),
]

_CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",
    "CAD": "C$",
    "EUR": "EUR",
    "GBP": "GBP",
}

# K-notation pattern: e.g. "150K", "200k"
_K_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*[kK]")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class NormalizedSalary:
    """Platform-agnostic salary representation.

    All monetary values are annual in the *original* currency (no conversion).
    """

    min_annual: int | None = None
    max_annual: int | None = None
    currency: str = "USD"
    raw: str = ""
    display: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_salary(
    text: str | None,
    default_currency: str = "USD",
) -> NormalizedSalary:
    """Parse a salary string into a :class:`NormalizedSalary`.

    Returns a ``NormalizedSalary`` with ``min_annual=None`` when *text* is
    empty or unparseable.
    """
    if not text or not text.strip():
        return NormalizedSalary()

    raw = text.strip()

    # -- Detect currency ---------------------------------------------------
    currency = default_currency
    for curr, pattern in _CURRENCY_PATTERNS:
        if pattern.search(raw):
            currency = curr
            break

    # -- Detect period multiplier ------------------------------------------
    lower = raw.lower()
    if "hour" in lower or "/hr" in lower:
        multiplier = HOURLY_MULTIPLIER
    elif "month" in lower:
        multiplier = MONTHLY_MULTIPLIER
    else:
        multiplier = 1  # assume annual

    # -- Handle K-notation explicitly before generic number extraction -----
    k_matches = _K_PATTERN.findall(raw)
    if k_matches:
        values: list[int] = []
        for n in k_matches[:2]:
            val = float(n) * 1000
            values.append(int(val * multiplier))
        min_val = min(values)
        max_val = max(values) if len(values) > 1 else min_val
        display = _format_display(min_val, max_val, currency)
        return NormalizedSalary(
            min_annual=min_val,
            max_annual=max_val,
            currency=currency,
            raw=raw,
            display=display,
        )

    # -- Generic numeric extraction ----------------------------------------
    # Strip currency symbols/words before extracting numbers
    cleaned = re.sub(
        r"USD|CAD|EUR|GBP|US\$|CA\$|C\$|\$|\u00a3|\u20ac",
        "",
        raw,
        flags=re.IGNORECASE,
    )
    # Remove commas inside numbers
    cleaned = cleaned.replace(",", "")
    nums = re.findall(r"\d+(?:\.\d+)?", cleaned)

    if not nums:
        return NormalizedSalary(raw=raw)

    values = []
    for n in nums[:2]:
        val = float(n)
        # Small values without explicit K or hourly/monthly notation are
        # likely K-shorthand (e.g. "150" meaning $150,000).
        if val < 1000 and multiplier == 1:
            val *= 1000
        values.append(int(val * multiplier))

    min_val = min(values)
    max_val = max(values) if len(values) > 1 else min_val

    display = _format_display(min_val, max_val, currency)
    return NormalizedSalary(
        min_annual=min_val,
        max_annual=max_val,
        currency=currency,
        raw=raw,
        display=display,
    )


def parse_salary_ints(
    min_val: int | None,
    max_val: int | None,
    currency: str = "USD",
) -> NormalizedSalary:
    """Build a :class:`NormalizedSalary` from raw integers (RemoteOK API).

    Handles RemoteOK quirk where ``salary_max`` may be 0 when
    ``salary_min`` > 0.
    """
    if min_val is None and max_val is None:
        return NormalizedSalary()

    # RemoteOK quirk: salary_max = 0 when salary_min > 0
    effective_min = min_val or None
    effective_max = max_val or None
    if effective_max is None and effective_min is not None:
        effective_max = effective_min

    display = _format_display(
        effective_min or 0,
        effective_max or effective_min or 0,
        currency,
    )
    return NormalizedSalary(
        min_annual=effective_min,
        max_annual=effective_max,
        currency=currency,
        display=display,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _format_display(min_val: int, max_val: int, currency: str) -> str:
    """Format as compact range: ``$150K-$200K USD/yr``."""
    if min_val == 0 and max_val == 0:
        return ""
    symbol = _CURRENCY_SYMBOLS.get(currency, "$")
    min_k = f"{symbol}{min_val // 1000}K"
    if min_val == max_val:
        return f"{min_k} {currency}/yr"
    max_k = f"{symbol}{max_val // 1000}K"
    return f"{min_k}-{max_k} {currency}/yr"
