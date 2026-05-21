"""Tests for scripts/notify.py.

No network. The SMTP send is exercised via a fake SMTP class
(`_FakeSMTP`) injected through the `smtp_factory` hook on
`send_email` / `send_daily_summary`.

The formatting functions (`build_email_subject`, `build_email_body`)
are pure — tested by feeding them report dicts and asserting the
output contains the expected substrings.
"""
import unittest
from unittest.mock import patch

from .. import notify


def _make_verdict(verdict, vin, price=90000, action_items=None):
    return {
        "vin": vin,
        "triaged_at": "2026-05-21T16:00:30-04:00",
        "provider": "cargurus",
        "listing_url": f"https://example.com/inv/{vin}",
        "raw_metadata_snapshot": {"price": price, "mileage": 5000, "deal_badge": "Great Deal"},
        "discovered_at": "2026-05-21T16:00:05-04:00",
        "verdict": verdict,
        "reasoning": f"Test reasoning for {vin}",
        "key_factors": {
            "trim": "580",
            "model_year": 2024,
            "price": price,
            "mileage": 5000,
            "distance_miles": 78,
            "dealer_tier": "A",
            "cpo_status": "cpo",
            "price_assessment": "at_market",
        },
        "action_items": action_items or ([] if verdict != "ACTION" else ["Call dealer"]),
    }


def _make_report(verdicts=None, errors=None, ingest=None, triage=None):
    return {
        "started_at": "2026-05-21T16:00:00-04:00",
        "ended_at": "2026-05-21T16:00:47-04:00",
        "ingest": ingest or {"emails": 5, "new_candidates": 3, "duplicates": 2},
        "triage": triage or {"processed": 3, "actions": 1, "passes": 2, "needs_human": 0, "errors": 0},
        "verdicts_today": verdicts or [],
        "errors": errors or [],
    }


# ---------- subject formatting ----------

class TestEmailSubject(unittest.TestCase):
    def test_subject_includes_date_and_counts(self):
        report = _make_report(verdicts=[
            _make_verdict("ACTION", "VIN1"),
            _make_verdict("PASS", "VIN2"),
            _make_verdict("PASS", "VIN3"),
        ])
        subject = notify.build_email_subject(report)
        self.assertIn("2026-05-21", subject)
        self.assertIn("1 ACTION", subject)
        self.assertIn("0 NEEDS_HUMAN", subject)
        self.assertIn("2 PASS", subject)
        self.assertTrue(subject.startswith("[Sentinel]"))

    def test_subject_empty_run(self):
        report = _make_report(verdicts=[])
        subject = notify.build_email_subject(report)
        self.assertIn("0 ACTION, 0 NEEDS_HUMAN, 0 PASS", subject)

    def test_subject_errors_no_verdicts(self):
        # Pipeline broke entirely — no verdicts produced
        report = _make_report(
            verdicts=[],
            errors=[{"phase": "ingest", "error": "IMAP timeout"}],
        )
        subject = notify.build_email_subject(report)
        self.assertIn("ERRORS", subject)
        self.assertIn("no verdicts produced", subject)

    def test_subject_errors_with_verdicts(self):
        # Some verdicts landed but there were also errors (e.g., 2/3 candidates processed,
        # 1 failed on API timeout). Surface both signals.
        report = _make_report(
            verdicts=[_make_verdict("ACTION", "VIN1")],
            errors=[{"phase": "triage", "error": "rate limit"}],
        )
        subject = notify.build_email_subject(report)
        self.assertIn("1 ACTION", subject)
        self.assertIn("with errors", subject)


# ---------- body formatting ----------

class TestEmailBody(unittest.TestCase):
    def test_body_header_present(self):
        body = notify.build_email_body(_make_report())
        self.assertIn("Mercedes Sentinel — Daily Summary", body)
        self.assertIn("2026-05-21", body)
        self.assertIn("16:00", body)
        self.assertIn("runtime 47s", body)

    def test_body_includes_all_three_verdict_blocks_even_when_empty(self):
        body = notify.build_email_body(_make_report(verdicts=[]))
        # Each block header is present even when zero verdicts
        self.assertIn("ACTION (0)", body)
        self.assertIn("NEEDS_HUMAN (0)", body)
        self.assertIn("PASS (0)", body)
        # And the empty marker appears in each
        self.assertEqual(body.count("(none)"), 3)

    def test_body_action_block_shows_action_items(self):
        report = _make_report(verdicts=[
            _make_verdict("ACTION", "VIN_ACT", action_items=["First step", "Second step"]),
        ])
        body = notify.build_email_body(report)
        self.assertIn("ACTION (1)", body)
        self.assertIn("VIN_ACT", body)
        self.assertIn("• First step", body)
        self.assertIn("• Second step", body)
        self.assertIn("Listing: https://example.com/inv/VIN_ACT", body)

    def test_body_pass_block_omits_action_items(self):
        # PASS verdicts shouldn't render an Action items section even if the
        # data has stray action_items entries (defensive — the prompt says
        # action_items should be empty for non-ACTION, but defense in depth).
        verdict = _make_verdict("PASS", "VIN_PASS")
        verdict["action_items"] = ["This should not render"]
        body = notify.build_email_body(_make_report(verdicts=[verdict]))
        self.assertNotIn("Action items:", body)
        self.assertNotIn("This should not render", body)

    def test_body_errors_block_at_top(self):
        report = _make_report(
            verdicts=[_make_verdict("ACTION", "VIN1")],
            errors=[{"phase": "ingest", "error": "IMAP timeout"}],
        )
        body = notify.build_email_body(report)
        # Errors block appears before the ACTION block in the body
        self.assertLess(body.index("Errors"), body.index("ACTION (1)"))
        self.assertIn("[ingest] IMAP timeout", body)

    def test_body_no_errors_block_when_clean(self):
        body = notify.build_email_body(_make_report())
        self.assertNotIn("Errors\n──", body)

    def test_body_run_stats_at_bottom(self):
        body = notify.build_email_body(_make_report())
        self.assertIn("Run stats", body)
        self.assertIn("Ingest:  5 unread, 3 new, 2 duplicates", body)
        self.assertIn("Triage:  3 processed, 1 ACTION, 0 NEEDS_HUMAN, 2 PASS, 0 errors", body)
        self.assertIn("Runtime: 47s", body)
        # Run stats must come AFTER the verdict blocks
        self.assertGreater(body.index("Run stats"), body.index("PASS (0)"))

    def test_body_handles_missing_ingest_or_triage(self):
        # If a phase didn't run at all, the report has None for that key.
        # Construct the report inline because the _make_report helper's
        # `or` fallbacks collapse None to defaults.
        report = {
            "started_at": "2026-05-21T16:00:00-04:00",
            "ended_at": "2026-05-21T16:00:01-04:00",
            "ingest": None,
            "triage": None,
            "verdicts_today": [],
            "errors": [{"phase": "ingest", "error": "boom"}, {"phase": "triage", "error": "also boom"}],
        }
        body = notify.build_email_body(report)
        # Both phases report "did not run"
        self.assertEqual(body.count("(did not run or failed)"), 2)


# ---------- SMTP send (mocked) ----------

class _FakeSMTP:
    """Fake smtplib.SMTP context manager. Records what was done."""
    last_instance = None

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.ehlo_calls = 0
        self.starttls_called = False
        self.login_args = None
        self.sent_messages = []
        _FakeSMTP.last_instance = self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def ehlo(self):
        self.ehlo_calls += 1

    def starttls(self):
        self.starttls_called = True

    def login(self, user, password):
        self.login_args = (user, password)

    def send_message(self, msg):
        self.sent_messages.append(msg)


class TestSendEmail(unittest.TestCase):
    def test_send_email_uses_starttls_and_login(self):
        notify.send_email(
            subject="Test subject",
            body="Test body",
            from_addr="from@example.com",
            password="pw",
            to_addr="to@example.com",
            smtp_factory=_FakeSMTP,
        )
        inst = _FakeSMTP.last_instance
        self.assertEqual(inst.host, notify.GMAIL_SMTP_HOST)
        self.assertEqual(inst.port, notify.GMAIL_SMTP_PORT)
        self.assertTrue(inst.starttls_called)
        self.assertEqual(inst.login_args, ("from@example.com", "pw"))
        self.assertEqual(len(inst.sent_messages), 1)
        msg = inst.sent_messages[0]
        self.assertEqual(msg["Subject"], "Test subject")
        self.assertEqual(msg["From"], "from@example.com")
        self.assertEqual(msg["To"], "to@example.com")

    def test_send_email_calls_ehlo_around_starttls(self):
        # Gmail requires ehlo before AND after starttls so the server
        # re-sends its extended-feature list over the encrypted channel.
        notify.send_email(
            subject="x", body="y",
            from_addr="a@b.c", password="pw", to_addr="d@e.f",
            smtp_factory=_FakeSMTP,
        )
        self.assertGreaterEqual(_FakeSMTP.last_instance.ehlo_calls, 2)


class TestSendDailySummary(unittest.TestCase):
    @patch.dict("os.environ", {
        "IMAP_USERNAME": "test@example.com",
        "IMAP_APP_PASSWORD": "testpw",
    }, clear=True)
    def test_self_mail_default_when_email_to_unset(self):
        report = _make_report(verdicts=[_make_verdict("ACTION", "VIN1")])
        notify.send_daily_summary(report, smtp_factory=_FakeSMTP)
        msg = _FakeSMTP.last_instance.sent_messages[0]
        # No EMAIL_TO env -> sender == recipient
        self.assertEqual(msg["From"], "test@example.com")
        self.assertEqual(msg["To"], "test@example.com")

    @patch.dict("os.environ", {
        "IMAP_USERNAME": "test@example.com",
        "IMAP_APP_PASSWORD": "testpw",
        "EMAIL_TO": "recipient@example.com",
    }, clear=True)
    def test_email_to_env_overrides_recipient(self):
        report = _make_report()
        notify.send_daily_summary(report, smtp_factory=_FakeSMTP)
        msg = _FakeSMTP.last_instance.sent_messages[0]
        self.assertEqual(msg["From"], "test@example.com")
        self.assertEqual(msg["To"], "recipient@example.com")

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_credentials_raises(self):
        report = _make_report()
        with self.assertRaises(RuntimeError) as ctx:
            notify.send_daily_summary(report, smtp_factory=_FakeSMTP)
        self.assertIn("IMAP_USERNAME", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
