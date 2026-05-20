"""Tests for scripts/state.py.

State paths are redirected into a per-test tempdir so the tests don't
touch the real `data/` directory.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .. import state


class TestState(unittest.TestCase):
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

    # ---- seen-vins ----

    def test_load_seen_vins_returns_empty_dict_when_missing(self):
        self.assertEqual(state.load_seen_vins(), {})
        self.assertFalse(state.is_seen("4JGFF8FE2SB431338"))

    def test_mark_seen_creates_record_with_per_provider_block(self):
        state.mark_seen(
            "4JGFF8FE2SB431338",
            "cargurus",
            "https://example.com/inv/x",
            {"price": 95000, "mileage": 5000},
        )
        self.assertTrue(state.is_seen("4JGFF8FE2SB431338"))
        seen = state.load_seen_vins()
        record = seen["4JGFF8FE2SB431338"]
        self.assertIn("first_seen", record)
        self.assertIn("last_seen", record)
        self.assertIn("cargurus", record["per_provider"])
        self.assertEqual(
            record["per_provider"]["cargurus"]["last_metadata"],
            {"price": 95000, "mileage": 5000},
        )
        self.assertEqual(
            record["per_provider"]["cargurus"]["listing_urls"],
            ["https://example.com/inv/x"],
        )

    def test_mark_seen_accumulates_across_providers(self):
        state.mark_seen("VIN", "cargurus", "https://a.example.com/x", {"price": 90000})
        state.mark_seen("VIN", "autotrader", "https://b.example.com/x", {"price": 90500})
        record = state.load_seen_vins()["VIN"]
        self.assertEqual(set(record["per_provider"].keys()), {"cargurus", "autotrader"})
        self.assertEqual(record["per_provider"]["cargurus"]["last_metadata"]["price"], 90000)
        self.assertEqual(record["per_provider"]["autotrader"]["last_metadata"]["price"], 90500)

    def test_mark_seen_updates_metadata_on_repeat_call(self):
        state.mark_seen("VIN", "cargurus", "https://a.example.com/x", {"price": 95000})
        state.mark_seen("VIN", "cargurus", "https://a.example.com/x", {"price": 89000})
        record = state.load_seen_vins()["VIN"]
        # Metadata replaced (not merged) — last write wins
        self.assertEqual(record["per_provider"]["cargurus"]["last_metadata"]["price"], 89000)
        # URL deduped (still one entry)
        self.assertEqual(len(record["per_provider"]["cargurus"]["listing_urls"]), 1)

    def test_mark_seen_dedups_urls_within_provider(self):
        state.mark_seen("VIN", "cargurus", "https://a.example.com/x", {})
        state.mark_seen("VIN", "cargurus", "https://a.example.com/x", {})
        state.mark_seen("VIN", "cargurus", "https://b.example.com/y", {})
        urls = state.load_seen_vins()["VIN"]["per_provider"]["cargurus"]["listing_urls"]
        self.assertEqual(sorted(urls), ["https://a.example.com/x", "https://b.example.com/y"])

    def test_mark_seen_handles_missing_url(self):
        state.mark_seen("VIN", "unknown", None, {})
        urls = state.load_seen_vins()["VIN"]["per_provider"]["unknown"]["listing_urls"]
        self.assertEqual(urls, [])

    def test_get_last_metadata_returns_none_when_unseen(self):
        self.assertIsNone(state.get_last_metadata("VIN", "cargurus"))
        state.mark_seen("VIN", "cargurus", None, {"price": 90000})
        # Same VIN, different provider — still None
        self.assertIsNone(state.get_last_metadata("VIN", "autotrader"))
        # Same VIN+provider — returns the snapshot
        self.assertEqual(state.get_last_metadata("VIN", "cargurus"), {"price": 90000})

    # ---- queue ----

    def test_queue_empty(self):
        self.assertEqual(state.load_queue(), [])
        self.assertIsNone(state.pop_from_queue())
        self.assertEqual(state.queue_size(), 0)

    def test_queue_fifo(self):
        state.add_to_queue({"vin": "A", "listing_url": "https://a.example.com"})
        state.add_to_queue({"vin": "B", "listing_url": "https://b.example.com"})
        state.add_to_queue({"vin": "C", "listing_url": "https://c.example.com"})
        self.assertEqual(state.queue_size(), 3)
        self.assertEqual(state.pop_from_queue()["vin"], "A")
        self.assertEqual(state.pop_from_queue()["vin"], "B")
        self.assertEqual(state.pop_from_queue()["vin"], "C")
        self.assertIsNone(state.pop_from_queue())

    # ---- triaged ----

    def test_append_triaged(self):
        self.assertEqual(state.load_triaged(), [])
        state.append_triaged({"vin": "A", "verdict": "PASS"})
        state.append_triaged({"vin": "B", "verdict": "ACTION"})
        triaged = state.load_triaged()
        self.assertEqual(len(triaged), 2)
        self.assertEqual(triaged[0]["vin"], "A")
        self.assertEqual(triaged[1]["verdict"], "ACTION")

    def test_latest_triage_for_vin_returns_most_recent(self):
        self.assertIsNone(state.latest_triage_for_vin("A"))
        state.append_triaged({"vin": "A", "verdict": "PASS", "triaged_at": "2026-01-01T00:00:00"})
        state.append_triaged({"vin": "B", "verdict": "ACTION", "triaged_at": "2026-01-02T00:00:00"})
        state.append_triaged({"vin": "A", "verdict": "ACTION", "triaged_at": "2026-01-03T00:00:00"})
        latest = state.latest_triage_for_vin("A")
        self.assertEqual(latest["verdict"], "ACTION")
        self.assertEqual(latest["triaged_at"], "2026-01-03T00:00:00")

    # ---- file format sanity ----

    def test_seen_vins_file_is_valid_json(self):
        state.mark_seen("4JGFF8FE2SB431338", "cargurus", "https://example.com/x", {"price": 90000})
        raw = state.SEEN_VINS_PATH.read_text()
        loaded = json.loads(raw)
        self.assertIn("4JGFF8FE2SB431338", loaded)


if __name__ == "__main__":
    unittest.main()
