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

    def test_mark_seen_creates_record(self):
        state.mark_seen("4JGFF8FE2SB431338", "cargurus", "https://example.com/inv/x")
        self.assertTrue(state.is_seen("4JGFF8FE2SB431338"))
        seen = state.load_seen_vins()
        self.assertEqual(seen["4JGFF8FE2SB431338"]["providers"], ["cargurus"])
        self.assertEqual(
            seen["4JGFF8FE2SB431338"]["listing_urls"],
            ["https://example.com/inv/x"],
        )
        self.assertIn("first_seen", seen["4JGFF8FE2SB431338"])
        self.assertIn("last_seen", seen["4JGFF8FE2SB431338"])

    def test_mark_seen_is_idempotent_and_accumulates(self):
        state.mark_seen("4JGFF8FE2SB431338", "cargurus", "https://a.example.com/x")
        state.mark_seen("4JGFF8FE2SB431338", "cargurus", "https://a.example.com/x")
        state.mark_seen("4JGFF8FE2SB431338", "autotrader", "https://b.example.com/x")
        seen = state.load_seen_vins()
        # Providers dedup
        self.assertEqual(
            sorted(seen["4JGFF8FE2SB431338"]["providers"]),
            ["autotrader", "cargurus"],
        )
        # URLs dedup
        self.assertEqual(
            sorted(seen["4JGFF8FE2SB431338"]["listing_urls"]),
            ["https://a.example.com/x", "https://b.example.com/x"],
        )

    def test_mark_seen_handles_missing_url(self):
        state.mark_seen("4JGFF8FE2SB431338", "unknown", None)
        seen = state.load_seen_vins()
        self.assertEqual(seen["4JGFF8FE2SB431338"]["listing_urls"], [])

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

    # ---- file format sanity ----

    def test_seen_vins_file_is_valid_json(self):
        state.mark_seen("4JGFF8FE2SB431338", "cargurus", "https://example.com/x")
        raw = state.SEEN_VINS_PATH.read_text()
        loaded = json.loads(raw)
        self.assertIn("4JGFF8FE2SB431338", loaded)


if __name__ == "__main__":
    unittest.main()
