"""Dev-only tool: capture a JSON API response with browser-XHR headers.

Sibling of scripts.dev_capture_html. Used for recon and selector-design
work against MBUSA's inventory API
(nafta-service.mbusa.com/api/inv/v1/...).

The production HttpxFetcher in scripts/hydrate.py sends headers that
mimic a top-level browser navigation (Sec-Fetch-Mode: navigate,
Sec-Fetch-Dest: document, Accept: text/html, ...). API endpoints often
reject those headers because they expect a browser-XHR pattern
(Sec-Fetch-Mode: cors, Sec-Fetch-Dest: empty, Accept: */*). This
script sends the XHR-pattern headers MBUSA's own SPA sends, with
Origin + Referer set to https://www.mbusa.com.

Usage:
    python -m scripts.dev_capture_api URL OUTPUT_PATH

Example:
    python -m scripts.dev_capture_api \\
        "https://nafta-service.mbusa.com/api/inv/v1/en_us/used/vehicles/search?count=12&distance=ANY&invType=cpo&zip=22180" \\
        scripts/tests/fixtures/mbusa_search_recon.json
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import httpx


API_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://www.mbusa.com",
    "Referer": "https://www.mbusa.com/en/cpo/inventory/search?zip=22180&inventory=cpo",
    "Sec-Ch-Ua": '"Google Chrome";v="126", "Not-A.Brand";v="8", "Chromium";v="126"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Priority": "u=3, i",
}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if len(sys.argv) != 3:
        print(
            "Usage: python -m scripts.dev_capture_api URL OUTPUT_PATH",
            file=sys.stderr,
        )
        return 2

    url, out_path = sys.argv[1], Path(sys.argv[2])

    client = httpx.Client(
        headers=API_HEADERS,
        http2=True,
        follow_redirects=True,
        timeout=httpx.Timeout(connect=15.0, read=30.0, write=15.0, pool=15.0),
    )
    try:
        # Modest jitter so back-to-back manual invocations don't look
        # like a tight scrape loop. One-second floor is enough for ad-hoc
        # exploration without being annoying.
        time.sleep(1.0)
        response = client.get(url)
    finally:
        client.close()

    print(f"HTTP {response.status_code} | {len(response.content):,} bytes")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.content)
    print(f"Saved to {out_path}")

    if response.status_code >= 400:
        print(
            f"WARNING: non-2xx response. First 500 chars of body:\n"
            f"{response.text[:500]}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
