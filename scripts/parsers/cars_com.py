"""Cars.com saved-search email parser.

Stub-quality v1: defers to fallback for VIN+URL extraction, layers
price + mileage + deal-badge metadata from regex over the body. Sharpen
with real .eml fixtures.
"""
from __future__ import annotations

import re
from email.message import Message
from typing import List

from . import fallback

PRICE_PATTERN = re.compile(r"\$([\d]{1,3}(?:,\d{3})+)")
MILEAGE_PATTERN = re.compile(r"([\d]{1,3}(?:,\d{3})+|\d{4,6})\s*miles?", re.IGNORECASE)
DEAL_BADGE_PATTERN = re.compile(
    r"\b(Great Deal|Good Deal|Fair Deal|High Price|Overpriced)\b",
    re.IGNORECASE,
)


def _strip_int(s: str) -> int:
    return int(s.replace(",", ""))


def parse(msg: Message) -> List[dict]:
    candidates = fallback.parse(msg)
    body = fallback.get_email_body(msg)

    metadata: dict = {}
    price_match = PRICE_PATTERN.search(body)
    if price_match:
        metadata["price"] = _strip_int(price_match.group(1))
    mileage_match = MILEAGE_PATTERN.search(body)
    if mileage_match:
        metadata["mileage"] = _strip_int(mileage_match.group(1))
    badge_match = DEAL_BADGE_PATTERN.search(body)
    if badge_match:
        metadata["deal_badge"] = badge_match.group(1)

    for c in candidates:
        c["provider"] = "cars_com"
        c["parser"] = "cars_com"
        if metadata:
            c["raw_metadata"] = metadata

    return candidates
