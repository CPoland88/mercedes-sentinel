"""State management for the ingest + triage pipeline.

Three JSON files in `data/`:

- `seen-vins.json` — dedup memory. Maps VIN to first/last seen timestamps
  AND per-provider snapshots of the listing metadata. The per-provider
  snapshots are what let us detect "this VIN reappeared on CarGurus but
  the price dropped $5K" and trigger re-triage on a known VIN that
  would otherwise have been deduped out.
- `queue.json` — untriaged candidates. FIFO. Drained by triage in C2.
- `triaged.json` — append-only verdict log. Each entry self-contained
  (VIN + provider + metadata snapshot + verdict + reasoning), so a VIN
  that's been re-triaged after a price change accumulates a history.

All three live under `data/` and are gitignored.

Schema change in C2: the C1 schema stored `providers` (list of strings)
and `listing_urls` (flat list) on each VIN. The C2 schema replaces both
with a `per_provider` dict keyed by provider name, with each provider's
`last_metadata`, `last_seen`, and `listing_urls`. This was a breaking
change but no live data existed yet (the C1 live run was dry-run-only,
which doesn't persist state), so no migration was needed.

Schema change in MBUSA pivot (v2): adds an `email_signals` list to
each VIN record. An EmailSignal is one observation of a VIN in an
authorized email alert (cars.com / autotrader / cargurus): the alert's
provider, the time we observed it, the ask price at that observation,
and the price-drop delta the alert reported. The list accumulates so
triage can see the trajectory of a candidate's ask over time even when
no MBUSA candidate matches on a given day.

The v2 migration runs on first `load_seen_vins` against a pre-v2 file:
adds `email_signals: []` to every existing VIN record and stamps a
top-level `_schema_version: 2` marker. The migrated state is persisted
on the next `save_seen_vins` call (i.e., the next `mark_seen` after
ingestion resumes). The migration is idempotent — a v2 file loads
unchanged.

The `source` field on candidate dicts (queue, triaged) is a sibling
concern handled by ingest.py, not by this module — state.py passes
candidates through opaquely.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Resolve `data/` relative to this file's parent's parent (= repo root).
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEEN_VINS_PATH = DATA_DIR / "seen-vins.json"
QUEUE_PATH = DATA_DIR / "queue.json"
TRIAGED_PATH = DATA_DIR / "triaged.json"

# Current schema version for seen-vins.json. Bumped by the MBUSA pivot
# to add per-VIN email_signals. See module docstring for the v1→v2
# migration story.
SCHEMA_VERSION = 2

# Top-level sentinel key carrying the schema version. Prefixed with
# `_` so it sorts above VIN entries (which are 17-char uppercase
# alphanumeric and never start with underscore) and is trivially
# distinguishable from a VIN by any iterator that needs to skip it.
_SCHEMA_VERSION_KEY = "_schema_version"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


# ---------- seen-vins ----------

def _migrate_if_needed(state: dict) -> dict:
    """Upgrade a seen-vins state dict to the current schema in place.

    Idempotent: a v2 dict (or empty dict) loads unchanged. A v1 dict
    (no `_schema_version`, no `email_signals` on VIN records) is
    upgraded by adding `email_signals: []` to every VIN record and
    stamping the version marker.

    Mutates and returns ``state`` so callers can chain.
    """
    current_version = state.get(_SCHEMA_VERSION_KEY)
    if current_version == SCHEMA_VERSION:
        return state

    # v1 → v2: add email_signals to every VIN record. We iterate by
    # key list (not items()) so it's safe to mutate the dict, and skip
    # any underscore-prefixed metadata keys defensively even though
    # only _schema_version is defined today.
    for key in list(state.keys()):
        if key.startswith("_"):
            continue
        record = state[key]
        if isinstance(record, dict) and "email_signals" not in record:
            record["email_signals"] = []

    state[_SCHEMA_VERSION_KEY] = SCHEMA_VERSION
    return state


def load_seen_vins() -> dict:
    _ensure_data_dir()
    if not SEEN_VINS_PATH.exists():
        return {_SCHEMA_VERSION_KEY: SCHEMA_VERSION}
    state = json.loads(SEEN_VINS_PATH.read_text())
    return _migrate_if_needed(state)


def save_seen_vins(state: dict) -> None:
    _ensure_data_dir()
    SEEN_VINS_PATH.write_text(json.dumps(state, indent=2, sort_keys=True))


def is_seen(vin: str) -> bool:
    """True if we've ever seen this VIN, regardless of which provider or
    whether the metadata has changed. Used for raw existence checks; the
    smarter re-triage gate is `should_enqueue`."""
    return vin in load_seen_vins()


def get_last_metadata(vin: str, provider: str) -> Optional[dict]:
    """Return the most recent metadata snapshot we have for this
    (vin, provider) pair, or None if we've never seen the pair."""
    state = load_seen_vins()
    return (
        state.get(vin, {})
        .get("per_provider", {})
        .get(provider, {})
        .get("last_metadata")
    )


def should_enqueue(vin: str, provider: str, raw_metadata: Optional[dict]) -> bool:
    """The dedup gate. Returns True (enqueue this candidate for triage) when:

      1. We've never seen this VIN at all, OR
      2. We've seen the VIN but never from this provider, OR
      3. We've seen the (vin, provider) pair but the metadata changed.

    Returns False (skip) when this exact (vin, provider, metadata) combo
    has already been ingested — that's the common case for daily polling
    against a label that keeps the same alerts around.

    The metadata comparison is a structural equality check on dicts.
    Providers that include timestamps in their metadata would defeat this
    (every alert would look "new"), so v1 parsers should keep metadata
    limited to listing facts (price, mileage, badge, days_on_lot).
    """
    state = load_seen_vins()
    if vin not in state:
        return True
    prov_record = state[vin].get("per_provider", {}).get(provider)
    if prov_record is None:
        return True
    return prov_record.get("last_metadata") != (raw_metadata or {})


def mark_seen(
    vin: str,
    provider: str,
    listing_url: Optional[str],
    raw_metadata: Optional[dict] = None,
) -> None:
    """Record that a VIN has been observed. Idempotent — repeat calls with
    the same provider update the last_seen timestamp and replace the
    last_metadata snapshot. URLs accumulate (deduped) on the provider's
    record."""
    state = load_seen_vins()
    now = _now_iso()

    if vin not in state:
        state[vin] = {
            "first_seen": now,
            "last_seen": now,
            "per_provider": {},
            "email_signals": [],
        }
    else:
        state[vin]["last_seen"] = now
        # Belt-and-suspenders: a record created before the v2 migration
        # ran (shouldn't happen in practice — load_seen_vins migrates
        # everything on read — but cheap insurance against an external
        # writer or a partial migration) gets the email_signals field
        # added here so downstream readers don't trip on its absence.
        state[vin].setdefault("email_signals", [])

    per_provider = state[vin].setdefault("per_provider", {})
    if provider not in per_provider:
        per_provider[provider] = {
            "first_seen": now,
            "last_seen": now,
            "last_metadata": raw_metadata or {},
            "listing_urls": [],
        }
    else:
        per_provider[provider]["last_seen"] = now
        per_provider[provider]["last_metadata"] = raw_metadata or {}

    if listing_url and listing_url not in per_provider[provider]["listing_urls"]:
        per_provider[provider]["listing_urls"].append(listing_url)

    save_seen_vins(state)


# ---------- email signals ----------


def add_email_signal(
    vin: str,
    provider: str,
    price_drop_delta: Optional[float] = None,
    ask_at_observation: Optional[float] = None,
    observed_at: Optional[str] = None,
) -> None:
    """Append an EmailSignal to a VIN's accumulated history.

    An EmailSignal is one observation of a VIN inside an authorized
    email alert. It carries the alert's provider name, the time we
    observed it, the asking price at that observation (if the alert
    reported one), and the price-drop delta the alert advertised (a
    positive number means the ask decreased by that amount since the
    alert's last sighting; cars.com / autotrader / cargurus all use
    positive-for-drop).

    Auto-creates the VIN record if it doesn't exist yet — an email
    signal for an unknown VIN is still worth logging for audit even
    if no MBUSA candidate ever materializes for it. The record is
    created with empty `per_provider` and the new signal in
    `email_signals`; `first_seen` / `last_seen` are stamped to now.

    Idempotent only in the trivial sense that calling it twice with
    identical args appends two records — that's deliberate, since each
    call represents a distinct observation event (e.g., two emails on
    different days both mentioning the same VIN-and-price).
    """
    state = load_seen_vins()
    now = observed_at or _now_iso()

    if vin not in state:
        state[vin] = {
            "first_seen": now,
            "last_seen": now,
            "per_provider": {},
            "email_signals": [],
        }
    else:
        state[vin]["last_seen"] = now
        state[vin].setdefault("email_signals", [])

    signal = {
        "provider": provider,
        "observed_at": now,
        "price_drop_delta": price_drop_delta,
        "ask_at_observation": ask_at_observation,
    }
    state[vin]["email_signals"].append(signal)

    save_seen_vins(state)


def get_email_signals(vin: str) -> list:
    """Return the EmailSignal history for a VIN.

    Returns an empty list when the VIN is unknown or when the record
    predates the v2 schema migration (defensive — load_seen_vins
    should have migrated it, but a degraded environment shouldn't
    crash callers).
    """
    state = load_seen_vins()
    record = state.get(vin)
    if not isinstance(record, dict):
        return []
    return list(record.get("email_signals") or [])


# ---------- queue ----------

def load_queue() -> list:
    _ensure_data_dir()
    if not QUEUE_PATH.exists():
        return []
    return json.loads(QUEUE_PATH.read_text())


def save_queue(queue: list) -> None:
    _ensure_data_dir()
    QUEUE_PATH.write_text(json.dumps(queue, indent=2))


def add_to_queue(candidate: dict) -> None:
    queue = load_queue()
    queue.append(candidate)
    save_queue(queue)


def pop_from_queue() -> Optional[dict]:
    """FIFO pop. Returns None on empty queue."""
    queue = load_queue()
    if not queue:
        return None
    candidate = queue.pop(0)
    save_queue(queue)
    return candidate


def queue_size() -> int:
    return len(load_queue())


# ---------- triaged ----------

def load_triaged() -> list:
    _ensure_data_dir()
    if not TRIAGED_PATH.exists():
        return []
    return json.loads(TRIAGED_PATH.read_text())


def append_triaged(verdict: dict) -> None:
    triaged = load_triaged()
    triaged.append(verdict)
    _ensure_data_dir()
    TRIAGED_PATH.write_text(json.dumps(triaged, indent=2))


def latest_triage_for_vin(vin: str) -> Optional[dict]:
    """Return the most recent triage record for a VIN, or None."""
    triaged = load_triaged()
    for entry in reversed(triaged):
        if entry.get("vin") == vin:
            return entry
    return None
