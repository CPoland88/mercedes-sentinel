# Mercedes Sentinel — ingest pipeline

Local automation that polls a dedicated Gmail label for saved-search
alerts (Cars.com, AutoTrader, CarGurus), extracts VINs and listing URLs,
dedups against past sightings, triages each via Claude (Sonnet 4.6)
against the project's living rubric, and emails a daily summary —
running automatically once a day via launchd.

This README documents the complete 3-commit build: C1 (ingest),
C2 (triage), C3 (scheduled daily runner + email summary).

## Architecture

```
scripts/
  ingest.py                  # C1 entry — argparse, run_live, run_fixtures
  triage.py                  # C2 entry — drain queue, call Claude, write verdicts
  daily.py                   # C3 entry — orchestrate ingest + triage + email
  notify.py                  # C3 — build daily summary, send via Gmail SMTP
  mail.py                    # Gmail IMAP context manager
  state.py                   # JSON I/O for seen-vins, queue, triaged
  llm.py                     # Anthropic client + prompt assembly + retry
  parsers/
    __init__.py              # provider detection + dispatch + fallback wiring
    fallback.py              # regex VIN + URL pairing (used when sender unknown
                             #   OR when a provider parser raises)
    cargurus.py              # CarGurus-specific price/IMV/mileage/badge
    autotrader.py            # AutoTrader-specific
    cars_com.py              # Cars.com-specific
  prompts/
    system.md                # triage prompt template (wrapper text)
    triage_tool.json         # tool-use schema for structured verdict output
  tests/
    test_state.py            # state I/O (uses tempdir; never touches data/)
    test_state_metadata.py   # per-provider dedup gate (re-triage logic)
    test_parsers.py          # in-memory synthetic emails
    test_triage.py           # mocked Anthropic client; verdict flow + queue mechanics
    test_notify.py           # mocked SMTP; email format + send
    test_daily.py            # mocked ingest+triage+notify; orchestrator control flow
    fixtures/                # real .eml samples (gitignored)
launchd/
  com.craigpoland.mercedes-sentinel.plist   # the launchd job definition
  install.sh                                # copy plist + launchctl bootstrap
  uninstall.sh                              # bootout + remove plist
data/
  seen-vins.json             # VIN -> first/last seen, per_provider metadata snapshots
  queue.json                 # FIFO of candidates awaiting triage (C2 input)
  triaged.json               # append-only triage verdict log (C2 output)
```

## One-time setup

1. **Create the Gmail app password** (already done; documented here
   for reproducibility on a second Mac):

   - Google Account → Security → 2-Step Verification → App passwords
   - Name: `MB-Sentinel ingest`
   - Save the 16-character string somewhere safe (Apple Keychain is
     fine; it will not be shown again).

2. **Create `.env` at the repo root** by copying `.env.example`
   and filling in real values. `.env` is gitignored; `.env.example`
   is tracked so the required keys are documented.

   ```ini
   IMAP_USERNAME=cpoland06@gmail.com
   IMAP_APP_PASSWORD=xxxxxxxxxxxxxxxx
   ANTHROPIC_API_KEY=sk-ant-...
   ```

   Get an Anthropic API key from
   <https://console.anthropic.com/settings/keys>. You'll also need
   to add a payment method and a starting balance at
   <https://console.anthropic.com/settings/billing> — Anthropic
   no longer auto-grants meaningful trial credits on new accounts.
   $5 is enough for ~100 triage calls; a $20/month spend cap on
   the same page gives a hard wall against runaway usage (realistic
   ongoing spend is well under $5/month at the daily 4 PM cadence).

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

## Triage (C2)

After ingest has populated `data/queue.json`, `scripts/triage.py`
walks the queue and sends each candidate to Claude (Sonnet 4.6) with
the full project rubric — CONTEXT.md plus the four core references
files — inlined into a cached system prompt. Claude returns a
structured verdict via a forced tool-use schema, eliminating
malformed-JSON failures. Verdicts land in `data/triaged.json`.

### Drain the queue

```bash
python -m scripts.triage
```

Processes every candidate in FIFO order. On API failure, the
candidate is re-queued for the next run.

### Triage just one candidate

```bash
python -m scripts.triage --limit 1
```

Useful for sanity-checking output after prompt changes without
burning the rest of the queue.

### Dry-run (no API calls, no state writes)

```bash
python -m scripts.triage --dry-run -v
```

Walks the queue, prints token estimates for the system prompt,
calls nothing. Use this to sanity-check token budget after editing
the rubric. **Note**: dry-run does drain the queue
(pop_from_queue mutates state). Use it only when you're prepared to
re-run ingest.

### Force re-triage of a specific VIN

```bash
python -m scripts.triage --vin 4JGFF8FE2SB431338
```

Re-runs triage against the most recent metadata snapshot for the
named VIN, pulled from `triaged.json`. Verdict history is preserved
— the new verdict is appended, the old one isn't overwritten. Useful
after prompt or rubric tuning.

### Cost notes

Sonnet 4.6 input cost is roughly $3 per million tokens, with cached
tokens billed at 10% of that. The system prompt (template + ~70KB
of rubric) is ~20K tokens; once the prompt cache warms (5-minute
ephemeral cache window), every subsequent triage in a batch pays
~$0.02-0.04. A daily 4 PM run processing 5 candidates is well
under $0.25/day; even a heavy week stays under $2.

### Verdict tiers

- `ACTION` — worth contacting the dealer now. `action_items` contains
  2-4 specific next steps.
- `PASS` — not worth pursuing (wrong spec, out of range, far above
  market, etc).
- `NEEDS_HUMAN` — Claude couldn't decide because key data was missing
  or ambiguous. Manual review needed. **Not** a "middle bucket" —
  borderline candidates that lean either way are pushed to ACTION
  by prompt design.

### Re-triage behavior

The dedup gate in ingest (`state.should_enqueue`) tracks the listing
metadata per VIN per provider. When CarGurus surfaces the same VIN
with a price drop, the new metadata differs from the stored snapshot
and the candidate is enqueued for fresh triage. A VIN that's been
re-triaged multiple times accumulates a verdict history in
`triaged.json` — entries are append-only.

## Scheduled operation (C3)

C3 wires up the daily 4 PM cadence and the email summary. After
installation, the system runs itself — new alerts get ingested,
triaged, and summarized to your inbox without any manual
invocation.

### What runs at 4 PM each day

`scripts/daily.py` is the orchestrator that launchd invokes. It
runs the pipeline in sequence:

1. **Ingest** — poll Gmail's MB-Sentinel label, parse new alerts,
   dedup against `data/seen-vins.json`, enqueue new candidates.
2. **Triage** — drain `data/queue.json`, call Claude per
   candidate, write verdicts to `data/triaged.json`.
3. **Email** — build a plaintext daily summary from today's
   verdicts and send via Gmail SMTP to `EMAIL_TO` (defaults to
   `IMAP_USERNAME`).

Partial failures are tolerated: a failed ingest doesn't prevent
triage from draining yesterday's queue; a failed triage still
produces an email reporting the failure; a failed email is logged
but doesn't lose verdict data (`triaged.json` is the source of
truth).

### Install the launchd job

From the repo root on your Mac mini:

```bash
bash launchd/install.sh
```

The script copies `launchd/com.craigpoland.mercedes-sentinel.plist`
into `~/Library/LaunchAgents/`, loads it via `launchctl bootstrap`,
creates the log directory at `~/Library/Logs/MercedesSentinel/`,
and prints the one remaining manual step.

### Enable scheduled wake-from-sleep

The plist alone doesn't wake the Mac. To make sure the machine is
awake at 4 PM, run (once, prompts for password):

```bash
sudo pmset repeat wakeorpoweron MTWRFSU 15:55:00
```

This wakes the Mac at 3:55 PM every day, 5 minutes before launchd
fires the job at 4:00 PM. The 5-minute headroom ensures network
and DNS are fully online before the script tries to run.

Verify with `pmset -g sched`. Cancel any time with
`sudo pmset repeat cancel`.

### Test the schedule without waiting until 4 PM

```bash
launchctl kickstart gui/$UID/com.craigpoland.mercedes-sentinel
```

Triggers the job immediately. You should receive the daily summary
email within ~30 seconds (assuming Anthropic API + Gmail SMTP are
both reachable).

### Daily summary email format

Subject line carries the headline counts so you can triage from
the lock screen:

```
[Sentinel] 2026-05-21 — 1 ACTION, 0 NEEDS_HUMAN, 3 PASS
```

Body is plaintext (most reliable across mobile clients), organized
as: header → errors (if any, surfaced at top) → ACTION block →
NEEDS_HUMAN block → PASS block → run stats. ACTION verdicts include
the listing URL and 2-4 concrete action items. PASS verdicts get
a one-line reason. The body always shows all three verdict blocks
even when empty, so silence means "checked, nothing matched" rather
than "system didn't run."

### Logs

`~/Library/Logs/MercedesSentinel/run.log` — append-only, captures
both stdout and stderr from the daily run. Tail to watch the next
run live:

```bash
tail -f ~/Library/Logs/MercedesSentinel/run.log
```

### Uninstall

```bash
bash launchd/uninstall.sh
```

Removes the plist and unloads the job. Data and logs are left
intact. To also cancel the scheduled wake, run
`sudo pmset repeat cancel`.

### Run modes for daily.py

The orchestrator can also be invoked manually for testing:

```bash
python -m scripts.daily          # full pipeline + email (what launchd runs)
python -m scripts.daily --no-email  # skip email send (handy when iterating
                                    # on parsers or prompts without spamming
                                    # your inbox)
python -m scripts.daily -v       # verbose / debug logging
```

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
    "per_provider": {
      "cargurus": {
        "first_seen": "2026-05-20T16:00:00-04:00",
        "last_seen": "2026-05-21T16:00:00-04:00",
        "last_metadata": {"price": 89000, "mileage": 5000, "deal_badge": "Great Deal"},
        "listing_urls": ["https://www.cargurus.com/Cars/4JGFF8FE2SB431338"]
      },
      "cars_com": {
        "first_seen": "2026-05-21T16:00:00-04:00",
        "last_seen": "2026-05-21T16:00:00-04:00",
        "last_metadata": {"price": 89500, "mileage": 5000, "deal_badge": "Fair Deal"},
        "listing_urls": ["https://www.cars.com/vehicledetail/...."]
      }
    }
  }
}
```

`mark_seen` is idempotent and accumulates URLs per provider, with the
latest `last_metadata` replacing the prior snapshot. The per-provider
metadata is what powers re-triage on price drops: `should_enqueue`
compares incoming metadata to the stored snapshot and enqueues a fresh
triage when they differ.

### `data/queue.json`

FIFO list of candidate dicts awaiting triage. Each entry carries the
parser output plus a `discovered_at` ISO timestamp. C2's triage script
will `pop_from_queue()` and write verdicts into `triaged.json`.

### `data/triaged.json`

Append-only log of Claude's triage verdicts. Each entry self-contained:

```json
{
  "vin": "4JGFF8FE2SB431338",
  "triaged_at": "2026-05-25T16:05:00-04:00",
  "provider": "cargurus",
  "listing_url": "https://www.cargurus.com/Cars/...",
  "raw_metadata_snapshot": {"price": 89000, "mileage": 5000},
  "discovered_at": "2026-05-25T16:00:00-04:00",
  "verdict": "ACTION",
  "reasoning": "2024 GLS 580 in Pinnacle trim, 78 mi from Vienna at...",
  "key_factors": {
    "trim": "580",
    "model_year": 2024,
    "price": 89000,
    "distance_miles": 78,
    "dealer_tier": "A",
    "cpo_status": "cpo",
    "price_assessment": "below_market"
  },
  "action_items": [
    "Call dealer to confirm captain's chairs in 3rd row",
    "Request the CPO 165-point inspection report",
    "Ask about negotiable extras (mats, ceramic coating)"
  ]
}
```

To get "current verdict for VIN X" filter the list and take the latest.
A VIN that's been re-triaged after price changes accumulates a verdict
history here naturally.

All three files are `.gitignored` — they contain dealer-specific data
that doesn't belong in a public fork.
