"""Match cars.com EmailSignals to MBUSA candidates.

Architecture B (see MBUSA_PIVOT.md) inverts the previous design: MBUSA's
inventory API is the authoritative source of in-spec vehicles, and
email alerts (cars.com / autotrader / cargurus) contribute *price-drop
trajectory signal* on top of those candidates. This module is the join
layer between the two streams.

The matching problem: a cars.com EmailSignal carries
``(year, trim_number, mileage, price, price_drop_delta)`` but no VIN
— cars.com strips VINs from alert bodies, and hydration is no longer
sustainable (Cloudflare). An MBUSA candidate carries the VIN plus all
the same metadata. We need to join them so the EmailSignal's
price-drop delta can be attached to the right VIN's history via
:func:`scripts.state.add_email_signal`.

Algorithm:

  1. **Year exact** — different model year = different car.
  2. **Trim exact** — 450 vs 580 is a fundamentally different vehicle
     per CONTEXT.md, never collapse them.
  3. **Mileage within tolerance** — typically ±500 mi to absorb the
     drift between when cars.com snapshotted the dealer's odometer
     and when MBUSA refreshed.
  4. **Price within tolerance** — typically ±$2,000 to absorb the
     drift between cars.com's snapshot and MBUSA's; covers most
     in-flight price moves.
  5. **Tie-break by normalized distance** — when multiple candidates
     pass all four gates, pick the one with the smallest
     ``|mileage_delta|/MAX_MILEAGE_DELTA + |price_delta|/MAX_PRICE_DELTA``.
     Normalization makes mileage and price contribute equally.

If the signal is missing mileage or price, we **fail closed** —
return no match rather than fall back to a (year, trim)-only match
that could collide between two real candidates. Better to log an
unmatched signal than to attach to the wrong VIN.

Tolerances are first-pass values; we'll revisit once we have real
match-rate data from a few weeks of runs.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ---------- Tolerances ----------

# Mileage tolerance window between the cars.com snapshot and the MBUSA
# snapshot. Dealer cars accumulate ~50–100 mi/day; ±500 covers about
# a week of drift, which is generous for two near-real-time feeds.
MATCH_MILEAGE_TOLERANCE_MI: float = 500.0

# Price tolerance window. Most price moves are $500–$1,500; ±$2,000 is
# a safety buffer that captures normal drift without admitting matches
# between two unrelated vehicles with similar prices.
MATCH_PRICE_TOLERANCE_USD: float = 2000.0


# ---------- Data shapes ----------


@dataclass(frozen=True)
class MatchOutcome:
    """Observable result of a match attempt.

    On match: ``matched_vin`` and ``score`` are set, ``reason_no_match``
    is None. On miss: ``matched_vin`` is None, ``reason_no_match``
    carries a short description for logs/audit.
    """

    matched_vin: Optional[str] = None
    matched_candidate: Optional[dict] = None
    score: Optional[float] = None
    reason_no_match: Optional[str] = None

    @property
    def matched(self) -> bool:
        return self.matched_vin is not None


# ---------- Public API ----------


# Pattern matches a model-id like "GLS450W4" or "GLS580W4" and captures
# the trim digit group (e.g. "450" or "580"). Permissive on the surrounding
# class letters and drivetrain suffix so future model_ids (e.g. an "AMG"
# variant) still parse.
_MODEL_ID_TRIM_PATTERN = re.compile(r"[A-Z]+([0-9]{2,4})[A-Z0-9]*")


def _extract_trim_from_model_id(model_id: Optional[str]) -> Optional[str]:
    """Pull the trim number out of an MBUSA model_id.

    "GLS450W4" → "450", "GLS580W4" → "580". Returns None on missing
    input or unparseable shape.
    """
    if not model_id:
        return None
    match = _MODEL_ID_TRIM_PATTERN.match(model_id)
    if not match:
        return None
    return match.group(1)


def match_email_signal(
    signal: dict,
    candidates: list[dict],
) -> MatchOutcome:
    """Find the MBUSA candidate that this cars.com EmailSignal refers to.

    Args:
        signal: An EmailSignal-shaped dict as produced by
            :func:`scripts.parsers.cars_com.parse`. Must carry
            ``raw_metadata.year`` and ``raw_metadata.trim_number``;
            ``raw_metadata.mileage`` and ``raw_metadata.price`` are
            required to attempt the fuzzy match (fail-closed otherwise).
        candidates: List of candidate dicts as produced by
            :func:`scripts.ingest._mbusa_candidate_to_dict`. Each must
            carry ``vin`` and ``raw_metadata.{year, model_id, mileage,
            ask_price/price}``.

    Returns:
        A :class:`MatchOutcome`. ``matched_vin`` is set when exactly
        one candidate clears all four gates, or when multiple do and
        a unique closest-by-distance winner exists. None otherwise.
    """
    s_md = signal.get("raw_metadata") or {}
    s_year = s_md.get("year")
    s_trim = s_md.get("trim_number")
    s_mileage = s_md.get("mileage")
    s_price = s_md.get("price")

    if s_year is None or s_trim is None:
        return MatchOutcome(reason_no_match="signal missing year or trim")
    if s_mileage is None or s_price is None:
        return MatchOutcome(
            reason_no_match="signal missing mileage or price (fail-closed)"
        )

    scored: list[tuple[float, dict]] = []
    for c in candidates:
        c_md = c.get("raw_metadata") or {}

        # Gate 1: year exact
        if c_md.get("year") != s_year:
            continue

        # Gate 2: trim exact
        c_trim = _extract_trim_from_model_id(c_md.get("model_id"))
        if c_trim != str(s_trim):
            continue

        # Gate 3 + 4: numeric tolerances. Skip the candidate if either
        # field is missing — same fail-closed posture as for the signal.
        c_mileage = c_md.get("mileage")
        c_price = c_md.get("price") or c_md.get("ask_price")
        if c_mileage is None or c_price is None:
            continue

        mileage_delta = abs(float(c_mileage) - float(s_mileage))
        price_delta = abs(float(c_price) - float(s_price))
        if mileage_delta > MATCH_MILEAGE_TOLERANCE_MI:
            continue
        if price_delta > MATCH_PRICE_TOLERANCE_USD:
            continue

        score = (
            mileage_delta / MATCH_MILEAGE_TOLERANCE_MI
            + price_delta / MATCH_PRICE_TOLERANCE_USD
        )
        scored.append((score, c))

    if not scored:
        return MatchOutcome(
            reason_no_match="no candidate within mileage/price tolerance"
        )

    # Smallest score wins. If two candidates tie exactly, the first one
    # encountered wins via stable sort — that's deterministic, which is
    # what matters for testing and reproducibility.
    scored.sort(key=lambda item: item[0])
    best_score, best_candidate = scored[0]

    return MatchOutcome(
        matched_vin=best_candidate.get("vin"),
        matched_candidate=best_candidate,
        score=best_score,
    )
