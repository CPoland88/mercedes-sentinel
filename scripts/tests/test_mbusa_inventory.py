"""Tests for scripts/mbusa_inventory.py.

Tests are fully offline. The parse-path tests load the scrubbed
fixture at scripts/tests/fixtures/mbusa_sample.json (one record
manually anonymized from the recon baseline); the fetch-path tests
inject a MagicMock httpx.Client that returns canned JSON payloads.

No live MBUSA calls anywhere in this suite.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from .. import mbusa_inventory
from ..mbusa_inventory import (
    MbusaCandidate,
    fetch_matching_inventory,
    parse_vehicle_record,
)


FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "mbusa_sample.json"
)


def _load_fixture() -> dict:
    """Load the scrubbed sample record as a fresh dict on every call.

    Returns a deep copy so tests can mutate without bleeding into siblings.
    """
    with FIXTURE_PATH.open() as f:
        return copy.deepcopy(json.load(f))


def _make_page(records, total_count, current_offset):
    """Build a MBUSA-shaped response payload for a single page."""
    return {
        "result": {
            "pagedVehicles": {
                "records": list(records),
                "paging": {
                    "totalCount": total_count,
                    "currentOffset": current_offset,
                    "currentCount": len(records),
                },
            }
        },
        "status": {"code": 200, "ok": True},
        "messages": [],
        "success": True,
    }


def _mock_response(status_code: int, body: dict | str):
    """Build a MagicMock that quacks like an httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    if isinstance(body, dict):
        response.json.return_value = body
        response.text = json.dumps(body)
    else:
        response.text = body
        response.json.side_effect = ValueError("not json")

    def raise_for_status():
        if status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{status_code}",
                request=MagicMock(),
                response=response,
            )

    response.raise_for_status.side_effect = raise_for_status
    return response


# ---------- parse_vehicle_record: happy path ----------


class TestParseVehicleRecordHappyPath(unittest.TestCase):
    """Parse the scrubbed fixture and assert every mapped field."""

    def setUp(self):
        self.record = _load_fixture()
        self.candidate = parse_vehicle_record(self.record)

    def test_returns_mbusa_candidate(self):
        self.assertIsInstance(self.candidate, MbusaCandidate)

    def test_identity_fields(self):
        self.assertEqual(self.candidate.vin, "4JGFF8FE0NB000001")
        self.assertEqual(self.candidate.year, 2024)
        self.assertEqual(self.candidate.model_id, "GLS580W4")
        self.assertEqual(self.candidate.class_id, "GLS")

    def test_year_coerced_to_int(self):
        # MBUSA ships year as a string; parser must coerce.
        self.assertIsInstance(self.candidate.year, int)

    def test_dealer_geography(self):
        self.assertEqual(
            self.candidate.dealer_name, "Sample Dealer of Sample City"
        )
        self.assertEqual(self.candidate.dealer_city, "Sample City")
        self.assertEqual(self.candidate.dealer_state, "NJ")
        self.assertEqual(self.candidate.dealer_zip, "08000")
        self.assertEqual(self.candidate.dealer_distance_mi, 125.0)

    def test_color_fields(self):
        self.assertEqual(self.candidate.exterior_meta_color, "BLU")
        self.assertEqual(
            self.candidate.paint_marketing, "Twilight Blue metallic"
        )

    def test_pricing(self):
        # msrp on the record is the real ask for CPO.
        self.assertEqual(self.candidate.ask_price, 87495.0)
        # inventoryPrice is reliably zero on CPO; retained as raw.
        self.assertEqual(self.candidate.inventory_price_raw, 0.0)

    def test_mileage(self):
        self.assertEqual(self.candidate.mileage, 13872.0)

    def test_cpo_flag(self):
        self.assertTrue(self.candidate.is_cpo)

    def test_option_list_populated(self):
        # The fixture's optionList carries the CONTEXT-relevant build
        # data — at minimum we should see entries flow through.
        self.assertGreater(len(self.candidate.option_list), 0)
        # Every entry is a non-empty string.
        for entry in self.candidate.option_list:
            self.assertIsInstance(entry, str)
            self.assertTrue(entry)

    def test_features_populated(self):
        self.assertGreater(len(self.candidate.features), 0)

    def test_raw_record_preserved(self):
        # Downstream debugging shouldn't have to re-fetch.
        self.assertEqual(self.candidate.raw_record["vin"], self.record["vin"])


# ---------- parse_vehicle_record: tolerance ----------


class TestParseVehicleRecordTolerance(unittest.TestCase):
    """Records vary in the wild. Parser must not raise on missing fields."""

    def test_missing_msrp_falls_back_to_dsrp(self):
        record = _load_fixture()
        record["msrp"] = 0.0
        record["usedVehicleAttributes"]["dsrp"] = 60000.0
        result = parse_vehicle_record(record)
        self.assertEqual(result.ask_price, 60000.0)

    def test_all_price_fields_zero(self):
        record = _load_fixture()
        record["msrp"] = 0.0
        record["usedVehicleAttributes"]["dsrp"] = 0.0
        record["usedVehicleAttributes"]["reservePrice"] = 0.0
        result = parse_vehicle_record(record)
        self.assertIsNone(result.ask_price)

    def test_empty_dealer_address(self):
        record = _load_fixture()
        record["dealer"]["address"] = []
        result = parse_vehicle_record(record)
        self.assertIsNone(result.dealer_city)
        self.assertIsNone(result.dealer_state)
        self.assertIsNone(result.dealer_zip)
        self.assertIsNone(result.dealer_distance_mi)
        # Dealer name still survives — it's on the dealer dict root.
        self.assertEqual(
            result.dealer_name, "Sample Dealer of Sample City"
        )

    def test_no_used_vehicle_attributes(self):
        record = _load_fixture()
        del record["usedVehicleAttributes"]
        result = parse_vehicle_record(record)
        # No mileage, no certified flag.
        self.assertIsNone(result.mileage)
        self.assertFalse(result.is_cpo)
        # Other fields still parse.
        self.assertEqual(result.vin, "4JGFF8FE0NB000001")

    def test_no_features_or_options(self):
        record = _load_fixture()
        record.pop("features", None)
        record.pop("includedFeatures", None)
        record["usedVehicleAttributes"].pop("optionList", None)
        result = parse_vehicle_record(record)
        self.assertEqual(result.features, [])
        self.assertEqual(result.included_features, [])
        self.assertEqual(result.option_list, [])

    def test_non_numeric_year(self):
        record = _load_fixture()
        record["year"] = "not-a-year"
        result = parse_vehicle_record(record)
        self.assertIsNone(result.year)

    def test_missing_vin_raises(self):
        record = _load_fixture()
        del record["vin"]
        with self.assertRaises(ValueError):
            parse_vehicle_record(record)


# ---------- parse_vehicle_record: CPO conjunction ----------


class TestParseVehicleRecordCpoFlag(unittest.TestCase):
    """is_cpo must require both type==PRE AND certified==True."""

    def test_pre_and_certified_true(self):
        record = _load_fixture()
        record["type"] = "PRE"
        record["usedVehicleAttributes"]["certified"] = True
        self.assertTrue(parse_vehicle_record(record).is_cpo)

    def test_pre_but_not_certified(self):
        record = _load_fixture()
        record["type"] = "PRE"
        record["usedVehicleAttributes"]["certified"] = False
        self.assertFalse(parse_vehicle_record(record).is_cpo)

    def test_new_type_with_certified_flag(self):
        # Belt-and-suspenders: a NEW-typed record (which shouldn't appear
        # under invType=cpo but might under cpo,pre or future calls)
        # must not flag CPO even if certified is somehow True.
        record = _load_fixture()
        record["type"] = "NEW"
        record["usedVehicleAttributes"]["certified"] = True
        self.assertFalse(parse_vehicle_record(record).is_cpo)


# ---------- fetch_matching_inventory: pagination ----------


class TestFetchMatchingInventorySinglePage(unittest.TestCase):
    """One page of results, totalCount == currentCount: one HTTP call."""

    def test_single_page(self):
        record = _load_fixture()
        payload = _make_page([record], total_count=1, current_offset=0)
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _mock_response(200, payload)

        result = fetch_matching_inventory(
            zip_code="22180",
            model_codes=["GLS450W4", "GLS580W4"],
            year_range=(2024, 2026),
            color_codes=["BLU", "GRN"],
            class_id="GLS",
            client=mock_client,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].vin, "4JGFF8FE0NB000001")
        self.assertEqual(mock_client.get.call_count, 1)


class TestFetchMatchingInventoryMultiPage(unittest.TestCase):
    """Two pages: 12 records then 8, totalCount 20. Two HTTP calls."""

    def test_two_pages(self):
        page_one_records = [
            dict(_load_fixture(), vin=f"4JGFF8FE0NB0001{i:02d}")
            for i in range(12)
        ]
        page_two_records = [
            dict(_load_fixture(), vin=f"4JGFF8FE0NB0002{i:02d}")
            for i in range(8)
        ]

        payloads = [
            _make_page(page_one_records, total_count=20, current_offset=0),
            _make_page(page_two_records, total_count=20, current_offset=12),
        ]
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = [
            _mock_response(200, p) for p in payloads
        ]

        # Patch the jitter so the test doesn't actually sleep.
        with patch.object(mbusa_inventory, "_jittered_sleep"):
            result = fetch_matching_inventory(
                zip_code="22180",
                model_codes=["GLS450W4", "GLS580W4"],
                year_range=(2024, 2026),
                color_codes=["BLU", "GRN"],
                class_id="GLS",
                client=mock_client,
            )

        self.assertEqual(len(result), 20)
        self.assertEqual(mock_client.get.call_count, 2)

        # Verify the start offsets advanced correctly across calls.
        first_url = mock_client.get.call_args_list[0].args[0]
        second_url = mock_client.get.call_args_list[1].args[0]
        self.assertIn("start=0", first_url)
        self.assertIn("start=12", second_url)


class TestFetchMatchingInventoryEmpty(unittest.TestCase):
    """Empty result set: one HTTP call, empty list."""

    def test_empty(self):
        payload = _make_page([], total_count=0, current_offset=0)
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _mock_response(200, payload)

        result = fetch_matching_inventory(
            zip_code="22180",
            model_codes=["GLS450W4"],
            year_range=(2024, 2026),
            color_codes=["BLU"],
            client=mock_client,
        )

        self.assertEqual(result, [])
        self.assertEqual(mock_client.get.call_count, 1)


# ---------- fetch_matching_inventory: query-string contract ----------


class TestFetchMatchingInventoryQueryString(unittest.TestCase):
    """Guard against accidentally regressing parameter names."""

    def setUp(self):
        payload = _make_page([], total_count=0, current_offset=0)
        self.mock_client = MagicMock(spec=httpx.Client)
        self.mock_client.get.return_value = _mock_response(200, payload)

        fetch_matching_inventory(
            zip_code="22180",
            model_codes=["GLS450W4", "GLS580W4"],
            year_range=(2024, 2026),
            color_codes=["BLU", "GRN"],
            class_id="GLS",
            inv_type="cpo",
            distance="ANY",
            client=self.mock_client,
        )
        self.url = self.mock_client.get.call_args.args[0]

    def test_uses_model_not_model_id(self):
        # The SPA uses ``model``, not ``modelId`` or ``modelDesignation``.
        self.assertIn("model=GLS450W4", self.url)
        self.assertNotIn("modelId=", self.url)
        self.assertNotIn("modelDesignation=", self.url)

    def test_uses_year_range_params(self):
        # ``minYear`` and ``maxYear`` — not ``year=2024,2025,2026``.
        self.assertIn("minYear=2024", self.url)
        self.assertIn("maxYear=2026", self.url)
        self.assertNotIn("year=", self.url)

    def test_uses_exterior_short_codes(self):
        # ``exterior`` accepts two-letter codes; not ``exteriorColor``.
        self.assertIn("exterior=BLU", self.url)
        self.assertNotIn("exteriorColor=", self.url)

    def test_class_id_present(self):
        self.assertIn("class=GLS", self.url)

    def test_inv_type_and_distance_present(self):
        self.assertIn("invType=cpo", self.url)
        self.assertIn("distance=ANY", self.url)

    def test_zip_present(self):
        self.assertIn("zip=22180", self.url)

    def test_sort_by_distance_asc(self):
        self.assertIn("sortBy=distance-asc", self.url)


class TestFetchMatchingInventoryOptionalClass(unittest.TestCase):
    """class_id is optional — omitted when not passed."""

    def test_omits_class_when_none(self):
        payload = _make_page([], total_count=0, current_offset=0)
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _mock_response(200, payload)

        fetch_matching_inventory(
            zip_code="22180",
            model_codes=["GLS450W4"],
            year_range=(2024, 2026),
            color_codes=["BLU"],
            client=mock_client,
        )

        url = mock_client.get.call_args.args[0]
        self.assertNotIn("class=", url)


# ---------- _get_with_retry ----------


class TestGetWithRetry(unittest.TestCase):
    """Retry behavior in isolation."""

    def test_200_returns_immediately(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _mock_response(200, {"ok": True})

        result = mbusa_inventory._get_with_retry(
            mock_client, "https://example.invalid/x"
        )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(mock_client.get.call_count, 1)

    def test_500_retries_once_then_succeeds(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = [
            _mock_response(500, "server error"),
            _mock_response(200, {"recovered": True}),
        ]

        with patch.object(mbusa_inventory.time, "sleep"):
            result = mbusa_inventory._get_with_retry(
                mock_client, "https://example.invalid/x"
            )

        self.assertEqual(result, {"recovered": True})
        self.assertEqual(mock_client.get.call_count, 2)

    def test_500_twice_raises(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = [
            _mock_response(500, "server error"),
            _mock_response(503, "still down"),
        ]

        with patch.object(mbusa_inventory.time, "sleep"):
            with self.assertRaises(httpx.HTTPStatusError):
                mbusa_inventory._get_with_retry(
                    mock_client, "https://example.invalid/x"
                )

        self.assertEqual(mock_client.get.call_count, 2)

    def test_400_fails_fast_no_retry(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _mock_response(400, "bad query")

        with self.assertRaises(httpx.HTTPStatusError):
            mbusa_inventory._get_with_retry(
                mock_client, "https://example.invalid/x"
            )

        self.assertEqual(mock_client.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
