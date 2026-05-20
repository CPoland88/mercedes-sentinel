"""Tests for the C2 re-triage gate (state.should_enqueue).

The dedup logic determines whether an incoming candidate from ingest
should land in the triage queue. It must:

  1. Enqueue any VIN we've never seen.
  2. Enqueue when this is a new provider for a known VIN
     (different platforms often surface different metadata, so a
     CarGurus-known VIN appearing on Cars.com is worth a fresh look).
  3. Enqueue when the (vin, provider) pair is known but the metadata
     has changed since last time (this is the price-drop re-triage
     case — the primary reason this gate exists).
  4. Skip when the (vin, provider, metadata) tuple is identical to
     what we've already ingested — the common case for daily polling
     against a stable label.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .. import state


class TestShouldEnqueue(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_dir = Path(self._tmp.name)
        self._patches = [
            patch.object(state, "DATA_DIR", self._tmp_dir),
            patch.object(state, "SEEN_VINS_PATH", self._tmp_dir / "seen-vins.json"),
            patch.object(state, "QUEUE_PATH", self._tmp_dir / "queue.json"),
            patch.object(state, "TRIAGED_PATH", self._tmp_dir / "triaged.json"),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def test_unseen_vin_enqueues(self):
        self.assertTrue(
            state.should_enqueue("VIN", "cargurus", {"price": 90000})
        )

    def test_new_provider_for_known_vin_enqueues(self):
        # Seen on CarGurus first
        state.mark_seen("VIN", "cargurus", "https://cargurus.com/x", {"price": 90000})
        # Now appears on Cars.com — different provider, should re-triage
        self.assertTrue(
            state.should_enqueue("VIN", "cars_com", {"price": 90000})
        )

    def test_identical_metadata_skips(self):
        state.mark_seen("VIN", "cargurus", "https://cargurus.com/x", {"price": 90000, "mileage": 5000})
        # Daily re-poll surfaces the same alert — metadata unchanged
        self.assertFalse(
            state.should_enqueue("VIN", "cargurus", {"price": 90000, "mileage": 5000})
        )

    def test_changed_price_enqueues(self):
        state.mark_seen("VIN", "cargurus", "https://cargurus.com/x", {"price": 95000, "mileage": 5000})
        # Price drop alert — must re-triage
        self.assertTrue(
            state.should_enqueue("VIN", "cargurus", {"price": 89000, "mileage": 5000})
        )

    def test_changed_mileage_enqueues(self):
        state.mark_seen("VIN", "cargurus", "https://cargurus.com/x", {"price": 90000, "mileage": 5000})
        # Mileage corrected on the dealer's side
        self.assertTrue(
            state.should_enqueue("VIN", "cargurus", {"price": 90000, "mileage": 5200})
        )

    def test_changed_badge_enqueues(self):
        state.mark_seen("VIN", "cargurus", "https://cargurus.com/x", {"price": 90000, "deal_badge": "Fair Deal"})
        # Badge upgrade — same VIN, same price, but now Great Deal
        self.assertTrue(
            state.should_enqueue("VIN", "cargurus", {"price": 90000, "deal_badge": "Great Deal"})
        )

    def test_empty_metadata_both_sides_skips(self):
        # Provider whose parser extracts no metadata (e.g., AutoTrader v1 stub
        # when an alert has no price block) shouldn't re-trigger on every poll.
        state.mark_seen("VIN", "autotrader", "https://autotrader.com/x", {})
        self.assertFalse(state.should_enqueue("VIN", "autotrader", {}))

    def test_none_metadata_treated_as_empty(self):
        state.mark_seen("VIN", "autotrader", "https://autotrader.com/x", None)
        # None on the incoming side should compare equal to the stored empty dict
        self.assertFalse(state.should_enqueue("VIN", "autotrader", None))


if __name__ == "__main__":
    unittest.main()
