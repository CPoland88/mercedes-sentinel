"""Fallback parser: regex-extract VINs and listing URLs from any email.

Used when provider detection fails or a per-provider parser raises.
Provides resilience against email-template redesigns: even when a richer
parser breaks, we still surface VINs and URLs so the alert lands in the
queue rather than getting dropped.
"""
from __future__ import annotations

from email.message import Message
from typing import List

import re

# FMVSS 565 VIN: 17 chars from A-Z minus {I, O, Q} and 0-9.
VIN_PATTERN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")

# HTTP(S) URL — terminate on whitespace and common HTML/email punctuation.
URL_PATTERN = re.compile(r"https?://[^\s<>\"')\]]+")


def _decode_part(part) -> str:
    """Decode an email part to a string. Returns '' on failure."""
    try:
        payload = part.get_payload(decode=True)
        if payload:
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    except Exception:
        pass
    return ""


def get_email_body(msg: Message) -> str:
    """Extract a single text representation of the email body.

    Prefers `text/plain` when present. Falls back to stripping HTML from
    `text/html` parts (uses BeautifulSoup if installed, else returns raw
    HTML — the regexes are tag-tolerant enough to still find VINs/URLs).
    """
    plain_parts: List[str] = []
    html_parts: List[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                text = _decode_part(part)
                if text:
                    plain_parts.append(text)
            elif ctype == "text/html":
                text = _decode_part(part)
                if text:
                    html_parts.append(text)
    else:
        ctype = msg.get_content_type()
        text = _decode_part(msg)
        if text:
            if ctype == "text/html":
                html_parts.append(text)
            else:
                plain_parts.append(text)

    chunks: List[str] = []
    if plain_parts:
        chunks.append("\n".join(plain_parts))

    if html_parts:
        try:
            from bs4 import BeautifulSoup

            for h in html_parts:
                soup = BeautifulSoup(h, "html.parser")
                # Pull href URLs out explicitly — get_text() drops attributes,
                # which would lose listing URLs that only appear in <a href>.
                hrefs = [a.get("href", "") for a in soup.find_all("a")]
                text = soup.get_text(separator=" ", strip=True)
                href_blob = " ".join(h for h in hrefs if h)
                chunks.append(f"{text} {href_blob}".strip())
        except ImportError:
            # BS4 missing — feed raw HTML through; VIN/URL regexes are
            # tag-tolerant and will still find matches in attribute values.
            chunks.extend(html_parts)

    return "\n".join(chunks)


def parse(msg: Message) -> List[dict]:
    """Extract candidates by regex.

    Heuristic: emit one candidate per unique VIN in the body. Listing URL
    paired with VIN by:
      1. Strongest — URL string that contains the VIN substring.
      2. Otherwise — nearest URL by character position within ~2K chars.
      3. Otherwise — the first URL in the body.
    """
    body = get_email_body(msg)
    if not body:
        return []

    # Preserve insertion order; dedup.
    vins = list(dict.fromkeys(VIN_PATTERN.findall(body)))
    urls = URL_PATTERN.findall(body)

    candidates: List[dict] = []
    for vin in vins:
        listing_url = _pair_url_with_vin(body, vin, urls)
        candidates.append({
            "vin": vin,
            "listing_url": listing_url,
            "provider": "unknown",
            "raw_metadata": {},
            "parser": "fallback",
        })

    return candidates


def _pair_url_with_vin(body: str, vin: str, urls: List[str]) -> str | None:
    """Pick the best URL for a given VIN. Prefers VIN-in-URL match."""
    # 1. URL containing the VIN (case-insensitive)
    vin_lower = vin.lower()
    vin_urls = [u for u in urls if vin_lower in u.lower()]
    if vin_urls:
        return vin_urls[0]

    # 2. Nearest URL by character position
    vin_pos = body.find(vin)
    if vin_pos < 0 or not urls:
        return urls[0] if urls else None
    nearest_url = None
    nearest_dist = float("inf")
    for url in urls:
        url_pos = body.find(url)
        if url_pos < 0:
            continue
        dist = abs(url_pos - vin_pos)
        if dist < nearest_dist and dist < 2000:
            nearest_dist = dist
            nearest_url = url

    return nearest_url or (urls[0] if urls else None)
