"""CarGurus saved-search email parser.

CarGurus alerts carry the richest metadata of the three providers:
asking price, Instant Market Value (IMV), days-on-lot, deal badge
(Great/Good/Fair/High/Overpriced), mileage.

This v1 parser uses regex over the email body. With real .eml fixtures
in scripts/tests/fixtures/, the patterns will sharpen against actual
CarGurus email structure. Until then, it falls through to fallback for
VIN+URL extraction and adds whatever metadata the regexes catch.
"""
from __future__ import annotations

import re
from email.message import Message
from typing import List

from . import fallback

PRICE_PATTERN = re.compile(r"\$([\d]{1,3}(?:,\d{3})+)")
IMV_PATTERN = re.compile(
    r"(?:Instant Market Value|IMV)[^\$]*\$([\d]{1,3}(?:,\d{3})+)",
    re.IGNORECASE,
)
# Mileage: number followed by "miles" on the SAME line (no \s, which would
# match newlines) and with a word boundary so "Mileage:" isn't picked up
# as a `mile` match on the IMV figure that precedes it.
MILEAGE_PATTERN = re.compile(
    r"([\d]{1,3}(?:,\d{3})+|\d{4,6})[ \t]*miles?\b",
    re.IGNORECASE,
)
DAYS_PATTERN = re.compile(r"(\d+)\s*days?\s*(?:on|at|listed)", re.IGNORECASE)
DEAL_BADGE_PATTERN = re.compile(
    r"\b(Great Deal|Good Deal|Fair Deal|High Price|Overpriced)\b",
    re.IGNORECASE,
)


def _strip_int(s: str) -> int:
    return int(s.replace(",", ""))


def parse(msg: Message) -> List[dict]:
    """Parse a CarGurus alert email.

    Note on multi-car emails: CarGurus alerts typically list one car per
    email. If multiple cars appear, the metadata extracted here is body-
    wide and applied to every candidate — which is wrong. Flagged for
    future work once real fixtures expose the multi-car case.
    """
    candidates = fallback.parse(msg)
    body = fallback.get_email_body(msg)

    metadata = _extract_metadata(body)

    for c in candidates:
        c["provider"] = "cargurus"
        c["parser"] = "cargurus"
        # Layer per-listing metadata only when extracted
        if metadata:
            c["raw_metadata"] = metadata

    return candidates


def _extract_metadata(body: str) -> dict:
    metadata: dict = {}

    # IMV first so the generic price regex doesn't pick up the IMV value.
    imv_match = IMV_PATTERN.search(body)
    if imv_match:
        metadata["imv"] = _strip_int(imv_match.group(1))

    # First $-prefixed amount that isn't the IMV
    if imv_match:
        before_imv = body[:imv_match.start()]
        after_imv = body[imv_match.end():]
        price_search_body = before_imv + after_imv
    else:
        price_search_body = body
    price_match = PRICE_PATTERN.search(price_search_body)
    if price_match:
        metadata["price"] = _strip_int(price_match.group(1))

    mileage_match = MILEAGE_PATTERN.search(body)
    if mileage_match:
        metadata["mileage"] = _strip_int(mileage_match.group(1))

    days_match = DAYS_PATTERN.search(body)
    if days_match:
        metadata["days_on_lot"] = int(days_match.group(1))

    badge_match = DEAL_BADGE_PATTERN.search(body)
    if badge_match:
        metadata["deal_badge"] = badge_match.group(1)

    return metadata
