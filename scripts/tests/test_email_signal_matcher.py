"""Tests for scripts/email_signal_matcher.

Pure-function tests; no IO, no state, no fixtures. Each test builds
the minimal signal + candidate shapes it needs inline.
"""
from __future__ import annotations

import unittest

from ..email_signal_matcher import (
    MATCH_MILEAGE_TOLERANCE_MI,
    MATCH_PRICE_TOLERANCE_USD,
    _extract_trim_from_model_id,
    match_email_signal,
)


def _signal(
    *,
    year: int = 2024,
    trim_number: str = "580",
    mileage: float = 13872,
    price: float = 87495,
    price_drop_delta: float = 1245,
) -> dict:
    return {
        "provider": "cars_com",
        "source": "email_signal",
        "cars_com_uuid": "test-uuid",
        "listing_url": "https://www.cars.com/vehicledetail/test-uuid",
        "raw_metadata": {
            "year": year,
            "trim_number": trim_number,
            "mileage": mileage,
            "price": price,
            "price_drop_delta": price_drop_delta,
        },
    }


def _candidate(
    *,
    vin: str = "4JGFF8FE0NB000001",
    year: int = 2024,
    model_id: str = "GLS580W4",
    mileage: float = 13872,
    price: float = 87495,
) -> dict:
    return {
        "vin": vin,
        "provider": "mbusa",
        "source": "mbusa",
        "listing_url": None,
        "raw_metadata": {
            "year": year,
            "model_id": model_id,
            "mileage": mileage,
            "price": price,
        },
    }


# ---------- _extract_trim_from_model_id ----------


class TestExtractTrimFromModelId(unittest.TestCase):

    def test_gls_580(self):
        self.assertEqual(_extract_trim_from_model_id("GLS580W4"), "580")

    def test_gls_450(self):
        self.assertEqual(_extract_trim_from_model_id("GLS450W4"), "450")

    def test_none_input(self):
        self.assertIsNone(_extract_trim_from_model_id(None))

    def test_empty_input(self):
        self.assertIsNone(_extract_trim_from_model_id(""))

    def test_unparseable_input(self):
        self.assertIsNone(_extract_trim_from_model_id("WeirdModelName"))


# ---------- match_email_signal: happy path ----------


class TestMatchEmailSignalHappyPath(unittest.TestCase):

    def test_exact_match_returns_vin(self):
        result = match_email_signal(_signal(), [_candidate()])
        self.assertTrue(result.matched)
        self.assertEqual(result.matched_vin, "4JGFF8FE0NB000001")
        self.assertEqual(result.score, 0.0)

    def test_match_returns_full_candidate_dict(self):
        cand = _candidate()
        result = match_email_signal(_signal(), [cand])
        self.assertIs(result.matched_candidate, cand)


# ---------- match_email_signal: tolerance boundaries ----------


class TestMatchEmailSignalTolerances(unittest.TestCase):

    def test_mileage_delta_at_boundary_matches(self):
        # Signal mileage 13,872, candidate 14,372 — exactly +500 delta.
        signal = _signal(mileage=13872)
        cand = _candidate(mileage=14372)
        result = match_email_signal(signal, [cand])
        self.assertTrue(result.matched)

    def test_mileage_delta_just_over_no_match(self):
        signal = _signal(mileage=13872)
        cand = _candidate(mileage=14373)  # +501 delta
        result = match_email_signal(signal, [cand])
        self.assertFalse(result.matched)
        self.assertIn("tolerance", result.reason_no_match)

    def test_price_delta_at_boundary_matches(self):
        signal = _signal(price=87495)
        cand = _candidate(price=89495)  # exactly +$2,000 delta
        result = match_email_signal(signal, [cand])
        self.assertTrue(result.matched)

    def test_price_delta_just_over_no_match(self):
        signal = _signal(price=87495)
        cand = _candidate(price=89496)  # +$2,001 delta
        result = match_email_signal(signal, [cand])
        self.assertFalse(result.matched)

    def test_negative_mileage_delta_works_too(self):
        # Cars.com sometimes shows mileage AHEAD of MBUSA (e.g., when
        # cars.com refreshed more recently). The tolerance is absolute.
        signal = _signal(mileage=14000)
        cand = _candidate(mileage=13600)  # signal is +400 ahead
        result = match_email_signal(signal, [cand])
        self.assertTrue(result.matched)

    def test_normalized_score_increases_with_delta(self):
        # Score is |miles_delta|/500 + |price_delta|/2000. A candidate
        # with 250 miles delta and $1,000 price delta should score
        # 0.5 + 0.5 = 1.0.
        signal = _signal(mileage=13872, price=87495)
        cand = _candidate(mileage=14122, price=88495)
        result = match_email_signal(signal, [cand])
        self.assertTrue(result.matched)
        self.assertAlmostEqual(result.score, 1.0, places=3)


# ---------- match_email_signal: hard mismatches ----------


class TestMatchEmailSignalHardMismatches(unittest.TestCase):

    def test_year_mismatch_no_match(self):
        result = match_email_signal(
            _signal(year=2024),
            [_candidate(year=2025)],
        )
        self.assertFalse(result.matched)

    def test_trim_mismatch_no_match(self):
        # 580 signal against a 450 candidate. CONTEXT.md treats them
        # as different spec tiers — never collapse.
        result = match_email_signal(
            _signal(trim_number="580"),
            [_candidate(model_id="GLS450W4")],
        )
        self.assertFalse(result.matched)

    def test_empty_candidates_no_match(self):
        result = match_email_signal(_signal(), [])
        self.assertFalse(result.matched)
        self.assertIn("tolerance", result.reason_no_match)


# ---------- match_email_signal: tie-break ----------


class TestMatchEmailSignalTieBreak(unittest.TestCase):

    def test_picks_smallest_normalized_distance(self):
        signal = _signal(mileage=13872, price=87495)
        # Two candidates, both within tolerance. The closer one wins.
        far_candidate = _candidate(
            vin="VINFAR", mileage=14372, price=89495,
        )  # +500 mi, +$2000 → score 2.0
        near_candidate = _candidate(
            vin="VINNEAR", mileage=13900, price=87500,
        )  # +28 mi, +$5 → score ~0.058
        result = match_email_signal(
            signal, [far_candidate, near_candidate]
        )
        self.assertEqual(result.matched_vin, "VINNEAR")

    def test_picks_smallest_normalized_distance_regardless_of_order(self):
        signal = _signal(mileage=13872, price=87495)
        near_candidate = _candidate(
            vin="VINNEAR", mileage=13900, price=87500,
        )
        far_candidate = _candidate(
            vin="VINFAR", mileage=14372, price=89495,
        )
        # Order reversed — same result.
        result = match_email_signal(
            signal, [near_candidate, far_candidate]
        )
        self.assertEqual(result.matched_vin, "VINNEAR")


# ---------- match_email_signal: fail-closed on missing fields ----------


class TestMatchEmailSignalFailClosed(unittest.TestCase):

    def test_signal_missing_mileage_no_match(self):
        signal = _signal()
        del signal["raw_metadata"]["mileage"]
        result = match_email_signal(signal, [_candidate()])
        self.assertFalse(result.matched)
        self.assertIn("mileage or price", result.reason_no_match)

    def test_signal_missing_price_no_match(self):
        signal = _signal()
        del signal["raw_metadata"]["price"]
        result = match_email_signal(signal, [_candidate()])
        self.assertFalse(result.matched)
        self.assertIn("mileage or price", result.reason_no_match)

    def test_signal_missing_year_no_match(self):
        signal = _signal()
        del signal["raw_metadata"]["year"]
        result = match_email_signal(signal, [_candidate()])
        self.assertFalse(result.matched)
        self.assertIn("year or trim", result.reason_no_match)

    def test_signal_missing_trim_no_match(self):
        signal = _signal()
        del signal["raw_metadata"]["trim_number"]
        result = match_email_signal(signal, [_candidate()])
        self.assertFalse(result.matched)

    def test_candidate_missing_mileage_skipped(self):
        cand = _candidate()
        del cand["raw_metadata"]["mileage"]
        result = match_email_signal(_signal(), [cand])
        # The single candidate is skipped silently; overall: no match.
        self.assertFalse(result.matched)

    def test_candidate_missing_price_skipped(self):
        cand = _candidate()
        del cand["raw_metadata"]["price"]
        result = match_email_signal(_signal(), [cand])
        self.assertFalse(result.matched)

    def test_candidate_missing_model_id_skipped(self):
        cand = _candidate()
        del cand["raw_metadata"]["model_id"]
        result = match_email_signal(_signal(), [cand])
        self.assertFalse(result.matched)


# ---------- module-level constants ----------


class TestModuleConstants(unittest.TestCase):

    def test_tolerances_are_finite_positive(self):
        self.assertGreater(MATCH_MILEAGE_TOLERANCE_MI, 0)
        self.assertGreater(MATCH_PRICE_TOLERANCE_USD, 0)


if __name__ == "__main__":
    unittest.main()
