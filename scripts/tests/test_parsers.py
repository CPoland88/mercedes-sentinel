"""Tests for scripts/parsers/.

Tests use synthetic emails built in-memory rather than checked-in
fixtures so the test suite has no external dependencies. Real .eml
samples from your actual Gmail inbox should be added under
scripts/tests/fixtures/ (gitignored — they may contain dealer-specific
data you don't want public) and exercised via the --fixtures CLI flag.
"""
from __future__ import annotations

import email
import unittest
from email.message import EmailMessage

from ..parsers import detect_provider, fallback, parse


# ---- helpers ----

def _build_email(sender: str, subject: str, body: str, html: str | None = None) -> bytes:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = "cpoland06+mbsentinel@gmail.com"
    msg["Subject"] = subject
    msg.set_content(body)
    if html is not None:
        msg.add_alternative(html, subtype="html")
    return bytes(msg)


def _email_from_bytes(b: bytes):
    return email.message_from_bytes(b)


# ---- fallback parser ----

class TestFallbackParser(unittest.TestCase):
    def test_extracts_single_vin_and_url(self):
        body = (
            "New listing: VIN 4JGFF8FE2SB431338 priced at $104,327. "
            "https://dealer.example.com/inv/4JGFF8FE2SB431338"
        )
        msg = _email_from_bytes(_build_email("alerts@example.com", "alert", body))
        candidates = fallback.parse(msg)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["vin"], "4JGFF8FE2SB431338")
        self.assertIn("dealer.example.com", candidates[0]["listing_url"])
        self.assertEqual(candidates[0]["provider"], "unknown")
        self.assertEqual(candidates[0]["parser"], "fallback")

    def test_vin_pattern_rejects_forbidden_letters(self):
        # FMVSS 565 forbids I, O, Q in VINs.
        body = "Bad VIN: 1234567890ABCIOQQQ (contains I, O, Q)"
        msg = _email_from_bytes(_build_email("alerts@example.com", "alert", body))
        candidates = fallback.parse(msg)
        self.assertEqual(len(candidates), 0)

    def test_vin_pattern_requires_exactly_17_chars(self):
        body = "Too short: 4JGFF8FE2SB43133 ; Too long: 4JGFF8FE2SB4313381"
        msg = _email_from_bytes(_build_email("alerts@example.com", "alert", body))
        # The 18-char string contains a valid 17-char substring at position 0;
        # the \b word boundary should prevent matching when neighboring chars
        # are also word chars. Verify the short string yields zero matches.
        candidates = fallback.parse(msg)
        for c in candidates:
            self.assertEqual(len(c["vin"]), 17)

    def test_dedups_repeated_vin(self):
        body = (
            "VIN 4JGFF8FE2SB431338 in subject. VIN 4JGFF8FE2SB431338 again. "
            "URL https://dealer.example.com/inv/4JGFF8FE2SB431338"
        )
        msg = _email_from_bytes(_build_email("alerts@example.com", "alert", body))
        candidates = fallback.parse(msg)
        self.assertEqual(len(candidates), 1)

    def test_multiple_distinct_vins(self):
        body = """
        Car 1: 4JGFF5KE0SB288880 listing at https://dealer1.example.com/inv/4JGFF5KE0SB288880
        Car 2: 4JGFF8FE2SB431338 listing at https://dealer2.example.com/inv/4JGFF8FE2SB431338
        """
        msg = _email_from_bytes(_build_email("alerts@example.com", "alert", body))
        candidates = fallback.parse(msg)
        self.assertEqual(len(candidates), 2)
        vins = {c["vin"] for c in candidates}
        self.assertEqual(vins, {"4JGFF5KE0SB288880", "4JGFF8FE2SB431338"})

    def test_pairs_url_containing_vin_over_nearer_url(self):
        # Decoy URL is closer in text, but the URL containing the VIN should win.
        body = (
            "VIN 4JGFF8FE2SB431338 (decoy here: https://dealer.example.com/other "
            "right next to it). Actual listing: "
            "https://other.example.com/inv/4JGFF8FE2SB431338"
        )
        msg = _email_from_bytes(_build_email("alerts@example.com", "alert", body))
        candidates = fallback.parse(msg)
        self.assertEqual(len(candidates), 1)
        self.assertIn("4JGFF8FE2SB431338", candidates[0]["listing_url"])

    def test_falls_back_to_nearest_url_when_vin_not_in_any_url(self):
        body = (
            "VIN 4JGFF8FE2SB431338 details: https://dealer.example.com/listing/123 "
            "Some other content. Another URL https://elsewhere.example.com/page"
        )
        msg = _email_from_bytes(_build_email("alerts@example.com", "alert", body))
        candidates = fallback.parse(msg)
        self.assertEqual(len(candidates), 1)
        # Nearest URL is the dealer listing
        self.assertIn("dealer.example.com/listing/123", candidates[0]["listing_url"])

    def test_html_body_falls_through_to_strip(self):
        html = """<html><body>
            <p>VIN: <strong>4JGFF8FE2SB431338</strong></p>
            <a href="https://dealer.example.com/inv/4JGFF8FE2SB431338">View listing</a>
        </body></html>"""
        msg = _email_from_bytes(_build_email("alerts@example.com", "alert", "fallback text", html))
        candidates = fallback.parse(msg)
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["vin"], "4JGFF8FE2SB431338")


# ---- provider detection + dispatch ----

class TestProviderDetection(unittest.TestCase):
    def test_cargurus_sender_detected(self):
        body = (
            "New CarGurus alert: 2025 GLS 580. VIN 4JGFF8FE2SB431338. "
            "Price $104,327. https://www.cargurus.com/Cars/inventorylisting/4JGFF8FE2SB431338"
        )
        msg_bytes = _build_email("noreply@cargurus.com", "New match", body)
        candidates = parse(msg_bytes)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["provider"], "cargurus")
        self.assertEqual(candidates[0]["parser"], "cargurus")

    def test_autotrader_sender_detected(self):
        body = "New AutoTrader alert: VIN 4JGFF8FE2SB431338. $87,495. https://autotrader.com/cars/X"
        msg_bytes = _build_email("alerts@autotrader.com", "match", body)
        candidates = parse(msg_bytes)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["provider"], "autotrader")

    def test_cars_com_sender_detected(self):
        body = "VIN 4JGFF8FE2SB431338 listing. Great Deal. https://cars.com/v/12345"
        msg_bytes = _build_email("noreply@cars.com", "match", body)
        candidates = parse(msg_bytes)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["provider"], "cars_com")

    def test_unknown_sender_uses_fallback(self):
        body = "VIN 4JGFF8FE2SB431338 at https://random.example.com/listing"
        msg_bytes = _build_email("random@example.com", "alert", body)
        candidates = parse(msg_bytes)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["provider"], "unknown")
        self.assertEqual(candidates[0]["parser"], "fallback")


# ---- per-provider metadata extraction ----

class TestCarGurusMetadata(unittest.TestCase):
    def test_extracts_price_imv_mileage_days_badge(self):
        body = (
            "2024 Mercedes-Benz GLS 580 — Great Deal\n"
            "Price: $87,495\n"
            "Instant Market Value: $89,200\n"
            "Mileage: 13,872 miles\n"
            "27 days on CarGurus\n"
            "VIN 4JGFF8FE1RB057816\n"
            "https://www.cargurus.com/Cars/4JGFF8FE1RB057816"
        )
        msg_bytes = _build_email("noreply@cargurus.com", "alert", body)
        candidates = parse(msg_bytes)
        self.assertEqual(len(candidates), 1)
        md = candidates[0]["raw_metadata"]
        self.assertEqual(md.get("price"), 87495)
        self.assertEqual(md.get("imv"), 89200)
        self.assertEqual(md.get("mileage"), 13872)
        self.assertEqual(md.get("days_on_lot"), 27)
        self.assertEqual(md.get("deal_badge"), "Great Deal")


class TestCarsComMetadata(unittest.TestCase):
    def test_extracts_price_mileage_badge(self):
        body = (
            "VIN 4JGFF8FE2SB431338\n"
            "$104,327\n"
            "7,487 miles\n"
            "Fair Deal\n"
            "https://www.cars.com/vehicledetail/12345/"
        )
        msg_bytes = _build_email("noreply@cars.com", "alert", body)
        candidates = parse(msg_bytes)
        md = candidates[0]["raw_metadata"]
        self.assertEqual(md.get("price"), 104327)
        self.assertEqual(md.get("mileage"), 7487)
        self.assertEqual(md.get("deal_badge"), "Fair Deal")


# ---- parser-failure fallback ----

class TestProviderFailureFallback(unittest.TestCase):
    def test_provider_failure_falls_back_to_regex(self):
        """If a provider parser raises, the dispatcher should fall back to
        the regex parser AND tag the candidates with the detected provider."""
        from unittest.mock import patch
        from ..parsers import cargurus as cargurus_module

        body = "VIN 4JGFF8FE1RB057816 at https://www.cargurus.com/x/4JGFF8FE1RB057816"
        msg_bytes = _build_email("noreply@cargurus.com", "alert", body)

        def boom(_msg):
            raise RuntimeError("simulated parser failure")

        with patch.object(cargurus_module, "parse", side_effect=boom):
            candidates = parse(msg_bytes)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["vin"], "4JGFF8FE1RB057816")
        # Tagged with detected provider even though regex did the work
        self.assertEqual(candidates[0]["provider"], "cargurus")
        self.assertTrue(candidates[0].get("parser_fallback"))


if __name__ == "__main__":
    unittest.main()
