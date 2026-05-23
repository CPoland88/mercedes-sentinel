"""Tests for scripts/parsers/.

Tests use synthetic emails built in-memory rather than checked-in
fixtures so the test suite has no external dependencies. Real .eml
samples from your actual Gmail inbox should be added under
scripts/tests/fixtures/ (gitignored — they may contain dealer-specific
data you don't want public) and exercised via the --fixtures CLI flag.

Cars.com tests assert the post-MBUSA-pivot EmailSignal shape: no VIN,
``source: "email_signal"``, ``cars_com_uuid`` extracted from the URL.
The parser no longer hydrates listing URLs, so no hydration mock is
needed.
"""
from __future__ import annotations

import email
import unittest
from email.message import EmailMessage

from ..parsers import cars_com, detect_provider, fallback, parse


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

    def test_all_digit_17_char_string_is_not_a_vin(self):
        """Real VINs always have at least one letter (WMI is alpha,
        model-year position 10 is always a letter). An all-digit
        17-char string is some other identifier (observed in the wild
        from cars.com listing pages: `21360397902943945`). Filtering
        these prevents poisoning seen-vins.json with bogus dedup keys."""
        body = "Inventory ID 21360397902943945 listed at https://x.example.com/y"
        msg = _email_from_bytes(_build_email("alerts@example.com", "alert", body))
        candidates = fallback.parse(msg)
        self.assertEqual(len(candidates), 0)

    def test_filters_bogus_id_keeps_real_vin(self):
        body = (
            "Listing 21360397902943945 with VIN 4JGFF8FE2SB431338 "
            "at https://dealer.example.com/inv/4JGFF8FE2SB431338"
        )
        msg = _email_from_bytes(_build_email("alerts@example.com", "alert", body))
        candidates = fallback.parse(msg)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["vin"], "4JGFF8FE2SB431338")

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


def _cars_com_block(uuid: str, year: str, trim: str, mileage_str: str,
                    price: str, price_drop: str | None = None) -> str:
    """Build one vehicle block matching the cars.com email template.

    Shared by TestCarsComMetadata and TestCarsComHydration. The wire
    format mirrors what we observed in real price-drop alerts: title,
    URL (with angle brackets), mileage, optional '↓ $N price drop'
    line, ask price, 'View details' line, duplicate URL.
    """
    delta_line = f"↓ {price_drop} price drop \n\n\n" if price_drop else ""
    url = f"https://www.cars.com/vehicledetail/{uuid}?aff=acqem100"
    return (
        f"\n {year} Mercedes-Benz GLS {trim} 4MATIC  \n"
        f"<{url}>\n"
        f" {mileage_str} \n"
        f"{delta_line}"
        f" {price} \n"
        f"View details about this car ↗ \n"
        f"<{url}>\n"
    )


class TestCarsComMetadata(unittest.TestCase):
    """Per-vehicle block parsing for Cars.com saved-search alerts.

    The cars.com price-drop and new-listing email templates use a
    repeating block per vehicle: title line, listing URL, mileage,
    optional price-drop delta, ask price, then a duplicate of the URL
    as a "View details" link. The block-detection algorithm groups by
    the per-vehicle URL UUID, so the duplicate URL doesn't cause
    duplicate candidates.

    Post-MBUSA-pivot: the parser emits **EmailSignals** rather than
    full candidates. No VIN field (cars.com strips it from emails);
    ``source: "email_signal"`` and ``cars_com_uuid`` flag the dict
    for commit 6's matcher. EmailSignal-specific shape assertions
    live in :class:`TestCarsComEmailSignalShape` below.

    These tests build synthetic bodies that mirror the real template.
    Real .eml samples live in scripts/tests/fixtures/ (gitignored).
    """

    _block = staticmethod(_cars_com_block)

    def test_single_vehicle_block_extracts_full_metadata(self):
        body = self._block("12345abc", "2024", "580", "13,872 mi.",
                           "$87,495", price_drop="$1,245")
        msg = _build_email("noreply@cars.com", "Price drop!", body)
        candidates = parse(msg)
        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertIn("vehicledetail/12345abc", c["listing_url"])
        self.assertEqual(c["provider"], "cars_com")
        self.assertEqual(c["parser"], "cars_com")
        md = c["raw_metadata"]
        self.assertEqual(md["year"], 2024)
        self.assertEqual(md["trim_number"], "580")
        self.assertEqual(md["drivetrain"], "4MATIC")
        self.assertEqual(md["mileage"], 13872)
        self.assertEqual(md["price"], 87495)
        self.assertEqual(md["price_drop_delta"], 1245)

    def test_three_vehicle_blocks_emit_three_candidates(self):
        # Use real-format hex GUIDs matching observed cars.com URLs.
        body = (
            self._block("5b475d0d-b34a-40b6-b372-83469b4b7655", "2024",
                        "450", "38,099 mi.", "$59,397", price_drop="$1,245") +
            self._block("b2cc612e-a40b-4073-a457-4facb2d82a6f", "2024",
                        "450", "37,802 mi.", "$67,864", price_drop="$1,036") +
            self._block("d092dc28-4909-4dca-ac69-855bdf8da7ea", "2024",
                        "450", "25,619 mi.", "$71,999", price_drop="$498")
        )
        msg = _build_email("noreply@cars.com", "Price drop!", body)
        candidates = parse(msg)
        self.assertEqual(len(candidates), 3)
        # Order preserved from email
        uuids = [c["listing_url"].split("/vehicledetail/")[1].split("?")[0]
                 for c in candidates]
        self.assertEqual(uuids, [
            "5b475d0d-b34a-40b6-b372-83469b4b7655",
            "b2cc612e-a40b-4073-a457-4facb2d82a6f",
            "d092dc28-4909-4dca-ac69-855bdf8da7ea",
        ])
        # Prices distinct and in order
        prices = [c["raw_metadata"]["price"] for c in candidates]
        self.assertEqual(prices, [59397, 67864, 71999])

    def test_duplicate_url_per_vehicle_does_not_double_emit(self):
        """Each vehicle's URL appears twice (top + 'View details'). The
        block algorithm groups by UUID and emits one candidate per UUID."""
        body = self._block("dup-uuid", "2025", "580", "5,000 mi.", "$104,327")
        # _block already includes the duplicate URL. Sanity-check assumption:
        self.assertEqual(body.count("vehicledetail/dup-uuid"), 2)
        msg = _build_email("noreply@cars.com", "alert", body)
        candidates = parse(msg)
        self.assertEqual(len(candidates), 1)

    def test_mileage_mi_abbreviation_with_period(self):
        body = self._block("a", "2024", "450", "38,099 mi.", "$59,397")
        candidates = parse(_build_email("noreply@cars.com", "alert", body))
        self.assertEqual(candidates[0]["raw_metadata"]["mileage"], 38099)

    def test_mileage_mi_abbreviation_no_period(self):
        body = self._block("a", "2024", "450", "38,099 mi", "$59,397")
        candidates = parse(_build_email("noreply@cars.com", "alert", body))
        self.assertEqual(candidates[0]["raw_metadata"]["mileage"], 38099)

    def test_mileage_full_word_still_works(self):
        body = self._block("a", "2024", "450", "38,099 miles", "$59,397")
        candidates = parse(_build_email("noreply@cars.com", "alert", body))
        self.assertEqual(candidates[0]["raw_metadata"]["mileage"], 38099)

    def test_mileage_does_not_match_inside_word(self):
        # "milestones" should NOT be parsed as a mileage value.
        body = self._block("a", "2024", "450", "0000 milestones", "$59,397")
        candidates = parse(_build_email("noreply@cars.com", "alert", body))
        self.assertNotIn("mileage", candidates[0]["raw_metadata"])

    def test_ask_price_wins_over_price_drop_delta(self):
        # Body has $1,245 (delta) and $59,397 (ask). Ask must win.
        body = self._block("a", "2024", "450", "38,099 mi.",
                           "$59,397", price_drop="$1,245")
        candidates = parse(_build_email("noreply@cars.com", "alert", body))
        md = candidates[0]["raw_metadata"]
        self.assertEqual(md["price"], 59397)
        self.assertEqual(md["price_drop_delta"], 1245)

    def test_block_without_price_drop_still_parses(self):
        # New-listing alerts don't have a price-drop line.
        body = self._block("a", "2024", "580", "5,000 mi.", "$104,327")
        candidates = parse(_build_email("noreply@cars.com", "alert", body))
        md = candidates[0]["raw_metadata"]
        self.assertEqual(md["price"], 104327)
        self.assertNotIn("price_drop_delta", md)

    def test_no_vehicledetail_urls_falls_back_to_regex(self):
        """Non-standard cars.com formats (account notices, weekly
        digests) shouldn't be silently dropped — fallback parser still
        runs and tags candidates with provider=cars_com."""
        body = (
            "Your saved search summary: VIN 4JGFF8FE2SB431338 was "
            "viewed by 12 people. https://www.cars.com/account/"
        )
        candidates = parse(_build_email("noreply@cars.com", "summary", body))
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["provider"], "cars_com")
        self.assertTrue(candidates[0].get("parser_fallback"))
        self.assertEqual(candidates[0]["vin"], "4JGFF8FE2SB431338")

    def test_email_with_no_text_plain_falls_back(self):
        """HTML-only cars.com emails are rare but possible. Defer to
        fallback so they're not silently dropped."""
        html = (
            "<html><body>"
            "<p>VIN <b>4JGFF8FE2SB431338</b> at "
            "<a href='https://www.cars.com/vehicledetail/abc'>this listing</a></p>"
            "</body></html>"
        )
        # _build_email with html and EMPTY text body still creates text/plain;
        # to truly omit text/plain we have to build the message differently.
        msg = EmailMessage()
        msg["From"] = "noreply@cars.com"
        msg["Subject"] = "alert"
        msg.set_content(html, subtype="html")
        candidates = parse(bytes(msg))
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["provider"], "cars_com")


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


class TestCarsComEmailSignalShape(unittest.TestCase):
    """Post-MBUSA-pivot output contract for cars.com.

    cars.com emails no longer feed the queue directly. The parser
    emits EmailSignal-shaped dicts: no VIN (cars.com strips it from
    alert bodies), ``source: "email_signal"`` to route through commit
    6's matcher, and ``cars_com_uuid`` for the audit trail and any
    future direct-match scheme.
    """

    def test_signal_has_source_email_signal(self):
        body = _cars_com_block(
            "5b475d0d-b34a-40b6-b372-83469b4b7655",
            "2024", "450", "38,099 mi.", "$59,397",
        )
        signals = parse(_build_email("noreply@cars.com", "alert", body))
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["source"], "email_signal")

    def test_signal_has_no_vin_field(self):
        body = _cars_com_block(
            "5b475d0d-b34a-40b6-b372-83469b4b7655",
            "2024", "450", "38,099 mi.", "$59,397",
        )
        signals = parse(_build_email("noreply@cars.com", "alert", body))
        # Absent — not present-but-None. Downstream defensively uses
        # .get("vin") so both shapes would work, but absence is the
        # cleaner contract.
        self.assertNotIn("vin", signals[0])

    def test_signal_carries_cars_com_uuid(self):
        uuid = "5b475d0d-b34a-40b6-b372-83469b4b7655"
        body = _cars_com_block(uuid, "2024", "450", "38,099 mi.", "$59,397")
        signals = parse(_build_email("noreply@cars.com", "alert", body))
        self.assertEqual(signals[0]["cars_com_uuid"], uuid)

    def test_signal_listing_url_preserved_for_audit(self):
        uuid = "5b475d0d-b34a-40b6-b372-83469b4b7655"
        body = _cars_com_block(uuid, "2024", "450", "38,099 mi.", "$59,397")
        signals = parse(_build_email("noreply@cars.com", "alert", body))
        self.assertIn(f"vehicledetail/{uuid}", signals[0]["listing_url"])

    def test_signal_carries_price_drop_delta_for_matcher(self):
        # The whole point of the post-pivot cars.com path: feed the
        # price-drop delta to triage as additional negotiation context.
        body = _cars_com_block(
            "5b475d0d-b34a-40b6-b372-83469b4b7655",
            "2024", "580", "13,872 mi.", "$87,495", price_drop="$1,245",
        )
        signals = parse(_build_email("noreply@cars.com", "alert", body))
        md = signals[0]["raw_metadata"]
        self.assertEqual(md["price_drop_delta"], 1245)
        self.assertEqual(md["price"], 87495)

    def test_parser_does_not_import_hydrate(self):
        # The hydrate module was deleted in commit 7 of the
        # Architecture B pivot. This test guards against accidentally
        # reintroducing a hydrate dependency on a future refactor.
        self.assertFalse(
            hasattr(cars_com, "hydrate"),
            "cars_com.py must not import scripts.hydrate — emails are "
            "signal-only and don't hit the network post-pivot.",
        )
        self.assertFalse(
            hasattr(cars_com, "_try_hydrate"),
            "_try_hydrate was removed in commit 5; do not reintroduce.",
        )


if __name__ == "__main__":
    unittest.main()
