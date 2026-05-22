"""Tests for scripts/hydrate.py.

Tests use synthetic HTML strings built in-memory and a MagicMock-injected
httpx.Client so the suite stays offline. Real cars.com HTML snapshots
should be saved under scripts/tests/fixtures/ for ad-hoc CLI exercise
(see fixtures/README.md), but unit tests don't depend on them.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

import httpx

from .. import hydrate
from ..hydrate import (
    FileFetcher,
    HttpxFetcher,
    HydratedListing,
    HydrationError,
    hydrate_cars_com,
)


# ---------- HydratedListing.to_dict ----------

class TestHydratedListingToDict(unittest.TestCase):
    def test_drops_empty(self):
        listing = HydratedListing()
        self.assertEqual(listing.to_dict(), {})

    def test_keeps_filled(self):
        listing = HydratedListing(
            vin="4JGFF8FE2SB431338",
            dealer_name="MB of Tysons",
            dealer_city="Vienna",
            dealer_state="VA",
            packages=["Pinnacle"],
            cpo_badge="Certified Pre-Owned",
        )
        out = listing.to_dict()
        self.assertEqual(out["vin"], "4JGFF8FE2SB431338")
        self.assertEqual(out["dealer_name"], "MB of Tysons")
        self.assertEqual(out["packages"], ["Pinnacle"])
        # Empty fields drop out
        self.assertNotIn("exterior_color", out)
        self.assertNotIn("interior_color", out)


# ---------- FileFetcher ----------

class TestFileFetcher(unittest.TestCase):
    def test_returns_raw_html_string(self):
        f = FileFetcher({"https://cars.com/x": "<html>hello</html>"})
        self.assertEqual(f.get("https://cars.com/x"), "<html>hello</html>")

    def test_raises_on_unknown_url(self):
        f = FileFetcher({})
        with self.assertRaises(HydrationError):
            f.get("https://cars.com/missing")


# ---------- JSON-LD parsing ----------

class TestParseJsonLd(unittest.TestCase):
    def test_vehicle_object_extracts_vin_and_color(self):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "Vehicle",
         "vehicleIdentificationNumber": "4JGFF8FE2SB431338",
         "color": "Emerald Green Metallic",
         "vehicleInteriorColor": "Macchiato Beige",
         "modelDate": "2024",
         "bodyType": "SUV",
         "vehicleConfiguration": "GLS 580 4MATIC"}
        </script>
        </head><body></body></html>
        """
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.vin, "4JGFF8FE2SB431338")
        self.assertEqual(listing.exterior_color, "Emerald Green Metallic")
        self.assertEqual(listing.interior_color, "Macchiato Beige")
        self.assertEqual(listing.model_year, 2024)
        self.assertEqual(listing.body_style, "SUV")
        self.assertEqual(listing.trim, "GLS 580 4MATIC")

    def test_graph_wrapper(self):
        html = """
        <script type="application/ld+json">
        {"@context": "https://schema.org",
         "@graph": [
            {"@type": "Vehicle", "vehicleIdentificationNumber": "4JGFF5KE0SB288880"}
         ]}
        </script>
        """
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.vin, "4JGFF5KE0SB288880")

    def test_dealer_via_seller(self):
        html = """
        <script type="application/ld+json">
        {"@type": "Vehicle",
         "vehicleIdentificationNumber": "4JGFF8FE2SB431338",
         "seller": {
            "@type": "AutoDealer",
            "name": "Mercedes-Benz of Tysons Corner",
            "address": {
                "addressLocality": "Vienna",
                "addressRegion": "VA",
                "postalCode": "22182"
            }
         }}
        </script>
        """
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.dealer_name, "Mercedes-Benz of Tysons Corner")
        self.assertEqual(listing.dealer_city, "Vienna")
        self.assertEqual(listing.dealer_state, "VA")
        self.assertEqual(listing.dealer_zip, "22182")

    def test_dealer_via_separate_autodealer_object(self):
        html = """
        <script type="application/ld+json">
        [{"@type": "Vehicle", "vehicleIdentificationNumber": "4JGFF8FE2SB431338"},
         {"@type": "AutoDealer", "name": "MB White Plains",
          "address": {"addressLocality": "White Plains", "addressRegion": "NY"}}]
        </script>
        """
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.vin, "4JGFF8FE2SB431338")
        self.assertEqual(listing.dealer_name, "MB White Plains")
        self.assertEqual(listing.dealer_city, "White Plains")
        self.assertEqual(listing.dealer_state, "NY")

    def test_dealer_via_offers_seller_nesting(self):
        html = """
        <script type="application/ld+json">
        {"@type": "Vehicle",
         "vehicleIdentificationNumber": "4JGFF8FE2SB431338",
         "offers": {"seller": {"name": "Dealer Via Offers",
                               "address": {"addressLocality": "Tysons"}}}}
        </script>
        """
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.dealer_name, "Dealer Via Offers")
        self.assertEqual(listing.dealer_city, "Tysons")

    def test_malformed_jsonld_skipped_cleanly(self):
        html = """
        <script type="application/ld+json">{this is not valid json}</script>
        <script type="application/ld+json">
        {"@type": "Vehicle", "vehicleIdentificationNumber": "4JGFF8FE2SB431338"}
        </script>
        """
        listing = hydrate._parse_vehicledetail_html(html)
        # Should NOT raise on the malformed block; should still pick up the valid one.
        self.assertEqual(listing.vin, "4JGFF8FE2SB431338")


# ---------- CSS selector parsing ----------

class TestParseCssSelectors(unittest.TestCase):
    def test_vin_via_data_testid(self):
        html = """<html><body>
        <span data-testid="vin-value">4JGFF8FE2SB431338</span>
        </body></html>"""
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.vin, "4JGFF8FE2SB431338")

    def test_vin_via_data_vin_attribute(self):
        html = """<html><body>
        <div data-vin="4JGFF5KE0SB288880">Click for details</div>
        </body></html>"""
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.vin, "4JGFF5KE0SB288880")

    def test_cpo_badge_text_match(self):
        html = """<html><body>
        <p>This vehicle is Mercedes-Benz Certified Pre-Owned.</p>
        <span data-testid="vin-value">4JGFF8FE2SB431338</span>
        </body></html>"""
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.cpo_badge, "Mercedes-Benz Certified Pre-Owned")

    def test_cpo_badge_normalizes_cpo_acronym(self):
        html = """<html><body>
        <p>CPO inventory only.</p>
        <span data-testid="vin-value">4JGFF8FE2SB431338</span>
        </body></html>"""
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.cpo_badge, "Certified Pre-Owned")

    def test_packages_under_heading(self):
        html = """<html><body>
        <h3>Packages</h3>
        <ul>
            <li>Pinnacle Trim</li>
            <li>Acoustic Comfort Package</li>
            <li>Warmth &amp; Comfort Package</li>
        </ul>
        <span data-testid="vin-value">4JGFF8FE2SB431338</span>
        </body></html>"""
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(
            listing.packages,
            ["Pinnacle Trim", "Acoustic Comfort Package", "Warmth & Comfort Package"],
        )


# ---------- Regex fallback ----------

class TestParseRegexFallback(unittest.TestCase):
    def test_vin_in_raw_html_when_no_jsonld_or_css(self):
        html = """<html><body>
        <p>Some unstructured text that mentions VIN 4JGFF8FE2SB431338 somewhere.</p>
        </body></html>"""
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.vin, "4JGFF8FE2SB431338")

    def test_no_vin_anywhere_returns_none(self):
        html = "<html><body>Nothing here.</body></html>"
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertIsNone(listing.vin)


# ---------- Strategy layering ----------

class TestStrategyLayering(unittest.TestCase):
    def test_jsonld_vin_wins_over_regex(self):
        # Two distinct VINs — JSON-LD should win.
        html = """
        <script type="application/ld+json">
        {"@type": "Vehicle", "vehicleIdentificationNumber": "4JGFF8FE2SB431338"}
        </script>
        <p>Stray VIN 4JGFF5KE0SB288880 in the body</p>
        """
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.vin, "4JGFF8FE2SB431338")

    def test_css_fills_gaps_left_by_jsonld(self):
        # JSON-LD has no color; CSS-found badge fills CPO field.
        html = """
        <script type="application/ld+json">
        {"@type": "Vehicle", "vehicleIdentificationNumber": "4JGFF8FE2SB431338"}
        </script>
        <p>Certified Pre-Owned inventory</p>
        """
        listing = hydrate._parse_vehicledetail_html(html)
        self.assertEqual(listing.vin, "4JGFF8FE2SB431338")
        self.assertEqual(listing.cpo_badge, "Certified Pre-Owned")


# ---------- Public API end-to-end ----------

class TestHydrateCarsComPublicApi(unittest.TestCase):
    def test_end_to_end_with_file_fetcher(self):
        html = """
        <script type="application/ld+json">
        {"@type": "Vehicle",
         "vehicleIdentificationNumber": "4JGFF8FE2SB431338",
         "color": "Twilight Blue Metallic",
         "seller": {"name": "MB of Tysons",
                    "address": {"addressLocality": "Vienna", "addressRegion": "VA"}}}
        </script>
        """
        fetcher = FileFetcher({"https://cars.com/vehicledetail/abc": html})
        listing = hydrate_cars_com("https://cars.com/vehicledetail/abc", fetcher=fetcher)
        self.assertEqual(listing.vin, "4JGFF8FE2SB431338")
        self.assertEqual(listing.exterior_color, "Twilight Blue Metallic")
        self.assertEqual(listing.dealer_name, "MB of Tysons")
        self.assertEqual(listing.dealer_city, "Vienna")


# ---------- HttpxFetcher (mocked) ----------

def _mock_response(status_code: int, text: str = "<html></html>") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.reason_phrase = {200: "OK", 404: "Not Found", 500: "Server Error", 503: "Service Unavailable"}.get(
        status_code, "Unknown"
    )
    return resp


class TestHttpxFetcher(unittest.TestCase):
    def _fetcher_with_mock_client(self, client: MagicMock) -> HttpxFetcher:
        # jitter_min/max set to 0 so the test doesn't sleep.
        return HttpxFetcher(jitter_min=0.0, jitter_max=0.0, client=client)

    def test_200_returns_text(self):
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _mock_response(200, "<html>ok</html>")
        f = self._fetcher_with_mock_client(client)
        self.assertEqual(f.get("https://cars.com/x"), "<html>ok</html>")
        client.get.assert_called_once_with("https://cars.com/x")

    def test_4xx_raises_immediately(self):
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _mock_response(404)
        f = self._fetcher_with_mock_client(client)
        with self.assertRaises(HydrationError) as cm:
            f.get("https://cars.com/missing")
        self.assertIn("4xx", str(cm.exception))
        # Should NOT retry on 4xx
        self.assertEqual(client.get.call_count, 1)

    def test_5xx_retries_then_raises(self):
        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = [_mock_response(500), _mock_response(503)]
        f = self._fetcher_with_mock_client(client)
        # Bypass the inter-retry sleep so the test is fast.
        with unittest.mock.patch.object(hydrate.time, "sleep"):
            with self.assertRaises(HydrationError) as cm:
                f.get("https://cars.com/down")
        self.assertIn("after retry", str(cm.exception))
        self.assertEqual(client.get.call_count, 2)

    def test_5xx_then_200_succeeds(self):
        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = [_mock_response(500), _mock_response(200, "<html>recovered</html>")]
        f = self._fetcher_with_mock_client(client)
        with unittest.mock.patch.object(hydrate.time, "sleep"):
            self.assertEqual(f.get("https://cars.com/flaky"), "<html>recovered</html>")
        self.assertEqual(client.get.call_count, 2)

    def test_network_error_retries(self):
        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = [
            httpx.ConnectError("connection refused"),
            _mock_response(200, "<html>ok</html>"),
        ]
        f = self._fetcher_with_mock_client(client)
        with unittest.mock.patch.object(hydrate.time, "sleep"):
            self.assertEqual(f.get("https://cars.com/x"), "<html>ok</html>")
        self.assertEqual(client.get.call_count, 2)

    def test_network_error_persists_raises(self):
        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = [
            httpx.ConnectError("conn refused 1"),
            httpx.ConnectError("conn refused 2"),
        ]
        f = self._fetcher_with_mock_client(client)
        with unittest.mock.patch.object(hydrate.time, "sleep"):
            with self.assertRaises(HydrationError) as cm:
                f.get("https://cars.com/x")
        self.assertIn("Network error", str(cm.exception))

    def test_jitter_skipped_on_first_request(self):
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _mock_response(200)
        f = HttpxFetcher(jitter_min=5.0, jitter_max=5.0, client=client)
        with unittest.mock.patch.object(hydrate.time, "sleep") as mock_sleep:
            f.get("https://cars.com/x")
            # First call must NOT sleep
            mock_sleep.assert_not_called()
            f.get("https://cars.com/y")
            # Second call MUST sleep (5.0s per the construction)
            self.assertEqual(mock_sleep.call_count, 1)
            self.assertEqual(mock_sleep.call_args[0][0], 5.0)


if __name__ == "__main__":
    unittest.main()
