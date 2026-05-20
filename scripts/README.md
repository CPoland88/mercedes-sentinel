# Mercedes Sentinel — ingest pipeline

Local automation that polls a dedicated Gmail label for saved-search
alerts (Cars.com, AutoTrader, CarGurus), extracts VINs and listing URLs,
dedups against past sightings, and queues new candidates for downstream
triage.

This README documents C1 (ingest skeleton). C2 will add Claude-API
triage; C3 will add `launchd` scheduling and macOS notifications.

## Architecture

```
scripts/
  ingest.py            # entry point — argparse, run_live, run_fixtures
  mail.py              # Gmail IMAP context manager
  state.py             # JSON I/O for seen-vins, queue, triaged
  parsers/
    __init__.py        # provider detection + dispatch + fallback wiring
    fallback.py        # regex VIN + URL pairing (used when sender unknown
                       #   OR when a provider parser raises)
    cargurus.py        # CarGurus-specific price/IMV/mileage/badge
    autotrader.py      # AutoTrader-specific
    cars_com.py        # Cars.com-specific
  tests/
    test_state.py      # state I/O (uses tempdir; never touches data/)
    test_parsers.py    # in-memory synthetic emails
    fixtures/          # real .eml samples (gitignored)
data/
  seen-vins.json       # VIN → first/last seen, providers, listing_urls
  queue.json           # FIFO of candidates awaiting triage (C2 input)
  triaged.json         # append-only triage results (C2 output)
```

## One-time setup

1. **Create the Gmail app password** (already done; documented here
   for reproducibility on a second Mac):

   - Google Account → Security → 2-Step Verification → App passwords
   - Name: `MB-Sentinel ingest`
   - Save the 16-character string somewhere safe (Apple Keychain is
     fine; it will not be shown again).

2. **Create `.env` at the repo root** (this file is `.gitignored`):

   ```ini
   IMAP_USERNAME=cpoland06@gmail.com
   IMAP_APP_PASSWORD=xxxxxxxxxxxxxxxx
   # C2 will add:
   # ANTHROPIC_API_KEY=sk-ant-...
   ```

3. **Install dependencies in a venv**:

   ```bash
   cd "/Users/craigpoland/Documents/Claude/Projects/Mercedes Sentinel"
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r scripts/requirements.txt
   ```

4. **Verify the Gmail label exists.** The IMAP poller selects label
   `MB-Sentinel` by default. If you renamed the label, update
   `DEFAULT_LABEL` in `scripts/mail.py`.

## Run modes

All commands assume the venv is activated and you're at the repo root.

### Dry-run against live Gmail (safe)

Polls IMAP, parses everything, **does not** mark messages read and
**does not** write to `data/`. Use this to verify parsers work against
your actual alerts before letting the pipeline persist anything.

```bash
python -m scripts.ingest --dry-run -v
```

### Full live run

Polls IMAP, parses, dedups against `data/seen-vins.json`, writes new
candidates to `data/queue.json`, marks Gmail messages as read.

```bash
python -m scripts.ingest
```

### Fixture mode (offline)

Parses every `.eml` in a directory. Skips IMAP entirely. Never writes
state. Use this for parser development and regression testing against
checked-out real samples.

```bash
python -m scripts.ingest --fixtures scripts/tests/fixtures -v
```

See `scripts/tests/fixtures/README.md` for how to add real samples.

## Running the test suite

The tests are pure-Python (`unittest` only; no pytest required). State
tests redirect file paths into a tempdir, so they never touch `data/`.
Parser tests build emails in-memory, so they need no network access and
no real `.eml` fixtures.

```bash
python -m unittest discover -t . -s scripts/tests -v
```

The `-t .` flag is required so unittest treats the repo root as the top
of the package tree — without it, the test modules can't resolve the
`from ..parsers import ...` relative imports.

## State files

### `data/seen-vins.json`

```json
{
  "4JGFF8FE2SB431338": {
    "first_seen": "2026-05-20T16:00:00-04:00",
    "last_seen": "2026-05-21T16:00:00-04:00",
    "providers": ["cargurus", "cars_com"],
    "listing_urls": [
      "https://www.cargurus.com/Cars/4JGFF8FE2SB431338",
      "https://www.cars.com/vehicledetail/...."
    ]
  }
}
```

`mark_seen` is idempotent and accumulates providers + URLs, so the
same VIN appearing on multiple platforms enriches the record rather
than overwriting it.

### `data/queue.json`

FIFO list of candidate dicts awaiting triage. Each entry carries the
parser output plus a `discovered_at` ISO timestamp. C2's triage script
will `pop_from_queue()` and write verdicts into `triaged.json`.

### `data/triaged.json`

Append-only log of Claude's triage verdicts. Written by C2. C1 does not
touch this file.

All three files are `.gitignored` — they contain dealer-specific data
that doesn't belong in a public fork.
