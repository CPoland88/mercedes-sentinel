"""Tests for scripts/daily.py (C3 orchestrator).

The three subordinate modules — ingest, triage, notify — are mocked
so the orchestrator's control flow is testable without IMAP, the
Anthropic API, or SMTP.

State paths are redirected into a tempdir so we can populate
triaged.json with prior entries and verify the orchestrator
correctly isolates "today's verdicts" from accumulated history.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from .. import daily, ingest, notify, state, triage


def _prior_triage(vin, verdict="PASS"):
    return {
        "vin": vin,
        "triaged_at": "2026-05-20T16:00:00-04:00",
        "provider": "cargurus",
        "listing_url": f"https://example.com/{vin}",
        "raw_metadata_snapshot": {"price": 90000},
        "verdict": verdict,
        "reasoning": "prior run",
        "key_factors": {},
        "action_items": [],
    }


def _new_triage(vin, verdict="ACTION"):
    return {
        "vin": vin,
        "triaged_at": "2026-05-21T16:00:30-04:00",
        "provider": "cargurus",
        "listing_url": f"https://example.com/{vin}",
        "raw_metadata_snapshot": {"price": 95000},
        "verdict": verdict,
        "reasoning": "today's run",
        "key_factors": {},
        "action_items": ["next step"] if verdict == "ACTION" else [],
    }


class TestDailyOrchestrator(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_dir = Path(self._tmp.name)
        self._state_patches = [
            patch.object(state, "DATA_DIR", self._tmp_dir),
            patch.object(state, "SEEN_VINS_PATH", self._tmp_dir / "seen-vins.json"),
            patch.object(state, "QUEUE_PATH", self._tmp_dir / "queue.json"),
            patch.object(state, "TRIAGED_PATH", self._tmp_dir / "triaged.json"),
        ]
        for p in self._state_patches:
            p.start()
        self.logger = daily.setup_logging(verbose=False)

    def tearDown(self):
        for p in self._state_patches:
            p.stop()
        self._tmp.cleanup()

    # ---- happy path ----

    def test_full_pipeline_success(self):
        # Pre-seed triaged.json with a prior verdict; today's run should
        # NOT include this in verdicts_today.
        state.append_triaged(_prior_triage("VIN_PRIOR"))

        def fake_triage_run(logger, **kwargs):
            # Simulate triage producing one new verdict
            state.append_triaged(_new_triage("VIN_NEW"))
            return {"processed": 1, "actions": 1, "passes": 0, "needs_human": 0, "errors": 0}

        with patch.object(ingest, "run_live", return_value={"emails": 1, "new_candidates": 1, "duplicates": 0}) as mock_ingest, \
             patch.object(triage, "run", side_effect=fake_triage_run) as mock_triage:
            report = daily.run_daily(self.logger)

        mock_ingest.assert_called_once()
        mock_triage.assert_called_once()
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["ingest"]["emails"], 1)
        self.assertEqual(report["triage"]["actions"], 1)
        # verdicts_today contains only the new verdict, not the prior one
        self.assertEqual(len(report["verdicts_today"]), 1)
        self.assertEqual(report["verdicts_today"][0]["vin"], "VIN_NEW")

    # ---- partial failures ----

    def test_ingest_failure_still_runs_triage(self):
        # Pre-seed the queue with a candidate from yesterday so triage
        # has something to drain even though today's ingest failed.
        state.add_to_queue({
            "vin": "VIN_QUEUED", "provider": "cargurus",
            "listing_url": "https://e.com/q", "raw_metadata": {},
        })

        def fake_triage_run(logger, **kwargs):
            state.append_triaged(_new_triage("VIN_QUEUED", verdict="PASS"))
            return {"processed": 1, "actions": 0, "passes": 1, "needs_human": 0, "errors": 0}

        with patch.object(ingest, "run_live", side_effect=RuntimeError("IMAP timeout")), \
             patch.object(triage, "run", side_effect=fake_triage_run) as mock_triage:
            report = daily.run_daily(self.logger)

        # Triage still ran
        mock_triage.assert_called_once()
        # Error recorded
        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(report["errors"][0]["phase"], "ingest")
        self.assertIn("IMAP timeout", report["errors"][0]["error"])
        # Triage stats present, today's verdict captured
        self.assertEqual(report["triage"]["passes"], 1)
        self.assertEqual(len(report["verdicts_today"]), 1)

    def test_triage_failure_still_produces_report(self):
        with patch.object(ingest, "run_live", return_value={"emails": 0, "new_candidates": 0, "duplicates": 0}), \
             patch.object(triage, "run", side_effect=RuntimeError("anthropic API down")):
            report = daily.run_daily(self.logger)

        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(report["errors"][0]["phase"], "triage")
        self.assertIn("anthropic API down", report["errors"][0]["error"])
        # Report is still well-formed
        self.assertIn("started_at", report)
        self.assertIn("ended_at", report)
        self.assertEqual(report["verdicts_today"], [])

    def test_both_phases_fail(self):
        with patch.object(ingest, "run_live", side_effect=RuntimeError("IMAP timeout")), \
             patch.object(triage, "run", side_effect=RuntimeError("API down")):
            report = daily.run_daily(self.logger)
        self.assertEqual(len(report["errors"]), 2)
        phases = {e["phase"] for e in report["errors"]}
        self.assertEqual(phases, {"ingest", "triage"})

    # ---- verdicts_today isolation ----

    def test_verdicts_today_excludes_prior_history(self):
        # Three prior verdicts already in triaged.json
        for vin in ["OLD1", "OLD2", "OLD3"]:
            state.append_triaged(_prior_triage(vin))

        def fake_triage_run(logger, **kwargs):
            state.append_triaged(_new_triage("NEW1", verdict="ACTION"))
            state.append_triaged(_new_triage("NEW2", verdict="PASS"))
            return {"processed": 2, "actions": 1, "passes": 1, "needs_human": 0, "errors": 0}

        with patch.object(ingest, "run_live", return_value={"emails": 2, "new_candidates": 2, "duplicates": 0}), \
             patch.object(triage, "run", side_effect=fake_triage_run):
            report = daily.run_daily(self.logger)

        # Today's verdicts are ONLY the two new ones, in order
        self.assertEqual(len(report["verdicts_today"]), 2)
        self.assertEqual([v["vin"] for v in report["verdicts_today"]], ["NEW1", "NEW2"])

    def test_empty_run_produces_empty_verdicts_today(self):
        with patch.object(ingest, "run_live", return_value={"emails": 0, "new_candidates": 0, "duplicates": 0}), \
             patch.object(triage, "run", return_value={"processed": 0, "actions": 0, "passes": 0, "needs_human": 0, "errors": 0}):
            report = daily.run_daily(self.logger)

        self.assertEqual(report["verdicts_today"], [])
        self.assertEqual(report["errors"], [])


class TestDailyMain(unittest.TestCase):
    """End-to-end of main() with all subordinates mocked."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_dir = Path(self._tmp.name)
        self._state_patches = [
            patch.object(state, "DATA_DIR", self._tmp_dir),
            patch.object(state, "SEEN_VINS_PATH", self._tmp_dir / "seen-vins.json"),
            patch.object(state, "QUEUE_PATH", self._tmp_dir / "queue.json"),
            patch.object(state, "TRIAGED_PATH", self._tmp_dir / "triaged.json"),
        ]
        for p in self._state_patches:
            p.start()

    def tearDown(self):
        for p in self._state_patches:
            p.stop()
        self._tmp.cleanup()

    def test_main_sends_email_by_default(self):
        with patch.object(ingest, "run_live", return_value={"emails": 0, "new_candidates": 0, "duplicates": 0}), \
             patch.object(triage, "run", return_value={"processed": 0, "actions": 0, "passes": 0, "needs_human": 0, "errors": 0}), \
             patch.object(notify, "send_daily_summary") as mock_send:
            rc = daily.main([])
        mock_send.assert_called_once()
        self.assertEqual(rc, 0)

    def test_main_skips_email_with_no_email_flag(self):
        with patch.object(ingest, "run_live", return_value={"emails": 0, "new_candidates": 0, "duplicates": 0}), \
             patch.object(triage, "run", return_value={"processed": 0, "actions": 0, "passes": 0, "needs_human": 0, "errors": 0}), \
             patch.object(notify, "send_daily_summary") as mock_send:
            rc = daily.main(["--no-email"])
        mock_send.assert_not_called()
        self.assertEqual(rc, 0)

    def test_main_does_not_propagate_email_failure(self):
        # Even if SMTP send fails, the orchestrator should NOT crash.
        # Verdicts are persisted; losing the email is a notification
        # problem, not a data problem.
        with patch.object(ingest, "run_live", return_value={"emails": 0, "new_candidates": 0, "duplicates": 0}), \
             patch.object(triage, "run", return_value={"processed": 0, "actions": 0, "passes": 0, "needs_human": 0, "errors": 0}), \
             patch.object(notify, "send_daily_summary", side_effect=RuntimeError("SMTP refused")):
            rc = daily.main([])
        # rc=1 because the email failure was recorded as an error in the report
        self.assertEqual(rc, 1)

    def test_main_returns_1_on_phase_errors(self):
        with patch.object(ingest, "run_live", side_effect=RuntimeError("boom")), \
             patch.object(triage, "run", return_value={"processed": 0, "actions": 0, "passes": 0, "needs_human": 0, "errors": 0}), \
             patch.object(notify, "send_daily_summary"):
            rc = daily.main([])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
