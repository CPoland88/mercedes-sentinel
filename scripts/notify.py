"""C3 — daily email summary.

Builds a plaintext daily-summary email from a run-report dict and
sends it via Gmail SMTP using the existing IMAP app password.
Gmail app passwords are scoped to all IMAP / SMTP / POP services,
so the credentials already in `.env` work for both directions —
no new secrets to manage.

Two concerns are separated so the formatter is testable without
the network:

* `build_email_subject` / `build_email_body` take a run-report dict
  and produce strings. Pure functions, fully deterministic.
* `send_email` opens an SMTP connection and ships the message.
  Tested with a mocked `smtplib.SMTP` so no real network call.
* `send_daily_summary` is the high-level entry point the daily
  orchestrator calls.

Run-report dict shape (produced by `scripts.daily`):

    {
      "started_at": "2026-05-21T16:00:03-04:00",
      "ended_at":   "2026-05-21T16:00:50-04:00",
      "ingest":     {<ingest stats dict>}  | None,
      "triage":     {<triage stats dict>}  | None,
      "verdicts_today": [<triage record>, ...],  # may be empty
      "errors": [{"phase": "ingest" | "triage" | "email", "error": "..."}, ...],
    }
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587  # STARTTLS port; 465 is SMTPS (deprecated for new code)

SUBJECT_PREFIX = "[Sentinel]"


# ---------- formatting ----------

def _verdict_counts(verdicts: list) -> dict:
    counts = {"ACTION": 0, "NEEDS_HUMAN": 0, "PASS": 0}
    for v in verdicts:
        verdict = v.get("verdict", "")
        if verdict in counts:
            counts[verdict] += 1
    return counts


def _date_from_iso(ts: Optional[str]) -> str:
    """Extract YYYY-MM-DD from an ISO timestamp. Returns '????-??-??' on failure."""
    if not ts:
        return "????-??-??"
    return ts[:10]


def _time_from_iso(ts: Optional[str]) -> str:
    """Extract HH:MM from an ISO timestamp."""
    if not ts or len(ts) < 16:
        return "??:??"
    return ts[11:16]


def _runtime_seconds(report: dict) -> Optional[int]:
    """Compute runtime in seconds from started_at / ended_at, or None."""
    try:
        from datetime import datetime
        start = datetime.fromisoformat(report["started_at"])
        end = datetime.fromisoformat(report["ended_at"])
        return int((end - start).total_seconds())
    except Exception:
        return None


def build_email_subject(report: dict) -> str:
    """`[Sentinel] 2026-05-21 — 1 ACTION, 0 NEEDS_HUMAN, 3 PASS`

    If there were errors and no verdicts, surface that in the
    subject so the bad-day signal isn't buried in the body.
    """
    date = _date_from_iso(report.get("started_at"))
    counts = _verdict_counts(report.get("verdicts_today", []))
    has_errors = bool(report.get("errors"))

    if not report.get("verdicts_today") and has_errors:
        return f"{SUBJECT_PREFIX} {date} — ERRORS, no verdicts produced"

    parts = f"{counts['ACTION']} ACTION, {counts['NEEDS_HUMAN']} NEEDS_HUMAN, {counts['PASS']} PASS"
    suffix = " (with errors)" if has_errors else ""
    return f"{SUBJECT_PREFIX} {date} — {parts}{suffix}"


def _format_verdict_block(verdicts: list, tier: str) -> list:
    """Format one verdict tier's block. Returns list of body lines."""
    filtered = [v for v in verdicts if v.get("verdict") == tier]
    lines = [f"{tier} ({len(filtered)})", "─" * (len(tier) + 6)]

    if not filtered:
        lines.append("(none)")
        lines.append("")
        return lines

    for v in filtered:
        vin = v.get("vin", "?")
        provider = v.get("provider", "?")
        snap = v.get("raw_metadata_snapshot", {}) or {}
        price = snap.get("price")
        price_str = f"${price:,}" if isinstance(price, int) else "?"
        kf = v.get("key_factors", {}) or {}
        trim = kf.get("trim", "?")
        model_year = kf.get("model_year", "?")
        mileage = kf.get("mileage") or snap.get("mileage")
        mileage_str = f"{mileage:,} mi" if isinstance(mileage, int) else "? mi"
        cpo = kf.get("cpo_status", "?")
        dealer_tier = kf.get("dealer_tier") or "?"
        distance = kf.get("distance_miles")
        distance_str = f"~{distance} mi" if isinstance(distance, int) else "? mi"

        lines.append(
            f"{vin} — {model_year} GLS {trim} — {price_str} — {provider}"
        )
        lines.append(f"  Tier {dealer_tier} • {distance_str} • {mileage_str} • CPO: {cpo}")
        reasoning = (v.get("reasoning") or "").strip()
        if reasoning:
            # Wrap reasoning to keep body readable on mobile (single block, not hard-wrapped)
            lines.append(f"  Reasoning: {reasoning}")
        if tier == "ACTION":
            action_items = v.get("action_items") or []
            if action_items:
                lines.append("  Action items:")
                for item in action_items:
                    lines.append(f"    • {item}")
        url = v.get("listing_url")
        if url:
            lines.append(f"  Listing: {url}")
        lines.append("")

    return lines


def _format_errors_block(errors: list) -> list:
    if not errors:
        return []
    lines = ["Errors", "─" * 6]
    for e in errors:
        phase = e.get("phase", "?")
        msg = e.get("error", "?")
        lines.append(f"  [{phase}] {msg}")
    lines.append("")
    return lines


def _format_run_stats_block(report: dict) -> list:
    lines = ["Run stats", "─" * 9]
    ingest = report.get("ingest")
    if ingest:
        lines.append(
            f"  Ingest:  {ingest.get('emails', 0)} unread, "
            f"{ingest.get('new_candidates', 0)} new, "
            f"{ingest.get('duplicates', 0)} duplicates"
        )
    else:
        lines.append("  Ingest:  (did not run or failed)")

    triage = report.get("triage")
    if triage:
        lines.append(
            f"  Triage:  {triage.get('processed', 0)} processed, "
            f"{triage.get('actions', 0)} ACTION, "
            f"{triage.get('needs_human', 0)} NEEDS_HUMAN, "
            f"{triage.get('passes', 0)} PASS, "
            f"{triage.get('errors', 0)} errors"
        )
    else:
        lines.append("  Triage:  (did not run or failed)")

    runtime = _runtime_seconds(report)
    if runtime is not None:
        lines.append(f"  Runtime: {runtime}s")

    return lines


def build_email_body(report: dict) -> str:
    """Build the plaintext email body from a run-report dict.

    Layout: header → errors (if any, surfaced at top) → ACTION →
    NEEDS_HUMAN → PASS → run stats. Verdict blocks always appear
    even when empty so the reader knows the system checked.
    """
    date = _date_from_iso(report.get("started_at"))
    time = _time_from_iso(report.get("started_at"))
    runtime = _runtime_seconds(report)
    runtime_str = f"runtime {runtime}s" if runtime is not None else "runtime ?"

    lines = [
        "Mercedes Sentinel — Daily Summary",
        f"{date} {time} — {runtime_str}",
        "",
    ]

    lines.extend(_format_errors_block(report.get("errors", [])))

    verdicts = report.get("verdicts_today", [])
    lines.extend(_format_verdict_block(verdicts, "ACTION"))
    lines.extend(_format_verdict_block(verdicts, "NEEDS_HUMAN"))
    lines.extend(_format_verdict_block(verdicts, "PASS"))

    lines.extend(_format_run_stats_block(report))

    return "\n".join(lines)


# ---------- SMTP send ----------

def _smtp_credentials() -> dict:
    """Pull SMTP credentials from environment. EMAIL_TO defaults to
    IMAP_USERNAME so the script self-mails by default — no extra
    config needed for the common case."""
    username = os.environ.get("IMAP_USERNAME")
    password = os.environ.get("IMAP_APP_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "Missing IMAP credentials in environment. SMTP uses the same "
            "credentials as IMAP. Set IMAP_USERNAME + IMAP_APP_PASSWORD in .env."
        )
    to_addr = os.environ.get("EMAIL_TO") or username
    return {"from": username, "password": password, "to": to_addr}


def send_email(
    subject: str,
    body: str,
    from_addr: str,
    password: str,
    to_addr: str,
    smtp_factory=None,
) -> None:
    """Send a plaintext email via Gmail SMTP (STARTTLS on 587).

    `smtp_factory` is a hook for tests — defaults to `smtplib.SMTP`.
    Tests pass a mock that records the connection without calling
    the network.

    Raises on send failure. The caller decides whether to log + swallow
    or propagate (the daily orchestrator logs + swallows so a failed
    email doesn't lose the day's verdict data).
    """
    factory = smtp_factory or smtplib.SMTP

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    with factory(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(from_addr, password)
        server.send_message(msg)
    logger.info("Sent daily summary email: subject=%r to=%s", subject, to_addr)


def send_daily_summary(report: dict, smtp_factory=None) -> None:
    """High-level entry point: build subject + body from the report,
    pull SMTP credentials from env, send. `smtp_factory` is a hook
    for tests (same as `send_email`)."""
    creds = _smtp_credentials()
    subject = build_email_subject(report)
    body = build_email_body(report)
    send_email(
        subject=subject,
        body=body,
        from_addr=creds["from"],
        password=creds["password"],
        to_addr=creds["to"],
        smtp_factory=smtp_factory,
    )
