"""Dev-only tool: capture a real HTML snapshot via the production
HttpxFetcher path.

Cars.com (Cloudflare) blocks curl with the same headers + HTTP/2 we
use in scripts/hydrate.py — the TLS fingerprint (JA3) differs between
curl and Python's httpx, and Cloudflare's bot-detection blocklists
curl's JA3 more aggressively than httpx's. For selector-debugging we
need a real HTML body, and the only client that gets through is the
one already wired into the pipeline.

This script just wraps HttpxFetcher.get + writes to disk. Not part of
the production pipeline — call it manually when iterating on selectors.

Usage:
    python -m scripts.dev_capture_html URL OUTPUT_PATH

Example:
    python -m scripts.dev_capture_html \\
        "https://www.cars.com/vehicledetail/5b475d0d-b34a-40b6-b372-83469b4b7655/?aff=acqem100&emc=acqem100" \\
        scripts/tests/fixtures/cars_com_listing_2026-05-21.html
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from .hydrate import HttpxFetcher, HydrationError


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if len(sys.argv) != 3:
        print(
            "Usage: python -m scripts.dev_capture_html URL OUTPUT_PATH",
            file=sys.stderr,
        )
        return 2

    url, out_path = sys.argv[1], Path(sys.argv[2])
    fetcher = HttpxFetcher()
    try:
        html = fetcher.get(url)
    except HydrationError as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        return 1
    finally:
        fetcher.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Saved {len(html):,} bytes to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
