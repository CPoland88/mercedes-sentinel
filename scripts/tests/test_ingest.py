"""Tests for scripts/ingest.py — specifically the MBUSA polling path
added in commit 4 of the Architecture B pivot.

Tests inject a MagicMock for ``mbusa_inventory.fetch_matching_inventory``
so no live MBUSA call ever fires. State paths are redirected into a
per-test tempdir using the same pattern as test_state.py — nothing
under data/ is touched.

Tests for the email path live in test_parsers.py (parser unit tests)
and the existing test_state.py (state interactions). Commit 5 will
exercise the EmailSignal refactor at the parser level.
"""
from __future__ import annotations

import json
import logging
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from .. import ingest, state
from ..mbusa_inventory import MbusaCandidate


def _mc(
    vin: str = "4JGFF8FE0NB000001",
    *,
    year: int = 2024,
    model_id: str = "GLS580W4",
    model_name: str = "GLS 580 4MATIC SUV",
    class_id: str = "GLS",
    dealer_name: str = "Sample Dealer",
    dealer_city: str = "Sample City",
    dealer_state: str = "VA",
    dealer_zip: str = "22180",
    dealer_distance_mi: float = 50.0,
    exterior_meta_color: str = "BLU",
    paint_marketing: str = "Twilight Blue metallic",
    ask_price: float = 87000.0,
    mileage: float = 15000.0,
    is_cpo: bool = True,
    option_list=None,
    features=None,
    stock_id: str = "STOCK1",
) -> MbusaCandidate:
    """Build an MbusaCandidate with sensible defaults; override any field
    by keyword. Used to keep test setup short and intent-focused."""
    return MbusaCandidate(
        vin=vin,
        year=year,
        model_id=model_id,
        model_name=model_name,
        class_id=class_id,
        dealer_name=dealer_name,
        dealer_city=dealer_city,
        dealer_state=dealer_state,
        dealer_zip=dealer_zip,
        dealer_distance_mi=dealer_distance_mi,
        exterior_meta_color=exterior_meta_color,
        paint_marketing=paint_marketing,
        ask_price=ask_price,
        inventory_price_raw=0.0,
        mileage=mileage,
        is_cpo=is_cpo,
        option_list=list(option_list or ["7-seat cabin configuration"]),
        features=list(features or ["Wireless Apple CarPlay"]),
        included_features=[],
        stock_id=stock_id,
    )


def _silent_logger() -> logging.Logger:
    logger = logging.getLogger("test_ingest")
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


# ---------- _mbusa_candidate_to_dict ----------


class TestMbusaCandidateToDict(unittest.TestCase):

    def test_top_level_fields(self):
        d = ingest._mbusa_candidate_to_dict(_mc())
        self.assertEqual(d["vin"], "4JGFF8FE0NB000001")
        self.assertEqual(d["provider"], "mbusa")
        self.assertEqual(d["source"], "mbusa")
        self.assertIsNone(d["listing_url"])

    def test_raw_metadata_carries_context_fields(self):
        d = ingest._mbusa_candidate_to_dict(_mc())
        rm = d["raw_metadata"]
        self.assertEqual(rm["price"], 87000.0)
        self.assertEqual(rm["mileage"], 15000.0)
        self.assertEqual(rm["year"], 2024)
        self.assertEqual(rm["model_name"], "GLS 580 4MATIC SUV")
        self.assertEqual(rm["paint_marketing"], "Twilight Blue metallic")
        self.assertEqual(rm["exterior_meta_color"], "BLU")
        self.assertEqual(rm["dealer_name"], "Sample Dealer")
        self.assertEqual(rm["dealer_city"], "Sample City")
        self.assertEqual(rm["dealer_state"], "VA")
        self.assertEqual(rm["dealer_distance_mi"], 50.0)
        self.assertTrue(rm["is_cpo"])
        self.assertEqual(rm["option_list"], ["7-seat cabin configuration"])

    def test_option_list_is_a_copy_not_a_reference(self):
        # Mutating the candidate's options after mapping must not
        # mutate the queued dict.
        original = ["7-seat cabin configuration", "Burmester 3D"]
        c = _mc(option_list=original)
        d = ingest._mbusa_candidate_to_dict(c)
        original.append("MUTATION")
        self.assertNotIn("MUTATION", d["raw_metadata"]["option_list"])


# ---------- _should_keep_mbusa ----------


class TestShouldKeepMbusa(unittest.TestCase):

    def test_at_boundary_all_kept(self):
        # Exactly at the hard caps — kept.
        keep, _ = ingest._should_keep_mbusa(
            _mc(year=2024, mileage=40000.0, dealer_distance_mi=250.0)
        )
        self.assertTrue(keep)

    def test_year_just_below_dropped(self):
        keep, reason = ingest._should_keep_mbusa(_mc(year=2023))
        self.assertFalse(keep)
        self.assertIn("year", reason)

    def test_mileage_just_over_dropped(self):
        keep, reason = ingest._should_keep_mbusa(_mc(mileage=40001.0))
        self.assertFalse(keep)
        self.assertIn("mileage", reason)

    def test_distance_just_over_dropped(self):
        keep, reason = ingest._should_keep_mbusa(_mc(dealer_distance_mi=251.0))
        self.assertFalse(keep)
        self.assertIn("distance", reason)

    def test_none_year_dropped(self):
        keep, _ = ingest._should_keep_mbusa(_mc(year=None))
        self.assertFalse(keep)

    def test_none_mileage_dropped(self):
        keep, _ = ingest._should_keep_mbusa(_mc(mileage=None))
        self.assertFalse(keep)

    def test_none_distance_dropped(self):
        # Defensive: a candidate with no resolvable distance is
        # treated as out-of-bounds rather than queued.
        keep, _ = ingest._should_keep_mbusa(_mc(dealer_distance_mi=None))
        self.assertFalse(keep)


# ---------- run_mbusa_poll ----------


class TestRunMbusaPollBase(unittest.TestCase):
    """Shared setup: tempdir for state, mocked fetch."""

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

        # Patch the function on the ingest module's namespace, which is
        # where it's looked up at call time (after `from . import
        # mbusa_inventory`). Patching the module-level symbol elsewhere
        # wouldn't catch the ingest-side reference.
        self._fetch_patch = patch.object(
            ingest.mbusa_inventory, "fetch_matching_inventory"
        )
        self.mock_fetch = self._fetch_patch.start()

        self.logger = _silent_logger()

    def tearDown(self):
        self._fetch_patch.stop()
        for p in self._state_patches:
            p.stop()
        self._tmp.cleanup()


class TestRunMbusaPollCallSignature(TestRunMbusaPollBase):
    """Guard the call into mbusa_inventory against drift."""

    def test_passes_context_md_params(self):
        self.mock_fetch.return_value = []
        stats = {}
        ingest.run_mbusa_poll(self.logger, write_state=True, stats=stats)

        self.assertEqual(self.mock_fetch.call_count, 1)
        kwargs = self.mock_fetch.call_args.kwargs
        self.assertEqual(kwargs["zip_code"], "22180")
        self.assertEqual(tuple(kwargs["model_codes"]), ("GLS450W4", "GLS580W4"))
        self.assertEqual(tuple(kwargs["color_codes"]), ("BLU", "GRN"))
        self.assertEqual(kwargs["class_id"], "GLS")
        self.assertEqual(kwargs["inv_type"], "cpo")
        self.assertEqual(kwargs["distance"], "ANY")
        # min year is CONTEXT.md floor; max year is clamped at the
        # current calendar year because MBUSA rejects future-year
        # queries (see ingest.py comment for the diagnostic story).
        min_year, max_year = kwargs["year_range"]
        self.assertEqual(min_year, 2024)
        self.assertEqual(max_year, datetime.now().year)


class TestRunMbusaPollFiltering(TestRunMbusaPollBase):

    def test_kept_candidates_queue(self):
        keep = _mc(vin="VIN1KEEP", dealer_distance_mi=100.0, mileage=10000.0)
        self.mock_fetch.return_value = [keep]

        stats = {
            "new_candidates": 0,
            "duplicates": 0,
        }
        ingest.run_mbusa_poll(self.logger, write_state=True, stats=stats)

        queue = state.load_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["vin"], "VIN1KEEP")
        self.assertEqual(queue[0]["source"], "mbusa")
        self.assertIn("discovered_at", queue[0])
        self.assertEqual(stats["new_candidates"], 1)
        self.assertEqual(stats["mbusa_records_returned"], 1)
        self.assertEqual(stats["mbusa_kept_after_filter"], 1)
        self.assertEqual(stats["mbusa_filtered_out"], 0)

    def test_filtered_candidates_do_not_queue(self):
        candidates = [
            _mc(vin="VINNEAR", dealer_distance_mi=50.0),
            _mc(vin="VINFAR", dealer_distance_mi=400.0),
            _mc(vin="VINMILES", mileage=80000.0),
            _mc(vin="VINOLD", year=2022),
        ]
        self.mock_fetch.return_value = candidates

        stats = {"new_candidates": 0, "duplicates": 0}
        ingest.run_mbusa_poll(self.logger, write_state=True, stats=stats)

        queue = state.load_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["vin"], "VINNEAR")
        self.assertEqual(stats["mbusa_records_returned"], 4)
        self.assertEqual(stats["mbusa_kept_after_filter"], 1)
        self.assertEqual(stats["mbusa_filtered_out"], 3)

    def test_dry_run_does_not_write_state(self):
        self.mock_fetch.return_value = [_mc(vin="VINDRY")]
        stats = {"new_candidates": 0, "duplicates": 0}

        ingest.run_mbusa_poll(self.logger, write_state=False, stats=stats)

        # Stats still update so the operator can see what would have queued.
        self.assertEqual(stats["mbusa_kept_after_filter"], 1)
        self.assertEqual(stats["new_candidates"], 1)
        # But no state writes occurred.
        self.assertEqual(state.load_queue(), [])
        self.assertFalse(state.is_seen("VINDRY"))


class TestRunMbusaPollDedup(TestRunMbusaPollBase):

    def test_second_identical_run_deduplicates(self):
        self.mock_fetch.return_value = [_mc(vin="VIN1")]
        stats = {"new_candidates": 0, "duplicates": 0}

        ingest.run_mbusa_poll(self.logger, write_state=True, stats=stats)
        self.assertEqual(stats["new_candidates"], 1)
        self.assertEqual(stats["duplicates"], 0)

        # Drain the queue so a "new candidate" doesn't just mean
        # "queue grew" but is actually about the dedup gate.
        state.pop_from_queue()

        # Second run with identical fetcher output → dedup gate trips.
        stats2 = {"new_candidates": 0, "duplicates": 0}
        ingest.run_mbusa_poll(self.logger, write_state=True, stats=stats2)
        self.assertEqual(stats2["new_candidates"], 0)
        self.assertEqual(stats2["duplicates"], 1)


# ---------- run_live --skip-mbusa wiring ----------


class TestRunLiveSkipMbusa(unittest.TestCase):
    """run_live should bypass MBUSA when skip_mbusa=True, even with
    a healthy fetcher available."""

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
        self._fetch_patch = patch.object(
            ingest.mbusa_inventory, "fetch_matching_inventory"
        )
        self.mock_fetch = self._fetch_patch.start()

        # Mock mail.from_env so run_live's email loop is a no-op for these tests.
        self._mail_patch = patch.object(ingest.mail, "from_env")
        mock_from_env = self._mail_patch.start()
        mock_poller = MagicMock()
        mock_poller.fetch_unread.return_value = []
        mock_poller.label = "test-label"
        mock_from_env.return_value.__enter__.return_value = mock_poller
        mock_from_env.return_value.__exit__.return_value = False

        self.logger = _silent_logger()

    def tearDown(self):
        self._mail_patch.stop()
        self._fetch_patch.stop()
        for p in self._state_patches:
            p.stop()
        self._tmp.cleanup()

    def test_skip_mbusa_true_does_not_call_fetch(self):
        stats = ingest.run_live(self.logger, dry_run=False, skip_mbusa=True)
        self.assertEqual(self.mock_fetch.call_count, 0)
        self.assertTrue(stats["mbusa_skipped"])

    def test_skip_mbusa_false_calls_fetch(self):
        self.mock_fetch.return_value = []
        stats = ingest.run_live(self.logger, dry_run=False, skip_mbusa=False)
        self.assertEqual(self.mock_fetch.call_count, 1)
        self.assertFalse(stats["mbusa_skipped"])


if __name__ == "__main__":
    unittest.main()
