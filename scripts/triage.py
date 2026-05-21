"""Mercedes Sentinel triage — autonomous candidate evaluation.

Reads candidates from data/queue.json, sends each to Claude (Sonnet 4.6)
with the full project rubric as context, writes structured verdicts to
data/triaged.json.

Second stage of the daily pipeline (ingest → triage → email summary).
Invoked by scripts/daily.py at 4 PM via launchd. The dedup gate in
ingest tracks per-provider metadata snapshots so price-drop alerts
re-trigger triage on a previously-seen VIN. See scripts/README.md for
the full architecture and per-stage cost notes.

Run modes:

    python -m scripts.triage                  # drain entire queue
    python -m scripts.triage --limit N        # process N candidates then stop
    python -m scripts.triage --dry-run        # assemble prompts, print
                                              #   token estimates, do NOT
                                              #   call the API or write state
    python -m scripts.triage --vin VIN        # force re-triage of a specific
                                              #   VIN using its last known
                                              #   metadata (pulls from
                                              #   triaged.json's latest entry)
    python -m scripts.triage -v               # verbose / debug logging

The queue is FIFO. On API failure, the candidate stays in the queue so
the next run can retry it. On malformed verdicts (which the tool-use
schema should prevent, but defense in depth never hurts), the candidate
is written to triaged.json with verdict=NEEDS_HUMAN and the error
captured in reasoning.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    def load_dotenv() -> None:
        pass

from . import llm, state


def setup_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger("triage")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _build_triage_record(
    candidate: dict,
    verdict_payload: dict,
    error: Optional[str] = None,
) -> dict:
    """Wrap Claude's verdict with the metadata snapshot + context that
    makes the triaged.json entry self-contained and useful for later
    analysis."""
    record = {
        "vin": candidate.get("vin"),
        "triaged_at": _now_iso(),
        "provider": candidate.get("provider", "unknown"),
        "listing_url": candidate.get("listing_url"),
        "raw_metadata_snapshot": candidate.get("raw_metadata", {}),
        "discovered_at": candidate.get("discovered_at"),
        "verdict": verdict_payload.get("verdict", "NEEDS_HUMAN"),
        "reasoning": verdict_payload.get("reasoning", ""),
        "key_factors": verdict_payload.get("key_factors", {}),
        "action_items": verdict_payload.get("action_items", []),
    }
    if error:
        record["error"] = error
    return record


def _process_one(candidate: dict, logger: logging.Logger, dry_run: bool) -> Optional[dict]:
    """Triage a single candidate. Returns the triage record (or None on
    API failure that should re-queue the candidate)."""
    vin = candidate.get("vin", "?")
    provider = candidate.get("provider", "unknown")
    logger.info("Triaging %s | %s", provider, vin)

    if dry_run:
        est = llm.estimate_input_tokens()
        logger.info("  [dry-run] estimated system prompt tokens: ~%d", est)
        return None

    try:
        verdict = llm.triage(candidate)
    except Exception as e:
        logger.exception("Triage call failed for %s: %s", vin, e)
        # Returning None signals the caller to re-queue
        return None

    record = _build_triage_record(candidate, verdict)
    logger.info(
        "  -> %s | %s",
        record["verdict"],
        (record["reasoning"][:120] + "...") if len(record["reasoning"]) > 120 else record["reasoning"],
    )
    return record


def run(
    logger: logging.Logger,
    limit: Optional[int] = None,
    dry_run: bool = False,
    vin_filter: Optional[str] = None,
) -> dict:
    """Drain the queue (or force-triage a single VIN). Returns summary stats."""
    stats = {
        "processed": 0,
        "actions": 0,
        "passes": 0,
        "needs_human": 0,
        "errors": 0,
        "dry_run": dry_run,
    }

    if vin_filter:
        # Force-triage path: synthesize a candidate from the most recent
        # triaged record for the VIN. Useful for re-running triage after
        # tuning the prompt without waiting for a fresh ingest cycle.
        latest = state.latest_triage_for_vin(vin_filter)
        if latest is None:
            logger.error("No prior triage record for VIN %s — can't force re-triage", vin_filter)
            return stats
        candidate = {
            "vin": latest["vin"],
            "provider": latest["provider"],
            "listing_url": latest["listing_url"],
            "raw_metadata": latest["raw_metadata_snapshot"],
            "discovered_at": _now_iso(),
        }
        record = _process_one(candidate, logger, dry_run)
        if record is None and not dry_run:
            stats["errors"] += 1
        elif record is not None:
            state.append_triaged(record)
            stats["processed"] += 1
            _tally(stats, record["verdict"])
        return stats

    # Queue-drain path
    processed_count = 0
    failed_candidates = []  # re-queue at the end so we don't loop forever
    while True:
        if limit is not None and processed_count >= limit:
            break
        candidate = state.pop_from_queue()
        if candidate is None:
            break
        record = _process_one(candidate, logger, dry_run)
        if record is None:
            if dry_run:
                # Dry-run intentionally produces no record; not an error
                processed_count += 1
                stats["processed"] += 1
            else:
                stats["errors"] += 1
                failed_candidates.append(candidate)
        else:
            state.append_triaged(record)
            processed_count += 1
            stats["processed"] += 1
            _tally(stats, record["verdict"])

    # Re-queue anything that failed mid-run so the next run can retry.
    # Order is preserved (failures append in pop order).
    for c in failed_candidates:
        state.add_to_queue(c)
    if failed_candidates:
        logger.warning("Re-queued %d candidate(s) after API failures", len(failed_candidates))

    return stats


def _tally(stats: dict, verdict: str) -> None:
    if verdict == "ACTION":
        stats["actions"] += 1
    elif verdict == "PASS":
        stats["passes"] += 1
    elif verdict == "NEEDS_HUMAN":
        stats["needs_human"] += 1


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Triage queued GLS candidates via Claude API (Sonnet 4.6)."
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Stop after processing N candidates. Default: drain the entire queue.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Walk the queue and print token estimates without calling the API or writing state.",
    )
    parser.add_argument(
        "--vin", type=str, default=None,
        help="Force re-triage of a specific VIN using its last known metadata from triaged.json.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args(argv)

    load_dotenv()
    logger = setup_logging(args.verbose)

    if args.dry_run:
        logger.info("DRY-RUN: queue size at start = %d", state.queue_size())
        logger.info("Estimated system prompt tokens: ~%d", llm.estimate_input_tokens())

    try:
        stats = run(logger, limit=args.limit, dry_run=args.dry_run, vin_filter=args.vin)
    except Exception as e:
        logger.exception("Triage run failed: %s", e)
        return 1

    logger.info("Done. Stats: %s", stats)
    logger.info("Queue size after run: %d", state.queue_size())
    return 0


if __name__ == "__main__":
    sys.exit(main())
