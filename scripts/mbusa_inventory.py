"""MBUSA inventory API client.

Primary candidate stream for Architecture B (see MBUSA_PIVOT.md). The
forked skill originally hydrated cars.com listing pages for VIN/dealer/
color/packages; Cloudflare's escalation ladder made that path
unsustainable for daily automation. We pivoted to the consumer-facing
inventory search endpoint that MBUSA's own SPA hits at
https://www.mbusa.com/en/cpo/inventory/search — same JSON, no auth, no
CSRF, no bot-detection beyond standard header expectations. The endpoint
is Akamai-cached and designed for high-volume consumer traffic.

This module is the production client for that endpoint. It paginates
the search response, parses each vehicle record into an MbusaCandidate
dataclass with fields shaped by CONTEXT.md needs (Tier A/B/C geography,
580-preferred posture, must-have packages, CPO-window verification),
and exposes a single `fetch_matching_inventory` entry point for the
ingest pipeline.

Posture (WORKSPACE.md):

  - MBUSA is a sanctioned consumer-facing API. The hydration carve-out
    posture (polite UA, jitter, no parallel fan-out, no headless browser)
    still applies and is straightforwardly OK here.
  - Headers match the SPA's own XHR signature (Sec-Fetch-Mode: cors,
    Origin/Referer set to https://www.mbusa.com). Validated working in
    scripts/dev_capture_api.py.
  - 1.5-3s jitter between page requests. One retry on 5xx with
    exponential backoff. Fail fast on 4xx — no point retrying a
    malformed query.
  - HTTP/2 via ALPN. httpx falls back to HTTP/1.1 if the server
    doesn't negotiate.

Open questions deferred from MBUSA_PIVOT.md, with current defaults:

  - Color codes: ship with broad two-letter codes (BLU,GRN). Marketing-
    name matching ("Emerald Green Metallic" vs "Twilight Blue Metallic")
    happens downstream in triage against the `paint_marketing` field.
  - Distance enforcement: ship with `distance=ANY` and the caller's
    post-filter on `dealer_distance_mi`. MBUSA's distance is straight-
    line, not drive-miles; CONTEXT.md uses drive-miles for the Tier
    A/B/C boundaries.
  - CPO posture: ship with `invType=cpo` only. CONTEXT.md prefers CPO;
    adding pre-owned (`cpo,pre`) roughly doubles the volume and depends
    on a foregone-warranty discount mechanic that doesn't exist in
    triage yet. Flip to `cpo,pre` once that logic lands.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Protocol
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)


# ---------- Constants ----------

BASE_URL = "https://nafta-service.mbusa.com/api/inv/v1/en_us/used/vehicles/search"

# Request-header signature for Chrome 126 on macOS performing an XHR
# call against the inventory endpoint. Lifted from
# scripts/dev_capture_api.py (which mirrors what MBUSA's SPA sends on
# the same call, validated via DevTools network capture). Origin and
# Referer are required — without them the endpoint serves 400. The
# Sec-Fetch-* triple identifies the request as a cors XHR (vs a
# top-level navigation), which is what the endpoint expects.
API_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://www.mbusa.com",
    "Referer": (
        "https://www.mbusa.com/en/cpo/inventory/search?zip=22180&inventory=cpo"
    ),
    "Sec-Ch-Ua": (
        '"Google Chrome";v="126", "Not-A.Brand";v="8", "Chromium";v="126"'
    ),
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Priority": "u=3, i",
}

# Page size that MBUSA tolerates reliably. 12 is the SPA's own value;
# values >= 50 sometimes 500 out per recon. Smaller is also fine but
# costs more requests.
DEFAULT_PAGE_SIZE = 12

# Per-page jitter band, seconds. Matches the WORKSPACE.md hydration
# carve-out. Pause is sampled uniformly between these on every page
# request after the first.
JITTER_MIN_SEC = 1.5
JITTER_MAX_SEC = 3.0

# Retry policy for 5xx. We retry once after a short backoff; further
# 5xx are treated as MBUSA having a bad minute, not our problem to
# work around at this layer.
RETRY_5XX_BACKOFF_SEC = 2.0

# Hard guard against pathological pagination loops (e.g., a server
# response that never advances). Architecture B is built around
# US-wide GLS inventory in the hundreds, so this is far above any
# legitimate ceiling.
MAX_PAGES = 200


# ---------- Data shapes ----------


@dataclass(frozen=True)
class MbusaCandidate:
    """Normalized representation of one MBUSA inventory record.

    Maps the documented MBUSA response schema (see MBUSA_PIVOT.md) to
    field names that match CONTEXT.md vocabulary. Tolerates missing
    fields gracefully — real MBUSA records vary, especially for
    dealer.address[] (occasionally empty) and ``msrp`` (occasionally
    zero for "contact dealer for price" listings).

    ``raw_record`` retains the original dict so downstream code can
    inspect anything not surfaced here without re-fetching.
    """

    vin: str
    year: Optional[int] = None
    model_id: Optional[str] = None
    model_name: Optional[str] = None
    class_id: Optional[str] = None

    # Dealer geography. ``dealer_distance_mi`` is the straight-line
    # distance MBUSA computes from the requested zip; CONTEXT.md uses
    # drive-miles so the caller applies its own Tier A/B/C gate on
    # this value (or recomputes against a routing service).
    dealer_name: Optional[str] = None
    dealer_city: Optional[str] = None
    dealer_state: Optional[str] = None
    dealer_zip: Optional[str] = None
    dealer_distance_mi: Optional[float] = None

    # Color. ``exterior_meta_color`` is the short code (BLU, GRN) the
    # API filter accepts. ``paint_marketing`` is the marketing name
    # ("Emerald Green metallic", "Twilight Blue metallic") that
    # CONTEXT.md gates on.
    exterior_meta_color: Optional[str] = None
    paint_marketing: Optional[str] = None

    # Pricing. ``ask_price`` is the value triage should treat as the
    # asking price — sourced from ``msrp`` in the MBUSA payload, which
    # for CPO records is the current dealer ask, not the original
    # MSRP (MBUSA reuses the field name). ``inventory_price_raw`` is
    # MBUSA's ``inventoryPrice`` field, which is reliably 0.0 for CPO
    # records — retained only for debugging/audit.
    ask_price: Optional[float] = None
    inventory_price_raw: Optional[float] = None

    mileage: Optional[float] = None

    # CPO signals. ``is_cpo`` is the conjunction of ``type == "PRE"``
    # and ``usedVehicleAttributes.certified == True`` so we don't flag
    # a non-CPO pre-owned car (possible when invType=cpo,pre) as CPO.
    is_cpo: bool = False

    # Build/options. Three lists with overlapping semantics in the
    # MBUSA response; we keep them separate because each is the most
    # reliable source for a different question:
    #   - option_list: factory option codes (e.g. "0:226 7-seat
    #     cabin configuration"). The build-sheet truth CONTEXT.md
    #     trusts for seating-config verification.
    #   - features: flat list of marketing-named features ("Wireless
    #     Apple CarPlay"). Easier for prompt context.
    #   - included_features: parallel to features but appears in
    #     a slightly different schema slot; retained for completeness.
    option_list: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    included_features: List[str] = field(default_factory=list)

    stock_id: Optional[str] = None

    raw_record: dict = field(default_factory=dict, repr=False, compare=False)


# ---------- Public API ----------


def parse_vehicle_record(record: dict) -> MbusaCandidate:
    """Map one MBUSA response record to an MbusaCandidate.

    Pure function. Tolerates missing/null fields by leaving the
    corresponding MbusaCandidate field at its default. The only
    required field is ``vin`` — a record without a VIN is upstream
    nonsense and the caller should drop it before calling here, but
    we raise ``ValueError`` to surface it clearly if it slips through.
    """
    vin = record.get("vin")
    if not vin:
        raise ValueError("MBUSA record missing vin")

    used_attrs = record.get("usedVehicleAttributes") or {}
    paint = record.get("paint") or {}
    dealer = record.get("dealer") or {}
    addresses = dealer.get("address") or []
    primary_addr = addresses[0] if addresses else {}
    location = primary_addr.get("location") or {}

    # Year comes through as a string in the MBUSA payload. Coerce
    # to int but tolerate a non-numeric value just in case.
    year: Optional[int] = None
    raw_year = record.get("year")
    if raw_year is not None:
        try:
            year = int(raw_year)
        except (TypeError, ValueError):
            logger.debug("Non-numeric year %r for VIN %s", raw_year, vin)

    # MBUSA's ``msrp`` for a used record is the current ask, not the
    # original MSRP. ``dsrp`` and ``reservePrice`` on usedVehicleAttributes
    # carry the same value. Fall back through them in order in case any
    # is zero/missing on a given record.
    ask_price = _first_positive(
        record.get("msrp"),
        used_attrs.get("dsrp"),
        used_attrs.get("reservePrice"),
    )
    inventory_price_raw = _to_float(record.get("inventoryPrice"))

    dealer_distance_mi = _to_float(location.get("dist"))

    # CPO conjunction. ``type == "PRE"`` is MBUSA's used-vehicle marker
    # (all pre-owned, certified or not). ``certified`` is the actual
    # CPO flag on usedVehicleAttributes. Both must be true.
    is_cpo = (
        record.get("type") == "PRE" and bool(used_attrs.get("certified"))
    )

    option_list = [
        opt.get("text", "")
        for opt in (used_attrs.get("optionList") or [])
        if opt.get("text")
    ]

    # ``features`` is a flat list of strings on the record root.
    features = [
        f for f in (record.get("features") or []) if isinstance(f, str) and f
    ]

    # ``includedFeatures`` is a list of {"name": ...} objects.
    included_features = [
        item.get("name", "")
        for item in (record.get("includedFeatures") or [])
        if isinstance(item, dict) and item.get("name")
    ]

    # Dedup the three lists' overlap-aware union isn't useful for the
    # downstream caller (each list has different reliability and
    # provenance); we keep them separate.

    return MbusaCandidate(
        vin=vin,
        year=year,
        model_id=record.get("modelId"),
        model_name=record.get("modelName"),
        class_id=record.get("classId"),
        dealer_name=dealer.get("name"),
        dealer_city=primary_addr.get("city"),
        dealer_state=primary_addr.get("state"),
        dealer_zip=primary_addr.get("zip"),
        dealer_distance_mi=dealer_distance_mi,
        exterior_meta_color=record.get("exteriorMetaColor"),
        paint_marketing=paint.get("name") or paint.get("id"),
        ask_price=ask_price,
        inventory_price_raw=inventory_price_raw,
        mileage=_to_float(used_attrs.get("mileage")),
        is_cpo=is_cpo,
        option_list=option_list,
        features=features,
        included_features=included_features,
        stock_id=record.get("stockId"),
        raw_record=record,
    )


def fetch_matching_inventory(
    zip_code: str,
    model_codes: Iterable[str],
    year_range: tuple[int, int],
    color_codes: Iterable[str],
    class_id: Optional[str] = None,
    inv_type: str = "cpo",
    distance: str = "ANY",
    page_size: int = DEFAULT_PAGE_SIZE,
    client: Optional[httpx.Client] = None,
) -> List[MbusaCandidate]:
    """Walk the MBUSA inventory search endpoint, return all matches.

    Args:
        zip_code: ZIP for geo-sort + distance reference. CONTEXT.md uses
            22180 (Vienna, VA).
        model_codes: Iterable of MBUSA model designation codes
            (e.g. ``["GLS450W4", "GLS580W4"]``). Joined comma-separated
            for the ``model`` query param.
        year_range: ``(min_year, max_year)``. CONTEXT.md gates on
            MY2024+, so caller typically passes ``(2024, current_year+1)``.
        color_codes: Iterable of two-letter MBUSA color codes
            (``["BLU", "GRN"]``). Joined comma-separated for the
            ``exterior`` query param.
        class_id: Optional vehicle-class filter (e.g. ``"GLS"``).
            Narrows MBUSA's response without affecting per-model selection.
        inv_type: ``"cpo"`` (default) for certified-only, ``"cpo,pre"``
            to include uncertified pre-owned.
        distance: ``"ANY"`` (default) for nationwide. Pass an integer
            string (e.g. ``"250"``) to apply MBUSA's straight-line
            distance cap, but caller should generally post-filter on
            ``dealer_distance_mi`` against drive-miles.
        page_size: Per-page record count. MBUSA tolerates 12 reliably;
            see DEFAULT_PAGE_SIZE.
        client: Optional httpx.Client. If None, a session-scoped client
            with API_HEADERS + HTTP/2 is constructed and closed before
            return. Inject for tests.

    Returns:
        Flat list of MbusaCandidate, one per record across all pages.
        Empty list if the query matches nothing. Raises ``httpx.HTTPError``
        on 4xx (malformed query, bad headers) or repeated 5xx.
    """
    owned_client = client is None
    if owned_client:
        client = httpx.Client(
            headers=API_HEADERS,
            http2=True,
            follow_redirects=True,
            timeout=httpx.Timeout(
                connect=15.0, read=30.0, write=15.0, pool=15.0
            ),
        )

    try:
        candidates: List[MbusaCandidate] = []
        min_year, max_year = year_range
        base_params = {
            "count": page_size,
            "distance": distance,
            "exterior": ",".join(color_codes),
            "invType": inv_type,
            "maxYear": max_year,
            "minYear": min_year,
            "model": ",".join(model_codes),
            "resvOnly": "false",
            "sortBy": "distance-asc",
            "withFilters": "true",
            "zip": zip_code,
        }
        if class_id:
            base_params["class"] = class_id

        start = 0
        for page_index in range(MAX_PAGES):
            if page_index > 0:
                _jittered_sleep()

            params = dict(base_params, start=start)
            url = f"{BASE_URL}?{urlencode(params)}"
            payload = _get_with_retry(client, url)

            paged = (payload.get("result") or {}).get("pagedVehicles") or {}
            records = paged.get("records") or []
            paging = paged.get("paging") or {}
            total_count = paging.get("totalCount", 0)
            current_count = paging.get("currentCount", len(records))

            for record in records:
                try:
                    candidates.append(parse_vehicle_record(record))
                except ValueError as exc:
                    logger.warning(
                        "Skipping malformed MBUSA record on page %d: %s",
                        page_index,
                        exc,
                    )

            # Termination: server returned no records, OR we've consumed
            # everything totalCount said exists.
            if not records:
                break
            start += current_count
            if start >= total_count:
                break
        else:
            logger.warning(
                "MBUSA pagination hit MAX_PAGES=%d guard; truncating",
                MAX_PAGES,
            )

        return candidates
    finally:
        if owned_client:
            client.close()


# ---------- Internal helpers ----------


def _get_with_retry(client: httpx.Client, url: str) -> dict:
    """GET with one retry on 5xx, fail-fast on 4xx.

    Raises ``httpx.HTTPStatusError`` after the retry budget is exhausted
    or on any 4xx. Returns the decoded JSON body on success.
    """
    for attempt in (1, 2):
        response = client.get(url)
        status = response.status_code
        if 200 <= status < 300:
            return response.json()
        if 400 <= status < 500:
            logger.error(
                "MBUSA %d on %s; first 300 chars of body: %s",
                status,
                url,
                response.text[:300],
            )
            response.raise_for_status()
        # 5xx: retry once.
        if attempt == 1:
            logger.warning(
                "MBUSA %d on %s; retrying after %.1fs",
                status,
                url,
                RETRY_5XX_BACKOFF_SEC,
            )
            time.sleep(RETRY_5XX_BACKOFF_SEC)
            continue
        logger.error("MBUSA %d on %s after retry; failing", status, url)
        response.raise_for_status()

    # Unreachable: the loop either returns or raises. Present so static
    # analysis sees a guaranteed exit.
    raise RuntimeError("unreachable")


def _jittered_sleep() -> None:
    """Sleep a uniform-random duration in the WORKSPACE.md jitter band."""
    time.sleep(random.uniform(JITTER_MIN_SEC, JITTER_MAX_SEC))


def _to_float(value) -> Optional[float]:
    """Best-effort float coercion. Returns None for None, "", or junk."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_positive(*values) -> Optional[float]:
    """Return the first value that coerces to a positive float, else None.

    Used to walk MBUSA's price-bearing fields (msrp, dsrp, reservePrice)
    and pick the first non-zero one. CPO records reliably have
    inventoryPrice=0.0 but valid prices in the others.
    """
    for value in values:
        coerced = _to_float(value)
        if coerced is not None and coerced > 0:
            return coerced
    return None
