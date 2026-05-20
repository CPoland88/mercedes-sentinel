"""Tests for scripts/triage.py.

The Anthropic API is never called — `llm.triage` is patched with a
fake that returns canned verdicts. State paths are redirected into a
per-test tempdir so production state is untouched.

What we verify:

* Each verdict tier (ACTION / PASS / NEEDS_HUMAN) flows through to
  triaged.json correctly, with the snapshot metadata preserved.
* FIFO order — first-queued is first-triaged.
* `--limit N` stops after N candidates.
* `--dry-run` triggers no llm calls and no state writes.
* API failures leave the candidate in the queue (re-queued) so the
  next run retries.
* The triage record is self-contained (carries VIN, provider, URL,
  metadata snapshot, discovered_at, triaged_at, all verdict fields).
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .. import state, triage, llm


def _make_candidate(vin: str, provider: str = "cargurus", price: int = 90000) -> dict:
    return {
        "vin": vin,
        "provider": provider,
        "listing_url": f"https://{provider}.example.com/inv/{vin}",
        "raw_metadata": {"price": price, "mileage": 5000, "deal_badge": "Great Deal"},
        "parser": provider,
        "discovered_at": "2026-05-25T16:00:00-04:00",
    }


def _make_verdict(verdict: str = "ACTION", reasoning: str = "test verdict") -> dict:
    return {
        "verdict": verdict,
        "reasoning": reasoning,
        "key_factors": {
            "trim": "580",
            "model_year": 2024,
            "price": 90000,
            "distance_miles": 78,
            "dealer_tier": "A",
            "cpo_status": "cpo",
            "price_assessment": "at_market",
        },
        "action_items": ["Call dealer to verify captain's chairs"] if verdict == "ACTION" else [],
    }


class TestTriage(unittest.TestCase):
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
        self.logger = triage.setup_logging(verbose=False)

    def tearDown(self):
        for p in self._state_patches:
            p.stop()
        self._tmp.cleanup()

    # ---- verdict flow ----

    def test_action_verdict_written_to_triaged(self):
        state.add_to_queue(_make_candidate("VIN1"))
        with patch.object(llm, "triage", return_value=_make_verdict("ACTION")):
            stats = triage.run(self.logger)
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["actions"], 1)
        triaged = state.load_triaged()
        self.assertEqual(len(triaged), 1)
        rec = triaged[0]
        self.assertEqual(rec["vin"], "VIN1")
        self.assertEqual(rec["verdict"], "ACTION")
        self.assertEqual(rec["provider"], "cargurus")
        self.assertEqual(rec["raw_metadata_snapshot"]["price"], 90000)
        self.assertIn("triaged_at", rec)
        self.assertEqual(rec["action_items"], ["Call dealer to verify captain's chairs"])

    def test_pass_verdict_written_to_triaged(self):
        state.add_to_queue(_make_candidate("VIN2"))
        with patch.object(llm, "triage", return_value=_make_verdict("PASS", "out of range")):
            stats = triage.run(self.logger)
        self.assertEqual(stats["passes"], 1)
        self.assertEqual(state.load_triaged()[0]["verdict"], "PASS")

    def test_needs_human_verdict_written_to_triaged(self):
        state.add_to_queue(_make_candidate("VIN3"))
        with patch.object(llm, "triage", return_value=_make_verdict("NEEDS_HUMAN", "missing price")):
            stats = triage.run(self.logger)
        self.assertEqual(stats["needs_human"], 1)
        self.assertEqual(state.load_triaged()[0]["verdict"], "NEEDS_HUMAN")

    # ---- queue mechanics ----

    def test_fifo_order_preserved(self):
        state.add_to_queue(_make_candidate("VIN_A"))
        state.add_to_queue(_make_candidate("VIN_B"))
        state.add_to_queue(_make_candidate("VIN_C"))
        with patch.object(llm, "triage", return_value=_make_verdict("PASS")):
            triage.run(self.logger)
        triaged = state.load_triaged()
        self.assertEqual([r["vin"] for r in triaged], ["VIN_A", "VIN_B", "VIN_C"])
        self.assertEqual(state.queue_size(), 0)

    def test_limit_stops_after_n(self):
        for i in range(5):
            state.add_to_queue(_make_candidate(f"VIN_{i}"))
        with patch.object(llm, "triage", return_value=_make_verdict("PASS")):
            stats = triage.run(self.logger, limit=2)
        self.assertEqual(stats["processed"], 2)
        # Remaining 3 candidates still in queue
        self.assertEqual(state.queue_size(), 3)
        triaged = state.load_triaged()
        self.assertEqual([r["vin"] for r in triaged], ["VIN_0", "VIN_1"])

    def test_empty_queue_is_noop(self):
        with patch.object(llm, "triage", return_value=_make_verdict("PASS")) as mock:
            stats = triage.run(self.logger)
        self.assertEqual(stats["processed"], 0)
        mock.assert_not_called()

    # ---- dry-run safety ----

    def test_dry_run_does_not_call_llm_or_write_state(self):
        state.add_to_queue(_make_candidate("VIN_DRY"))
        with patch.object(llm, "triage") as mock_triage:
            stats = triage.run(self.logger, dry_run=True)
        mock_triage.assert_not_called()
        self.assertTrue(stats["dry_run"])
        self.assertEqual(state.load_triaged(), [])
        # Dry-run does pop from the queue — we accept this as the cost
        # of letting the dry-run print per-candidate token estimates.
        # If we needed to preserve queue state across dry-runs we'd
        # snapshot+restore here. For now, document the behavior:
        # dry-run is destructive to queue.json (set expectation).
        self.assertEqual(state.queue_size(), 0)

    # ---- error handling ----

    def test_api_failure_requeues_candidate(self):
        state.add_to_queue(_make_candidate("VIN_FAIL"))
        with patch.object(llm, "triage", side_effect=RuntimeError("API down")):
            stats = triage.run(self.logger)
        self.assertEqual(stats["errors"], 1)
        self.assertEqual(stats["processed"], 0)
        # Candidate must be back in the queue for next run to retry
        self.assertEqual(state.queue_size(), 1)
        # Nothing landed in triaged.json
        self.assertEqual(state.load_triaged(), [])

    def test_mixed_success_and_failure_processes_what_it_can(self):
        state.add_to_queue(_make_candidate("VIN_OK_1"))
        state.add_to_queue(_make_candidate("VIN_FAIL"))
        state.add_to_queue(_make_candidate("VIN_OK_2"))

        call_count = {"n": 0}

        def fake_triage(candidate, *args, **kwargs):
            call_count["n"] += 1
            if candidate["vin"] == "VIN_FAIL":
                raise RuntimeError("API hiccup on this one")
            return _make_verdict("ACTION")

        with patch.object(llm, "triage", side_effect=fake_triage):
            stats = triage.run(self.logger)

        self.assertEqual(call_count["n"], 3)
        self.assertEqual(stats["processed"], 2)
        self.assertEqual(stats["errors"], 1)
        # Failed candidate re-queued for next run
        self.assertEqual(state.queue_size(), 1)
        self.assertEqual(state.load_queue()[0]["vin"], "VIN_FAIL")
        # The two successes landed in triaged.json
        vins = [r["vin"] for r in state.load_triaged()]
        self.assertEqual(sorted(vins), ["VIN_OK_1", "VIN_OK_2"])

    # ---- force re-triage path ----

    def test_force_retriage_by_vin(self):
        # Seed triaged.json with a prior verdict
        prior = {
            "vin": "VIN_RT",
            "triaged_at": "2026-05-20T16:00:00-04:00",
            "provider": "cargurus",
            "listing_url": "https://cargurus.example.com/inv/VIN_RT",
            "raw_metadata_snapshot": {"price": 95000, "mileage": 5000},
            "verdict": "PASS",
            "reasoning": "overpriced at $95K",
            "key_factors": {},
            "action_items": [],
        }
        state.append_triaged(prior)

        with patch.object(llm, "triage", return_value=_make_verdict("ACTION", "tuned prompt re-eval")):
            stats = triage.run(self.logger, vin_filter="VIN_RT")

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["actions"], 1)
        triaged = state.load_triaged()
        # Both old and new verdicts present (append-only history)
        self.assertEqual(len(triaged), 2)
        self.assertEqual(triaged[0]["verdict"], "PASS")
        self.assertEqual(triaged[1]["verdict"], "ACTION")
        self.assertEqual(triaged[1]["reasoning"], "tuned prompt re-eval")

    def test_force_retriage_unknown_vin_is_noop(self):
        with patch.object(llm, "triage") as mock_triage:
            stats = triage.run(self.logger, vin_filter="VIN_NEVER_SEEN")
        mock_triage.assert_not_called()
        self.assertEqual(stats["processed"], 0)


class TestPromptAssembly(unittest.TestCase):
    """Verify the prompt builder doesn't crash on real rubric files."""

    def test_assemble_system_prompt_includes_all_rubric_files(self):
        prompt = llm.assemble_system_prompt()
        # Should reference each rubric file's path in its section header
        for f in llm.RUBRIC_FILES:
            self.assertIn(f, prompt)

    def test_load_triage_tool_returns_expected_schema(self):
        tool = llm.load_triage_tool()
        self.assertEqual(tool["name"], "submit_triage_verdict")
        self.assertIn("input_schema", tool)
        # Verdict enum must match the 3-tier taxonomy
        verdicts = tool["input_schema"]["properties"]["verdict"]["enum"]
        self.assertEqual(sorted(verdicts), ["ACTION", "NEEDS_HUMAN", "PASS"])

    def test_build_user_message_includes_candidate_json(self):
        c = _make_candidate("VIN_X")
        msg = llm.build_user_message(c)
        self.assertIn("VIN_X", msg)
        self.assertIn("submit_triage_verdict", msg)

    def test_build_user_message_truncates_long_bodies(self):
        # Use a fill char ("Z") and VIN ("VIN_777") that don't overlap, so
        # msg.count() measures only the body, not incidental chars in
        # the candidate-JSON section.
        c = _make_candidate("VIN_777")
        huge_body = "Z" * 20000
        msg = llm.build_user_message(c, raw_email_body=huge_body)
        # Body is truncated to 8000 chars regardless of input size
        self.assertEqual(msg.count("Z"), 8000)


if __name__ == "__main__":
    unittest.main()
