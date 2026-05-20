"""Mercedes Sentinel ingest — daily watchlist processor.

Polls Gmail for new saved-search alerts (Cars.com, AutoTrader, CarGurus),
extracts VINs and listing URLs from each, dedups by VIN, and queues new
candidates for downstream triage.

Status: C1 of a 3-commit build.
  - C1 (this file): poll + parse + dedup + queue. No Claude API, no
    notifications.
  - C2 (next): autonomous triage via Claude API → verdicts in
    triaged.json.
  - C3 (last): launchd daily-at-4-PM + macOS notification + email
    summary.

Run modes:

    python -m scripts.ingest                  # live: poll Gmail, mark read
    python -m scripts.ingest --dry-run        # live: poll Gmail, do NOT
                                              #   mark read, do NOT write state
    python -m scripts.ingest --fixtures DIR   # parse local .eml files; no IMAP
    python -m scripts.ingest -v               # verbose / debug logging
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover — only relevant before requirements installed
    def load_dotenv() -> None:
        pass

from . import mail, state
from .parsers import parse as parse_email


def setup_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger("ingest")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _process_candidates(
    candidates: list,
    logger: logging.Logger,
    write_state: bool,
    stats: dict,
) -> None:
    for c in candidates:
        vin = c.get("vin")
        if not vin:
            logger.warning("Candidate missing VIN: %r", c)
            continue

        provider = c.get("provider", "unknown")
        raw_metadata = c.get("raw_metadata") or {}

        # The C2 dedup gate: enqueue when VIN is unseen, when this is a
        # new provider for a known VIN, or when the metadata changed
        # since last time we saw this (vin, provider) pair. The third
        # case is what catches price-drop alerts on a previously-triaged
        # VIN — those would otherwise be silently deduped out.
        if not state.should_enqueue(vin, provider, raw_metadata):
            stats["duplicates"] += 1
            logger.debug("Skip VIN %s (provider=%s) — unchanged since last seen", vin, provider)
            continue

        if write_state:
            state.mark_seen(vin, provider, c.get("listing_url"), raw_metadata)
            state.add_to_queue({**c, "discovered_at": _now_iso()})
        stats["new_candidates"] += 1
        logger.info(
            "Enqueue: %s | %s | %s",
            provider,
            vin,
            c.get("listing_url") or "(no URL)",
        )


def run_live(logger: logging.Logger, dry_run: bool) -> dict:
    """Poll Gmail, parse, dedup, queue. Return summary stats."""
    stats = {
        "mode": "live",
        "emails": 0,
        "candidates_extracted": 0,
        "new_candidates": 0,
        "duplicates": 0,
    }
    write_state = not dry_run
    with mail.from_env() as poller:
        unread = poller.fetch_unread()
        stats["emails"] = len(unread)
        logger.info("Fetched %d unread email(s) from label %s", len(unread), poller.label)
        for uid, raw in unread:
            try:
                candidates = parse_email(raw)
            except Exception as e:
                logger.exception("Parser raised on uid=%s: %s", uid, e)
                continue
            stats["candidates_extracted"] += len(candidates)
            _process_candidates(candidates, logger, write_state, stats)
            if not dry_run:
                poller.mark_read(uid)
    return stats


def run_fixtures(logger: logging.Logger, fixture_dir: Path) -> dict:
    """Parse a directory of .eml fixture files. No IMAP. No state writes."""
    stats = {
        "mode": "fixtures",
        "fixture_dir": str(fixture_dir),
        "emails": 0,
        "candidates_extracted": 0,
        "new_candidates": 0,
        "duplicates": 0,
    }
    if not fixture_dir.is_dir():
        logger.error("Fixture directory does not exist: %s", fixture_dir)
        return stats
    eml_files = sorted(fixture_dir.glob("*.eml"))
    if not eml_files:
        logger.warning("No .eml files in %s — add real samples to test parsers", fixture_dir)
        return stats
    for eml_path in eml_files:
        raw = eml_path.read_bytes()
        try:
            candidates = parse_email(raw)
        except Exception as e:
            logger.exception("Parser raised on %s: %s", eml_path.name, e)
            continue
        stats["emails"] += 1
        stats["candidates_extracted"] += len(candidates)
        logger.info("Fixture %s → %d candidate(s)", eml_path.name, len(candidates))
        for c in candidates:
            logger.info(
                "  %-10s | %s | %s",
                c.get("provider", "unknown"),
                c.get("vin", "?"),
                c.get("listing_url") or "(no URL)",
            )
            if c.get("raw_metadata"):
                logger.info("    metadata: %s", c["raw_metadata"])
        # Fixture mode does not persist state — we just verify parsers run.
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Poll Gmail saved-search alerts and queue new GLS candidates."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Poll Gmail but do NOT mark messages read or write state. "
             "Useful for verifying parsers against live alerts without disrupting state.",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="Parse .eml files from a directory; skip IMAP. State is never written in this mode.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args(argv)

    load_dotenv()
    logger = setup_logging(args.verbose)

    if args.fixtures is not None:
        stats = run_fixtures(logger, args.fixtures)
    else:
        try:
            stats = run_live(logger, dry_run=args.dry_run)
        except Exception as e:
            logger.exception("Ingest run failed: %s", e)
            return 1

    logger.info("Done. Stats: %s", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
