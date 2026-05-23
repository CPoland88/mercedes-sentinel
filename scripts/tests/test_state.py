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

    def test_load_seen_vins_returns_versioned_empty_state_when_missing(self):
        # Post-v2 contract: load always returns at least the schema marker.
        # is_seen still correctly reports False for any VIN since the marker
        # key (`_schema_version`) starts with an underscore and no real VIN
        # does.
        self.assertEqual(
            state.load_seen_vins(),
            {state._SCHEMA_VERSION_KEY: state.SCHEMA_VERSION},
        )
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

    # ---- schema v2: migration ----

    def _write_v1_state(self, payload: dict) -> None:
        """Write a synthetic pre-v2 seen-vins.json (no _schema_version,
        no email_signals on records) to the patched tempdir."""
        state.SEEN_VINS_PATH.write_text(json.dumps(payload, indent=2))

    def test_v1_state_migrates_on_load(self):
        # Synthetic v1 file: VIN records with the C2-era per_provider
        # shape but no email_signals field and no _schema_version marker.
        self._write_v1_state({
            "4JGFF8FE2SB431338": {
                "first_seen": "2026-01-01T00:00:00",
                "last_seen": "2026-01-05T00:00:00",
                "per_provider": {
                    "cars_com": {
                        "first_seen": "2026-01-01T00:00:00",
                        "last_seen": "2026-01-05T00:00:00",
                        "last_metadata": {"price": 95000},
                        "listing_urls": ["https://example.com/a"],
                    }
                },
            }
        })

        loaded = state.load_seen_vins()

        self.assertEqual(loaded[state._SCHEMA_VERSION_KEY], state.SCHEMA_VERSION)
        record = loaded["4JGFF8FE2SB431338"]
        self.assertIn("email_signals", record)
        self.assertEqual(record["email_signals"], [])
        # Pre-existing fields are untouched.
        self.assertEqual(record["first_seen"], "2026-01-01T00:00:00")
        self.assertEqual(
            record["per_provider"]["cars_com"]["last_metadata"],
            {"price": 95000},
        )

    def test_migration_is_idempotent(self):
        # An already-migrated v2 file loads unchanged.
        self._write_v1_state({
            "_schema_version": 2,
            "VIN": {
                "first_seen": "2026-01-01T00:00:00",
                "last_seen": "2026-01-01T00:00:00",
                "per_provider": {},
                "email_signals": [
                    {
                        "provider": "cars_com",
                        "observed_at": "2026-01-01T00:00:00",
                        "price_drop_delta": 1500.0,
                        "ask_at_observation": 91000.0,
                    }
                ],
            },
        })

        loaded = state.load_seen_vins()

        self.assertEqual(loaded[state._SCHEMA_VERSION_KEY], 2)
        # The pre-existing signal survives unchanged.
        self.assertEqual(len(loaded["VIN"]["email_signals"]), 1)
        self.assertEqual(
            loaded["VIN"]["email_signals"][0]["price_drop_delta"], 1500.0
        )

    def test_migration_persists_after_save(self):
        # First load migrates in memory; the next save (triggered by
        # mark_seen) should persist the migrated state to disk so
        # future loads don't re-run the migration unnecessarily.
        self._write_v1_state({
            "OLDVIN": {
                "first_seen": "2026-01-01T00:00:00",
                "last_seen": "2026-01-01T00:00:00",
                "per_provider": {},
            }
        })

        # Trigger a save by adding a new VIN.
        state.mark_seen("NEWVIN", "mbusa", None, {"price": 80000})

        raw = json.loads(state.SEEN_VINS_PATH.read_text())
        self.assertEqual(raw[state._SCHEMA_VERSION_KEY], state.SCHEMA_VERSION)
        # Old record was migrated.
        self.assertEqual(raw["OLDVIN"]["email_signals"], [])
        # New record was created with the v2 shape.
        self.assertEqual(raw["NEWVIN"]["email_signals"], [])

    # ---- schema v2: email_signals helpers ----

    def test_mark_seen_initializes_email_signals_on_new_record(self):
        state.mark_seen("NEWVIN", "mbusa", None, {})
        record = state.load_seen_vins()["NEWVIN"]
        self.assertEqual(record["email_signals"], [])

    def test_add_email_signal_creates_record_when_vin_unknown(self):
        state.add_email_signal(
            "UNKNOWNVIN",
            "cars_com",
            price_drop_delta=2000.0,
            ask_at_observation=89000.0,
        )

        record = state.load_seen_vins()["UNKNOWNVIN"]
        self.assertIn("first_seen", record)
        self.assertIn("last_seen", record)
        self.assertEqual(record["per_provider"], {})
        self.assertEqual(len(record["email_signals"]), 1)
        signal = record["email_signals"][0]
        self.assertEqual(signal["provider"], "cars_com")
        self.assertEqual(signal["price_drop_delta"], 2000.0)
        self.assertEqual(signal["ask_at_observation"], 89000.0)
        self.assertIn("observed_at", signal)

    def test_add_email_signal_appends_to_existing_history(self):
        state.add_email_signal(
            "VIN", "cars_com",
            price_drop_delta=1000.0, ask_at_observation=91000.0,
        )
        state.add_email_signal(
            "VIN", "cars_com",
            price_drop_delta=500.0, ask_at_observation=90500.0,
        )
        state.add_email_signal(
            "VIN", "autotrader",
            price_drop_delta=2500.0, ask_at_observation=88000.0,
        )

        signals = state.load_seen_vins()["VIN"]["email_signals"]
        self.assertEqual(len(signals), 3)
        # FIFO append order preserved.
        self.assertEqual(signals[0]["price_drop_delta"], 1000.0)
        self.assertEqual(signals[1]["price_drop_delta"], 500.0)
        self.assertEqual(signals[2]["provider"], "autotrader")

    def test_add_email_signal_survives_mark_seen(self):
        # Common sequence: ingest sees a VIN via MBUSA (mark_seen),
        # then later that day a cars.com email arrives mentioning the
        # same VIN (add_email_signal). The two writes must not clobber
        # each other.
        state.add_email_signal(
            "VIN", "cars_com",
            price_drop_delta=1500.0, ask_at_observation=89000.0,
        )
        state.mark_seen("VIN", "mbusa", None, {"price": 89000})

        record = state.load_seen_vins()["VIN"]
        self.assertEqual(len(record["email_signals"]), 1)
        self.assertEqual(record["email_signals"][0]["provider"], "cars_com")
        self.assertIn("mbusa", record["per_provider"])

    def test_add_email_signal_accepts_optional_fields_as_none(self):
        # Some emails carry only a VIN and a price-drop badge with no
        # explicit dollar deltas; the helper must accept Nones cleanly.
        state.add_email_signal("VIN", "cargurus")
        signal = state.load_seen_vins()["VIN"]["email_signals"][0]
        self.assertIsNone(signal["price_drop_delta"])
        self.assertIsNone(signal["ask_at_observation"])

    def test_add_email_signal_respects_explicit_observed_at(self):
        explicit = "2026-04-01T12:00:00-04:00"
        state.add_email_signal(
            "VIN", "cars_com",
            observed_at=explicit,
        )
        signal = state.load_seen_vins()["VIN"]["email_signals"][0]
        self.assertEqual(signal["observed_at"], explicit)

    def test_get_email_signals_returns_empty_for_unknown_vin(self):
        self.assertEqual(state.get_email_signals("NEVERSEEN"), [])

    def test_get_email_signals_returns_history_for_known_vin(self):
        state.add_email_signal(
            "VIN", "cars_com",
            price_drop_delta=500.0, ask_at_observation=90000.0,
        )
        state.add_email_signal(
            "VIN", "cars_com",
            price_drop_delta=1000.0, ask_at_observation=89000.0,
        )
        signals = state.get_email_signals("VIN")
        self.assertEqual(len(signals), 2)
        self.assertEqual(signals[0]["price_drop_delta"], 500.0)
        self.assertEqual(signals[1]["price_drop_delta"], 1000.0)

    def test_get_email_signals_returns_copy(self):
        # Returning the internal list would let a caller mutate state
        # without going through save_seen_vins. The helper returns a
        # fresh list per call.
        state.add_email_signal("VIN", "cars_com")
        signals = state.get_email_signals("VIN")
        signals.append({"provider": "rogue", "observed_at": "x"})

        # Persisted state should NOT have the rogue entry.
        fresh = state.get_email_signals("VIN")
        self.assertEqual(len(fresh), 1)


if __name__ == "__main__":
    unittest.main()
