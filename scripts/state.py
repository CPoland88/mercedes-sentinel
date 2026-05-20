"""State management for the ingest pipeline.

Three JSON files in `data/`:

- `seen-vins.json` — dedup memory. Maps VIN to first-seen timestamp,
  the providers that have surfaced it, and every listing URL we've
  encountered for that VIN.
- `queue.json` — untriaged candidates. FIFO. Drained by triage in C2.
- `triaged.json` — append-only verdict history. Populated in C2.

All three live under `data/` and are gitignored. C1 only writes the
first two; `triaged.json` exists in the API surface so C2 has
somewhere to land without a follow-up state migration.
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
    return vin in load_seen_vins()


def mark_seen(vin: str, provider: str, listing_url: Optional[str]) -> None:
    """Record that a VIN has been observed. Idempotent — additional
    providers and URLs accumulate on the existing record."""
    state = load_seen_vins()
    if vin in state:
        if provider and provider not in state[vin]["providers"]:
            state[vin]["providers"].append(provider)
        if listing_url and listing_url not in state[vin]["listing_urls"]:
            state[vin]["listing_urls"].append(listing_url)
        state[vin]["last_seen"] = _now_iso()
    else:
        state[vin] = {
            "first_seen": _now_iso(),
            "last_seen": _now_iso(),
            "providers": [provider] if provider else [],
            "listing_urls": [listing_url] if listing_url else [],
        }
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
