"""C3 — daily orchestrator.

This is the entry point launchd invokes at 4 PM local time each day.
It runs the full pipeline in sequence: ingest -> triage -> email
summary. Partial failures don't abort the run — a failed ingest
doesn't prevent triage from draining yesterday's queue, and a
failed triage still produces an email reporting the failure.

The email summary is best-effort: if SMTP send fails, the run still
completes successfully and verdicts remain persisted in
data/triaged.json. We don't want to lose verdict data because of an
email delivery problem.

Status: C3 of the 3-commit build (this is the final commit).

Run modes:

    python -m scripts.daily         # full pipeline + email
    python -m scripts.daily --no-email  # skip email send (useful for testing
                                        # changes to ingest/triage without
                                        # spamming yourself)
    python -m scripts.daily -v      # verbose / debug logging

The orchestrator is testable without network access — tests mock
ingest, triage, and notify modules and verify the report shape +
failure handling.
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

from . import ingest, notify, state, triage


def setup_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger("daily")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def run_daily(logger: logging.Logger) -> dict:
    """Run the full pipeline and return a report dict for notify.

    The report is the contract between this function and
    `notify.send_daily_summary`. See notify.py for the shape.
    """
    report = {
        "started_at": _now_iso(),
        "ended_at": None,
        "ingest": None,
        "triage": None,
        "verdicts_today": [],
        "errors": [],
    }

    # Snapshot triaged.json size BEFORE the run so we can identify
    # exactly which verdicts were produced today (vs prior accumulated
    # history). The triaged log is append-only, so taking the slice
    # from `before_len` to end gives us today's verdicts.
    before_len = len(state.load_triaged())

    # Ingest phase
    try:
        logger.info("Starting ingest phase")
        report["ingest"] = ingest.run_live(logger, dry_run=False)
        logger.info("Ingest complete: %s", report["ingest"])
    except Exception as e:
        logger.exception("Ingest phase failed: %s", e)
        report["errors"].append({"phase": "ingest", "error": str(e)})

    # Triage phase — runs regardless of ingest outcome, since the
    # queue may still have unprocessed candidates from prior runs.
    try:
        logger.info("Starting triage phase")
        report["triage"] = triage.run(logger, limit=None, dry_run=False, vin_filter=None)
        logger.info("Triage complete: %s", report["triage"])
    except Exception as e:
        logger.exception("Triage phase failed: %s", e)
        report["errors"].append({"phase": "triage", "error": str(e)})

    # Today's verdicts = whatever got appended during this run
    try:
        after = state.load_triaged()
        report["verdicts_today"] = after[before_len:]
    except Exception as e:
        logger.exception("Could not load triaged.json after run: %s", e)
        report["errors"].append({"phase": "load_triaged", "error": str(e)})

    report["ended_at"] = _now_iso()
    return report


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mercedes Sentinel daily orchestrator (C3). Runs ingest + triage + email summary."
    )
    parser.add_argument(
        "--no-email", action="store_true",
        help="Skip the email summary. Useful for testing pipeline changes "
             "without filling your inbox.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args(argv)

    load_dotenv()
    logger = setup_logging(args.verbose)
    logger.info("=" * 60)
    logger.info("Mercedes Sentinel daily run starting")

    report = run_daily(logger)

    if args.no_email:
        logger.info("--no-email set; skipping email summary")
    else:
        try:
            notify.send_daily_summary(report)
        except Exception as e:
            # Email-send failure is logged but does NOT propagate.
            # Verdicts are already persisted in data/triaged.json;
            # losing the email is a notification problem, not a data
            # problem. The caller (launchd) sees a successful exit,
            # which is the right signal — the pipeline ran fine.
            logger.exception("Email send failed; report not delivered: %s", e)
            report["errors"].append({"phase": "email", "error": str(e)})

    # Final summary line, useful when scanning logs
    n_verdicts = len(report["verdicts_today"])
    n_errors = len(report["errors"])
    logger.info(
        "Run complete: %d verdict(s), %d error(s). Pipeline %s.",
        n_verdicts, n_errors,
        "OK" if n_errors == 0 else "had failures (see above)",
    )
    logger.info("=" * 60)

    # Exit code conventions:
    #   0 — pipeline ran cleanly
    #   1 — one or more phases had errors (launchd / monitoring will
    #       see this; not currently used for anything, but available)
    return 0 if n_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
