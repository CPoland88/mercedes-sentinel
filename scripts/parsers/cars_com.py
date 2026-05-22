"""Cars.com saved-search email parser.

Handles the per-vehicle block template used by Cars.com price-drop alerts
and (likely) new-listing alerts. Each vehicle in the email body has:

  - Title:        "YYYY Mercedes-Benz GLS NNN 4MATIC"
  - Listing URL:  https://www.cars.com/vehicledetail/<uuid>?aff=...
                  (appears TWICE per vehicle — top + "View details" link)
  - Mileage:      "N mi."   (note abbreviation — not "miles")
  - Optional delta: "↓ $N price drop"
  - Ask price:    "$N"

The email body contains NO VINs — Cars.com strips them from alerts and
keeps them behind the vehicledetail URL. Hydration to fetch VIN, dealer,
color, packages, and CPO from the listing page lands in the next commit
(see scripts/hydrate.py for the helper).

This commit emits per-block candidates with `vin=None`. ingest.py will
warn-and-drop them (its VIN check is unchanged), which is intentional:
this is the bridge state between the pre-existing stub parser (which
returned [] on every cars.com alert) and the hydrated version (next
commit, which will populate `vin` from the hydrated listing page).

Block-detection algorithm:

  1. Find every `vehicledetail/<uuid>` URL in the text/plain body.
     Group by UUID — each unique UUID is one vehicle. The duplicate
     URL per vehicle is its own boundary signal; we use the first and
     last positions to bracket the block.
  2. For each unique vehicle, walk backward from its first URL to the
     closest title-line match. Title plus [first_url_start, last_url_end]
     defines the block.
  3. Extract mileage, price, and price-drop delta from inside the
     block, isolated from email-footer noise.

Falls back to `parsers.fallback` when no `vehicledetail/` URLs are
present — for non-standard Cars.com formats (weekly market reports,
account notifications) the fallback still surfaces any VINs and URLs
in the body so the alert doesn't get silently dropped.
"""
from __future__ import annotations

import re
from email.message import Message
from typing import List, Optional

from . import fallback


# ---- Patterns ----

# Title line for a Mercedes-Benz GLS listing. Captures year, trim number,
# drivetrain. CONTEXT.md is GLS-only, so this regex is GLS-only.
TITLE_PATTERN = re.compile(
    r"(\d{4})\s+Mercedes-Benz\s+GLS\s+(\d+)(?:\s+(4MATIC|AMG))?",
    re.IGNORECASE,
)

# Cars.com per-vehicle URL. Captures the path-segment after
# `/vehicledetail/` as the per-vehicle ID for dedup. Real cars.com IDs
# observed are hex GUIDs, but the pattern stays permissive
# ([A-Za-z0-9-]+) so a future ID-format change doesn't silently drop
# every alert. The trailing `[^\s<>"')\]]*` consumes the query string
# and stops at the angle-bracket terminator email clients use.
VEHICLEDETAIL_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?cars\.com/vehicledetail/([A-Za-z0-9-]+)[^\s<>\"')\]]*",
    re.IGNORECASE,
)

# Mileage — accept "mi", "mi.", "mile", "miles". The trailing negative
# lookahead `(?![a-zA-Z])` prevents matches inside words like "milestones".
MILEAGE_PATTERN = re.compile(
    r"([\d]{1,3}(?:,\d{3})+|\d{4,6})\s*mi(?:le)?s?\.?(?![a-zA-Z])",
    re.IGNORECASE,
)

# Price-drop delta — "↓ $1,245 price drop" or "$1,245 price drop"
PRICE_DROP_PATTERN = re.compile(
    r"\$\s*([\d]{1,3}(?:,\d{3})*|\d+)\s*price\s*drop",
    re.IGNORECASE,
)

# Ask price — any "$N,NNN..." amount with commas. The block isolates
# this regex from email-footer dollar amounts.
PRICE_PATTERN = re.compile(r"\$\s*([\d]{1,3}(?:,\d{3})+)")

# Cars.com deal-badge label (present on some alert types, not on
# price-drop emails). Kept from the pre-existing parser.
DEAL_BADGE_PATTERN = re.compile(
    r"\b(Great Deal|Good Deal|Fair Deal|High Price|Overpriced)\b",
    re.IGNORECASE,
)


# ---- Internals ----

def _strip_int(s: str) -> int:
    return int(s.replace(",", ""))


def _get_text_plain_body(msg: Message) -> str:
    """Return the email's text/plain part decoded to a string.

    Cars.com per-vehicle blocks live cleanly in text/plain. We
    deliberately do NOT use `fallback.get_email_body` here because that
    helper concatenates the HTML-stripped body too, which causes every
    title and URL to appear twice and confuses block-boundary detection.
    Empty string on any failure.
    """
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        return ""
    if msg.get_content_type() == "text/plain":
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def _find_title_before(title_matches, position: int):
    """Return the latest title match whose start is <= position, or None.

    title_matches must be in document order (the result of finditer).
    """
    best = None
    for m in title_matches:
        if m.start() <= position:
            best = m
        else:
            break
    return best


def _build_candidate(
    title_match,
    listing_url: str,
    block: str,
) -> dict:
    """Assemble the per-vehicle candidate dict.

    `block` is the substring [title.start, last_url.end] for this
    vehicle. Restricting metadata extraction to the block keeps
    email-footer dollar amounts from being misread as the asking price.
    """
    year = int(title_match.group(1))
    trim_number = title_match.group(2)
    drivetrain = title_match.group(3)

    metadata: dict = {
        "year": year,
        "trim_number": trim_number,
    }
    if drivetrain:
        metadata["drivetrain"] = drivetrain.upper()

    mileage_match = MILEAGE_PATTERN.search(block)
    if mileage_match:
        metadata["mileage"] = _strip_int(mileage_match.group(1))

    # Extract the delta FIRST so we can exclude it from the ask-price
    # candidates. Without this, the delta amount (e.g. $1,245) would
    # be one of the prices we consider for the ask.
    price_drop_match = PRICE_DROP_PATTERN.search(block)
    delta: Optional[int] = None
    if price_drop_match:
        delta = _strip_int(price_drop_match.group(1))
        metadata["price_drop_delta"] = delta

    prices = [_strip_int(m.group(1)) for m in PRICE_PATTERN.finditer(block)]
    ask_candidates = [p for p in prices if p != delta]
    if ask_candidates:
        metadata["price"] = max(ask_candidates)
    elif prices:
        # Degenerate case: only the delta amount was found as a price.
        # Surface it anyway so downstream sees something.
        metadata["price"] = max(prices)

    badge_match = DEAL_BADGE_PATTERN.search(block)
    if badge_match:
        metadata["deal_badge"] = badge_match.group(1)

    return {
        "vin": None,  # Populated by hydration in the next commit.
        "listing_url": listing_url,
        "provider": "cars_com",
        "parser": "cars_com",
        "raw_metadata": metadata,
    }


def _fallback_with_provider_tag(msg: Message) -> List[dict]:
    """Use the regex fallback parser, tag results as cars_com."""
    candidates = fallback.parse(msg)
    for c in candidates:
        c["provider"] = "cars_com"
        c["parser_fallback"] = True
    return candidates


# ---- Public API ----

def parse(msg: Message) -> List[dict]:
    body = _get_text_plain_body(msg)
    if not body:
        # No text/plain part — defer to fallback against the full message.
        return _fallback_with_provider_tag(msg)

    url_matches = list(VEHICLEDETAIL_URL_PATTERN.finditer(body))
    if not url_matches:
        # Non-standard format (weekly digest, account notice). Try
        # fallback so the alert isn't silently dropped.
        return _fallback_with_provider_tag(msg)

    # Group URL matches by UUID, preserving order of first occurrence.
    # Insertion-ordered dict is enough — we want the same order the
    # vehicles appear in the email.
    uuid_to_matches: dict = {}
    for m in url_matches:
        uuid = m.group(1).lower()
        uuid_to_matches.setdefault(uuid, []).append(m)

    title_matches = list(TITLE_PATTERN.finditer(body))

    candidates: List[dict] = []
    for uuid, matches in uuid_to_matches.items():
        first_url_match = matches[0]
        last_url_match = matches[-1]

        title_match = _find_title_before(title_matches, first_url_match.start())
        if title_match is None:
            # URL without a preceding title — not a vehicle block, skip.
            continue

        block = body[title_match.start():last_url_match.end()]
        listing_url = first_url_match.group(0)
        candidates.append(_build_candidate(title_match, listing_url, block))

    return candidates
