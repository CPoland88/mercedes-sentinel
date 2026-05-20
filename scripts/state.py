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


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


# ---------- seen-vins ----------

def load_seen_vins() -> dict:
    _ensure_data_dir()
    if not SEEN_VINS_PATH.exists():
        return {}
    return json.loads(SEEN_VINS_PATH.read_text())


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
        }
    else:
        state[vin]["last_seen"] = now

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
