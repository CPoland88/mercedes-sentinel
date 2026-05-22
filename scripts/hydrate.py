"""HTTP hydration for cars.com listing URLs.

When a cars.com saved-search alert lands in the MB-Sentinel mailbox, the
email body provides title, mileage, price, and a per-vehicle URL — but
NOT the VIN, dealer, color, packages, or CPO status. Those fields are
required by the triage rubric and by the dedup gate's per-provider
metadata snapshot, so we follow the link the user already received to
fetch them.

This is the only network operation in the ingest pipeline beyond IMAP
polling. Posture is explicitly scoped by WORKSPACE.md "Carve-out for
hydration":

  - Realistic User-Agent (current stable Chrome on macOS).
  - 1.5-3s jitter between requests (no rate-limited fan-out).
  - One request per email-referenced URL, never enumerate, never crawl,
    never parallelize.
  - Retry-once on 5xx, fail-hard on 4xx.
  - No headless browser, no JS rendering, no auth bypass.

Three parse strategies, layered most-stable-first:

  1. Schema.org `Vehicle` JSON-LD. Cars.com emits this for SEO; it's
     the cleanest source for VIN, color, dealer, and trim.
  2. Named CSS selectors against common cars.com markup. Expected to
     drift as the site redesigns; treat each selector as best-effort.
  3. Regex over raw HTML as last resort. Catches a VIN even when both
     upper layers miss.

When all three strategies miss a field, the field stays None. The
caller decides whether a missing VIN warrants dropping the candidate
or falling back to email-only metadata.
"""
from __future__ import annotations

import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Protocol

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ---------- Constants ----------

# Realistic UA pinned to a specific version so the request signature
# stays stable across runs. Bump when cars.com starts gating on old UAs
# (rare, but it does happen).
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = httpx.Timeout(connect=15.0, read=30.0, write=15.0, pool=15.0)

# Jitter range per WORKSPACE.md carve-out.
JITTER_MIN_S = 1.5
JITTER_MAX_S = 3.0


# ---------- Exceptions ----------

class HydrationError(Exception):
    """Raised on hard fetch failures: 4xx responses, network errors, or
    5xx that survived the single retry. Partial parse failures (page
    fetched but a selector missed a field) do NOT raise — the missed
    field stays None on the returned HydratedListing."""


# ---------- Data ----------

@dataclass
class HydratedListing:
    """Subset of cars.com vehicledetail page data that the triage rubric
    and the dedup gate care about. Fields are Optional because selectors
    drift; the caller decides what counts as "enough" to keep the
    candidate."""

    vin: Optional[str] = None
    dealer_name: Optional[str] = None
    dealer_city: Optional[str] = None
    dealer_state: Optional[str] = None
    dealer_zip: Optional[str] = None
    exterior_color: Optional[str] = None
    interior_color: Optional[str] = None
    packages: List[str] = field(default_factory=list)
    cpo_badge: Optional[str] = None
    model_year: Optional[int] = None
    trim: Optional[str] = None
    body_style: Optional[str] = None

    def to_dict(self) -> dict:
        """Project to a dict for merging into the candidate's
        raw_metadata. Drops empty/None values so dedup-gate comparisons
        aren't perturbed by absent fields."""
        out = {}
        for k, v in self.__dict__.items():
            if v is None or v == "" or v == []:
                continue
            out[k] = v
        return out


# ---------- Fetcher seam (production HTTP vs test files) ----------

class Fetcher(Protocol):
    """Injection seam. Production uses HttpxFetcher; tests use
    FileFetcher to read saved HTML snapshots without touching network."""

    def get(self, url: str) -> str: ...


class HttpxFetcher:
    """Production Fetcher. Applies jitter, retry-once-on-5xx,
    fail-hard-on-4xx. Reuses a single httpx.Client across calls so
    keep-alive works for back-to-back URLs in the same batch."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        jitter_min: float = JITTER_MIN_S,
        jitter_max: float = JITTER_MAX_S,
        client: Optional[httpx.Client] = None,
    ):
        self._client = client or httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout,
            follow_redirects=True,
        )
        self._jitter_min = jitter_min
        self._jitter_max = jitter_max
        self._first_request = True

    def get(self, url: str) -> str:
        # Jitter before every request EXCEPT the first one in this
        # fetcher's lifetime. A one-listing batch should not sleep.
        if not self._first_request:
            sleep_s = random.uniform(self._jitter_min, self._jitter_max)
            logger.debug("Jitter sleep %.2fs before %s", sleep_s, url)
            time.sleep(sleep_s)
        self._first_request = False

        for attempt in (1, 2):
            try:
                resp = self._client.get(url)
            except httpx.RequestError as e:
                if attempt == 2:
                    raise HydrationError(f"Network error fetching {url}: {e}") from e
                logger.warning("Network error attempt %d for %s: %s", attempt, url, e)
                time.sleep(1.0)
                continue
            if 400 <= resp.status_code < 500:
                raise HydrationError(
                    f"4xx fetching {url}: {resp.status_code} {resp.reason_phrase}"
                )
            if 500 <= resp.status_code < 600:
                if attempt == 2:
                    raise HydrationError(
                        f"5xx fetching {url} after retry: {resp.status_code}"
                    )
                logger.warning(
                    "5xx attempt %d for %s: %s; retrying",
                    attempt, url, resp.status_code,
                )
                time.sleep(1.0)
                continue
            return resp.text
        # Unreachable: the loop above always returns or raises.
        raise HydrationError(f"Exhausted retries fetching {url}")

    def close(self) -> None:
        self._client.close()


class FileFetcher:
    """Test Fetcher. Maps URL -> file path (or URL -> raw HTML string).
    No network, no jitter, no sleeps."""

    def __init__(self, url_to_source: dict):
        """`url_to_source` accepts either filesystem paths (strings/Paths
        that exist on disk and will be read) or raw HTML strings. The
        constructor doesn't validate — `get` raises HydrationError on
        miss so tests get a clear failure if a URL isn't wired up."""
        self._map = url_to_source

    def get(self, url: str) -> str:
        if url not in self._map:
            raise HydrationError(f"FileFetcher has no mapping for {url}")
        source = self._map[url]
        # Heuristic: if it looks like a path that exists, read it;
        # otherwise treat as raw HTML.
        try:
            from pathlib import Path
            p = Path(source)
            if p.exists():
                return p.read_text(encoding="utf-8")
        except (OSError, TypeError):
            pass
        return str(source)


# ---------- Public API ----------

_default_fetcher: Optional[Fetcher] = None


def _get_default_fetcher() -> Fetcher:
    """Lazy-init the prod fetcher so tests that never call live hydration
    don't pay for an httpx.Client they won't use."""
    global _default_fetcher
    if _default_fetcher is None:
        _default_fetcher = HttpxFetcher()
    return _default_fetcher


def hydrate_cars_com(url: str, fetcher: Optional[Fetcher] = None) -> HydratedListing:
    """Fetch a cars.com vehicledetail URL and extract triage-relevant
    fields. See module docstring for posture and strategy layering.

    Raises HydrationError on hard fetch failures (4xx, network down,
    retried 5xx). Partial parse failures return a HydratedListing with
    the missed field set to None — the caller decides what counts as
    "enough" to keep the candidate.
    """
    f = fetcher or _get_default_fetcher()
    html = f.get(url)
    return _parse_vehicledetail_html(html)


# ---------- HTML parsing ----------

# FMVSS 565 VIN pattern, same as parsers/fallback.py.
VIN_PATTERN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")

CPO_BADGE_PATTERN = re.compile(
    r"\b(Mercedes-Benz Certified Pre-Owned|Certified Pre-Owned|CPO)\b",
    re.IGNORECASE,
)


def _parse_vehicledetail_html(html: str) -> HydratedListing:
    """Try JSON-LD, then CSS selectors, then regex. Each strategy only
    fills fields the prior layer left empty — strategy order encodes
    confidence in stability."""
    listing = HydratedListing()
    soup = BeautifulSoup(html, "html.parser")

    _apply_jsonld(soup, listing)
    _apply_css_selectors(soup, listing)
    _apply_regex_fallbacks(html, listing)

    return listing


def _apply_jsonld(soup: BeautifulSoup, listing: HydratedListing) -> None:
    """Schema.org JSON-LD pass. Cars.com emits Vehicle objects for SEO;
    the spec at schema.org/Vehicle defines vehicleIdentificationNumber,
    color, vehicleInteriorColor, vehicleConfiguration, bodyType."""
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.debug("JSON-LD parse failed; skipping block")
            continue

        for obj in _iter_jsonld_objects(data):
            t = obj.get("@type")
            if t in ("Vehicle", "Car"):
                _merge_vehicle(obj, listing)
            elif t in ("AutoDealer", "AutomotiveBusiness", "Organization"):
                _merge_dealer(obj, listing)


def _iter_jsonld_objects(data):
    """Flatten a JSON-LD payload to an iterable of dicts. JSON-LD can be
    a single object, a list, or a @graph wrapper."""
    if isinstance(data, dict):
        yield data
        for obj in data.get("@graph", []) or []:
            if isinstance(obj, dict):
                yield obj
    elif isinstance(data, list):
        for obj in data:
            if isinstance(obj, dict):
                yield obj


def _merge_vehicle(obj: dict, listing: HydratedListing) -> None:
    if listing.vin is None:
        listing.vin = obj.get("vehicleIdentificationNumber")
    if listing.exterior_color is None:
        listing.exterior_color = obj.get("color")
    if listing.interior_color is None:
        listing.interior_color = obj.get("vehicleInteriorColor")
    if listing.model_year is None:
        my = obj.get("modelDate") or obj.get("vehicleModelDate") or obj.get("productionDate")
        if my:
            try:
                listing.model_year = int(str(my)[:4])
            except (TypeError, ValueError):
                pass
    if listing.body_style is None:
        listing.body_style = obj.get("bodyType")
    if listing.trim is None:
        listing.trim = obj.get("vehicleConfiguration") or obj.get("trim")
    # Seller may live directly on the Vehicle, or nested under offers.
    seller = obj.get("seller")
    if not isinstance(seller, dict):
        offers = obj.get("offers")
        if isinstance(offers, dict):
            seller = offers.get("seller")
    if isinstance(seller, dict):
        _merge_dealer(seller, listing)


def _merge_dealer(obj: dict, listing: HydratedListing) -> None:
    if listing.dealer_name is None:
        listing.dealer_name = obj.get("name")
    addr = obj.get("address")
    if isinstance(addr, dict):
        if listing.dealer_city is None:
            listing.dealer_city = addr.get("addressLocality")
        if listing.dealer_state is None:
            listing.dealer_state = addr.get("addressRegion")
        if listing.dealer_zip is None:
            listing.dealer_zip = addr.get("postalCode")


def _apply_css_selectors(soup: BeautifulSoup, listing: HydratedListing) -> None:
    """Named-selector pass. Selectors are speculative against current
    cars.com markup and EXPECTED to drift. When a selector stops
    matching, regex fallback still surfaces a VIN, and the caller can
    iterate."""

    # VIN — cars.com tends to label explicitly via data-testid or class
    if listing.vin is None:
        for selector in ("[data-testid='vin-value']", ".vin", ".vehicle-vin", "[data-vin]"):
            el = soup.select_one(selector)
            if el is None:
                continue
            # Prefer data-vin attribute when present, else text
            attr_vin = el.get("data-vin") if el.has_attr("data-vin") else None
            text = (attr_vin or el.get_text(strip=True) or "").upper()
            m = VIN_PATTERN.search(text)
            if m:
                listing.vin = m.group(0)
                break

    # CPO badge — text search over the visible page is more durable
    # than CSS selectors, which change every redesign.
    if listing.cpo_badge is None:
        page_text = soup.get_text(" ", strip=True)
        m = CPO_BADGE_PATTERN.search(page_text)
        if m:
            # Normalize "CPO" to the canonical label for downstream consistency.
            badge = m.group(1)
            if badge.upper() == "CPO":
                badge = "Certified Pre-Owned"
            listing.cpo_badge = badge

    # Packages — cars.com lists these under a "Packages" or "Features"
    # heading; speculative selector.
    if not listing.packages:
        for header in soup.find_all(["h2", "h3", "h4"]):
            if "package" in header.get_text(strip=True).lower():
                ul = header.find_next("ul")
                if ul:
                    items = [li.get_text(strip=True) for li in ul.find_all("li")]
                    listing.packages = [i for i in items if i]
                    break


def _apply_regex_fallbacks(html: str, listing: HydratedListing) -> None:
    """Last-resort raw-HTML regex. Catches a VIN that slipped past
    JSON-LD and CSS selectors. Intentionally minimal — anything more
    structured belongs in the upper layers."""
    if listing.vin is None:
        m = VIN_PATTERN.search(html)
        if m:
            listing.vin = m.group(0)
