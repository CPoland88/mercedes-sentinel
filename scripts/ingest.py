"""Mercedes Sentinel ingest — daily watchlist processor.

Pulls candidates from two streams on every run:

  1. **MBUSA inventory API** (primary, post-pivot). Polls
     `nafta-service.mbusa.com` for current CPO inventory matching the
     CONTEXT.md spec, applies the distance / mileage / year hard caps,
     and queues every survivor with ``source: "mbusa"``.
  2. **Gmail saved-search alerts** (secondary). Polls the configured
     Gmail label for cars.com / autotrader / cargurus messages, parses
     each into candidate dicts, queues them under their provider's
     name. The email path is the legacy primary stream from before
     the MBUSA pivot — kept running for now because cars.com alerts
     still carry price-drop signal that commits 5–6 will fold into
     EmailSignal attachment on MBUSA candidates.

First stage of the daily pipeline (ingest → triage → email summary).
Triage lives in scripts/triage.py and runs autonomously via Claude;
the daily orchestrator scripts/daily.py wires both stages plus an
email summary, and is invoked at 4 PM by launchd. See scripts/README.md
for the full architecture and per-stage cost notes.

Run modes:

    python -m scripts.ingest                  # live: poll MBUSA + Gmail
    python -m scripts.ingest --dry-run        # live, do NOT mark read or write state
    python -m scripts.ingest --skip-mbusa     # only poll Gmail (ops escape valve)
    python -m scripts.ingest --fixtures DIR   # parse local .eml files; no IMAP, no MBUSA
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

from . import email_signal_matcher, mail, mbusa_inventory, state
from .mbusa_inventory import MbusaCandidate
from .parsers import parse as parse_email


# ---------- MBUSA query constants (derived from CONTEXT.md) ----------

# Vienna, VA — geographic center of the search per CONTEXT.md.
MBUSA_ZIP = "22180"

# MBUSA model designation codes for the two trims CONTEXT.md gates on.
# 450 is included only because Architecture B will let triage apply
# the "≥$15K below comp 580" trigger; the ingest gate doesn't have
# to encode that economics rule.
MBUSA_MODEL_CODES = ("GLS450W4", "GLS580W4")
MBUSA_CLASS_ID = "GLS"

# Short codes the MBUSA `exterior` query param accepts. The marketing-
# name match (Emerald Green Metallic / Twilight Blue Metallic /
# MANUFAKTUR Signature Ireland Mid Green Metallic) is a triage-side
# concern — the API filter is the coarse first-pass gate.
MBUSA_COLOR_CODES = ("BLU", "GRN")

# CPO only for now (MBUSA_PIVOT.md open question). Flip to "cpo,pre"
# once triage's foregone-warranty-discount logic lands.
MBUSA_INV_TYPE = "cpo"

# Distance: leave the API call unrestricted (`ANY`) and apply the
# CONTEXT.md hard cap (≤250 mi) as a post-filter against MBUSA's
# straight-line `dealer_distance_mi`. MBUSA's distance is not drive-
# miles, so the cap is conservative — we'd rather over-include and
# let triage reject than under-include and never see a candidate.
MBUSA_DISTANCE = "ANY"
MBUSA_MAX_DISTANCE_MI = 250.0

# CONTEXT.md hard mileage cap. Auto-Pass above this.
MBUSA_MAX_MILEAGE = 40000.0

# CONTEXT.md hard year floor. Pre-2024 X167 cars are out of scope.
MBUSA_MIN_MODEL_YEAR = 2024


def setup_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger("ingest")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _mbusa_candidate_to_dict(c: MbusaCandidate) -> dict:
    """Map an MbusaCandidate to the candidate-dict shape downstream
    code (``_process_candidates``, state.add_to_queue, triage) expects.

    Provider is hard-coded to ``"mbusa"``; ``source`` is the new
    post-pivot field that distinguishes the primary API stream from
    legacy email candidates. ``listing_url`` is None — MBUSA records
    don't carry a per-vehicle URL; the SPA constructs detail URLs
    client-side. Triage can use ``raw_metadata.dealer`` + dealer_city
    to search if a human needs the listing.

    The raw_metadata bundle carries everything triage needs to apply
    the CONTEXT.md scoring rubric: price, mileage, color (both code
    and marketing name), year, dealer identity and distance, CPO
    flag, and the factory option list — which is the build-sheet
    truth CONTEXT.md trusts for seating-config verification.
    """
    raw_metadata = {
        "price": c.ask_price,
        "mileage": c.mileage,
        "year": c.year,
        "model_name": c.model_name,
        "model_id": c.model_id,
        "exterior_meta_color": c.exterior_meta_color,
        "paint_marketing": c.paint_marketing,
        "dealer_name": c.dealer_name,
        "dealer_city": c.dealer_city,
        "dealer_state": c.dealer_state,
        "dealer_zip": c.dealer_zip,
        "dealer_distance_mi": c.dealer_distance_mi,
        "is_cpo": c.is_cpo,
        "option_list": list(c.option_list),
        "stock_id": c.stock_id,
    }
    return {
        "vin": c.vin,
        "provider": "mbusa",
        "source": "mbusa",
        "listing_url": None,
        "raw_metadata": raw_metadata,
    }


def _should_keep_mbusa(c: MbusaCandidate) -> tuple[bool, str]:
    """Apply CONTEXT.md hard caps to an MBUSA candidate.

    Returns ``(True, "")`` to keep, ``(False, reason)`` to drop. The
    reason is logged at debug so a curious operator can see why a
    given VIN didn't make it into the queue.

    Defensive against missing fields — a candidate that's missing
    mileage, distance, or year is treated as failing the gate. We'd
    rather under-include than queue a candidate with unknown
    geography that turns out to be in Alaska.
    """
    if c.year is None or c.year < MBUSA_MIN_MODEL_YEAR:
        return False, f"year {c.year} < {MBUSA_MIN_MODEL_YEAR}"
    if c.mileage is None or c.mileage > MBUSA_MAX_MILEAGE:
        return False, f"mileage {c.mileage} > {MBUSA_MAX_MILEAGE:.0f}"
    if c.dealer_distance_mi is None or c.dealer_distance_mi > MBUSA_MAX_DISTANCE_MI:
        return False, f"distance {c.dealer_distance_mi} > {MBUSA_MAX_DISTANCE_MI:.0f} mi"
    return True, ""


def run_mbusa_poll(
    logger: logging.Logger,
    write_state: bool,
    stats: dict,
) -> list[dict]:
    """Fetch current MBUSA inventory and enqueue surviving candidates.

    Two-stage filter: the API call narrows by zip/model/color/CPO/year
    range (cheap, server-side), then ``_should_keep_mbusa`` applies the
    CONTEXT.md hard caps on the response (free, client-side). Survivors
    flow through the same ``_process_candidates`` path the email loop
    uses, so dedup behavior is identical.

    Returns the list of candidate dicts that passed the filter and were
    sent to ``_process_candidates``. Callers can use this list as the
    "this-run MBUSA candidates" set for downstream EmailSignal matching.

    Stats keys added on every call (regardless of dry-run):

      - ``mbusa_records_returned``: total MBUSA API records before filter
      - ``mbusa_kept_after_filter``: survivors after distance/mileage/year
      - ``mbusa_filtered_out``: difference between the two
    """
    # Year range is computed at call time so the launchd job picks up
    # a new model-year window automatically without code changes. We
    # clamp `max_year` at the current calendar year — MBUSA's API
    # responds 503 (nginx upstream rejection) when queried for a model
    # year not yet present in its schema. The dynamic ceiling rolls
    # forward in January each year, which lags MB's typical late-Q3
    # model-year transition by a few months; new-MY CPO inventory is
    # rare enough during that window that the cost is negligible.
    max_year = datetime.now().year

    logger.info(
        "MBUSA poll: zip=%s models=%s years=%d-%d colors=%s invType=%s",
        MBUSA_ZIP,
        ",".join(MBUSA_MODEL_CODES),
        MBUSA_MIN_MODEL_YEAR,
        max_year,
        ",".join(MBUSA_COLOR_CODES),
        MBUSA_INV_TYPE,
    )

    mbusa_candidates = mbusa_inventory.fetch_matching_inventory(
        zip_code=MBUSA_ZIP,
        model_codes=MBUSA_MODEL_CODES,
        year_range=(MBUSA_MIN_MODEL_YEAR, max_year),
        color_codes=MBUSA_COLOR_CODES,
        class_id=MBUSA_CLASS_ID,
        inv_type=MBUSA_INV_TYPE,
        distance=MBUSA_DISTANCE,
    )
    stats["mbusa_records_returned"] = len(mbusa_candidates)
    logger.info("MBUSA poll: %d records returned", len(mbusa_candidates))

    kept: list[dict] = []
    for mc in mbusa_candidates:
        keep, reason = _should_keep_mbusa(mc)
        if not keep:
            logger.debug("Drop MBUSA %s: %s", mc.vin, reason)
            continue
        kept.append(_mbusa_candidate_to_dict(mc))

    stats["mbusa_kept_after_filter"] = len(kept)
    stats["mbusa_filtered_out"] = len(mbusa_candidates) - len(kept)
    logger.info(
        "MBUSA poll: %d kept after CONTEXT.md filters (%d dropped)",
        len(kept),
        stats["mbusa_filtered_out"],
    )

    _process_candidates(kept, logger, write_state, stats)
    return kept


def _attach_email_signals(
    signals: list,
    mbusa_candidates_this_run: list,
    logger: logging.Logger,
    write_state: bool,
    stats: dict,
) -> None:
    """Match cars.com EmailSignals to MBUSA candidates from this run
    and persist matches via state.add_email_signal.

    On match: log the (signal UUID, matched VIN, score), call
    state.add_email_signal with the signal's price-drop fields.
    On no match: log the signal UUID and the reason; the signal is
    discarded but the discard is observable in the daily-run audit.

    No persistence of orphan signals (those without a matching MBUSA
    candidate). Cars.com price-drop emails for VINs that MBUSA isn't
    returning today are almost always auto-Pass per CONTEXT.md (non-
    CPO, wrong color, or out of geography) so silently dropping is
    acceptable. We can persist orphans later if real data shows we're
    losing useful signal.
    """
    for signal in signals:
        outcome = email_signal_matcher.match_email_signal(
            signal, mbusa_candidates_this_run
        )
        signal_id = signal.get("cars_com_uuid", "<no-uuid>")
        if not outcome.matched:
            stats["email_signals_unmatched"] += 1
            logger.info(
                "Unmatched email signal %s: %s",
                signal_id,
                outcome.reason_no_match,
            )
            continue

        s_md = signal.get("raw_metadata") or {}
        logger.info(
            "Matched email signal %s -> VIN %s (score %.3f)",
            signal_id,
            outcome.matched_vin,
            outcome.score,
        )
        if write_state:
            state.add_email_signal(
                vin=outcome.matched_vin,
                provider=signal.get("provider", "cars_com"),
                price_drop_delta=s_md.get("price_drop_delta"),
                ask_at_observation=s_md.get("price"),
            )
        stats["email_signals_attached"] += 1


def _split_signals_and_candidates(items: list) -> tuple[list, list]:
    """Partition a parser's output into (email_signals, regular).

    EmailSignals are routed through the matcher + state.add_email_signal
    path; regular candidates flow through _process_candidates as before.
    The discriminator is the `source` field that
    scripts.parsers.cars_com.parse stamps on each EmailSignal dict.
    """
    signals: list = []
    regular: list = []
    for item in items:
        if item.get("source") == "email_signal":
            signals.append(item)
        else:
            regular.append(item)
    return signals, regular


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


def run_live(
    logger: logging.Logger,
    dry_run: bool,
    skip_mbusa: bool = False,
) -> dict:
    """Poll MBUSA + Gmail, parse, dedup, queue. Return summary stats.

    MBUSA polling runs first so MBUSA-derived candidates land in the
    queue before any email-derived ones for the same VIN. If MBUSA
    is unreachable, ``--skip-mbusa`` lets the email path still run;
    otherwise an MBUSA failure aborts the run (caller catches in main).
    """
    stats = {
        "mode": "live",
        "emails": 0,
        "candidates_extracted": 0,
        "new_candidates": 0,
        "duplicates": 0,
        "mbusa_records_returned": 0,
        "mbusa_kept_after_filter": 0,
        "mbusa_filtered_out": 0,
        "mbusa_skipped": False,
        "email_signals_attached": 0,
        "email_signals_unmatched": 0,
    }
    write_state = not dry_run

    mbusa_candidates_this_run: list[dict] = []
    if skip_mbusa:
        stats["mbusa_skipped"] = True
        logger.info("MBUSA poll skipped (--skip-mbusa)")
    else:
        mbusa_candidates_this_run = run_mbusa_poll(logger, write_state, stats)

    with mail.from_env() as poller:
        unread = poller.fetch_unread()
        stats["emails"] = len(unread)
        logger.info("Fetched %d unread email(s) from label %s", len(unread), poller.label)
        for uid, raw in unread:
            try:
                items = parse_email(raw)
            except Exception as e:
                logger.exception("Parser raised on uid=%s: %s", uid, e)
                continue
            stats["candidates_extracted"] += len(items)

            # Split the parser output: EmailSignals (cars.com post-pivot)
            # go through the matcher + state.add_email_signal path;
            # regular candidates (autotrader, cargurus, fallback) flow
            # through _process_candidates as before.
            email_signals, regular_candidates = _split_signals_and_candidates(items)
            _process_candidates(regular_candidates, logger, write_state, stats)
            _attach_email_signals(
                email_signals,
                mbusa_candidates_this_run,
                logger,
                write_state,
                stats,
            )
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
        help="Poll MBUSA + Gmail but do NOT mark messages read or write state. "
             "Useful for verifying parsers and the MBUSA path against live "
             "data without disrupting state.",
    )
    parser.add_argument(
        "--skip-mbusa",
        action="store_true",
        help="Skip the MBUSA inventory poll and only process Gmail. Escape "
             "valve for ops days when MBUSA is unreachable but emails should "
             "still flow.",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="Parse .eml files from a directory; skip IMAP and MBUSA. State "
             "is never written in this mode.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args(argv)

    load_dotenv()
    logger = setup_logging(args.verbose)

    if args.fixtures is not None:
        stats = run_fixtures(logger, args.fixtures)
    else:
        try:
            stats = run_live(
                logger,
                dry_run=args.dry_run,
                skip_mbusa=args.skip_mbusa,
            )
        except Exception as e:
            logger.exception("Ingest run failed: %s", e)
            return 1

    logger.info("Done. Stats: %s", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
