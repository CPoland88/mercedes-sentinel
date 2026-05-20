# Real-email fixtures (gitignored)

This directory is for real `.eml` samples saved from your Gmail
`MB-Sentinel` label. They are used to exercise the per-provider parsers
against actual alert formats (which evolve over time as Cars.com,
AutoTrader, and CarGurus tweak their templates).

## Why these are gitignored

Real alerts contain dealer-identifying data (specific dealership names,
sales-rep contact info, VINs of vehicles you may be negotiating on).
None of that needs to be in a public GitHub fork. The `.gitignore` at
the repo root excludes `scripts/tests/fixtures/*.eml` for this reason.

## How to add a sample

1. In Gmail, open one of the alert emails routed to `MB-Sentinel`.
2. Click the three-dot menu (top right of the message) → **Download
   message**. Gmail saves an `.eml` file.
3. Move it into this directory with a descriptive name:
   - `cargurus_great_deal_580.eml`
   - `cars_com_fair_deal_450.eml`
   - `autotrader_new_match.eml`
4. Run the ingester in fixture mode:

   ```bash
   python -m scripts.ingest --fixtures scripts/tests/fixtures -v
   ```

   This parses each `.eml` without touching IMAP and without writing
   state. The logger prints provider, VIN, listing URL, and metadata
   per candidate so you can verify the parser handled the alert
   correctly.

## When to add fixtures

Add a sample any time:

- A parser misses a field that's clearly in the email.
- A provider changes its template and metadata regex stops matching.
- You want a regression test for a specific edge case (e.g., an alert
  with two vehicles in one email, or a price written `$87.5k` instead
  of `$87,500`).

If you want a fixture-driven unit test (rather than just CLI
verification), add a `test_*.py` that loads the fixture via
`Path(__file__).parent / "fixtures" / "name.eml"` and asserts on the
parsed output. Mark such tests with a skip-if-missing guard so the
test suite still passes on a clean clone without fixtures present.
