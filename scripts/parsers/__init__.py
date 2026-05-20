"""Email parsers for saved-search alerts.

Each provider module exposes `parse(msg: email.message.Message) -> List[dict]`
returning candidate dicts with at minimum {vin, listing_url, provider}.

The fallback parser extracts any VIN-like strings + URLs via regex and is
used when provider detection fails or a provider parser raises.
"""
from __future__ import annotations

import email
import logging
from email.message import Message
from typing import List, Optional

from . import autotrader, cargurus, cars_com, fallback

logger = logging.getLogger(__name__)

# Provider domain → parser module. Sender address is checked against each key.
PROVIDER_PARSERS = {
    "cargurus.com": ("cargurus", cargurus),
    "autotrader.com": ("autotrader", autotrader),
    "cars.com": ("cars_com", cars_com),
}


def detect_provider(msg: Message) -> Optional[str]:
    """Return provider name based on the From header, or None."""
    sender = (msg.get("From", "") or "").lower()
    for domain, (name, _) in PROVIDER_PARSERS.items():
        if domain in sender:
            return name
    return None


def parse(email_bytes: bytes) -> List[dict]:
    """Parse an email and return a list of candidate dicts.

    Each candidate has at minimum: vin, listing_url, provider, raw_metadata,
    parser (which parser successfully extracted it).
    """
    msg = email.message_from_bytes(email_bytes)
    provider = detect_provider(msg)

    candidates: List[dict] = []
    parser_succeeded = False

    if provider:
        # Find the module for this provider
        for domain, (name, module) in PROVIDER_PARSERS.items():
            if name == provider:
                try:
                    candidates = module.parse(msg)
                    parser_succeeded = True
                except Exception as e:
                    logger.warning(
                        "Provider parser %s failed: %s; falling back to regex",
                        provider, e,
                    )
                break

    if not parser_succeeded:
        candidates = fallback.parse(msg)
        if provider:
            # Tag the fallback output with the detected provider for traceability
            for c in candidates:
                c["provider"] = provider
                c["parser_fallback"] = True

    return candidates
