# Mercedes Sentinel

Autonomous franchise-dealer monitor for a used Mercedes-Benz GLS, model year 2024 or newer. Polls Mercedes-Benz USA's inventory API plus dedicated saved-search alerts in Gmail every afternoon, extracts candidates, scores each against a tight buyer spec via Claude (Sonnet 4.6), and emails a structured daily summary. Designed for a single buyer with a hard deadline and no time to manually scan inventory across multiple sources.

## What this is

A personal automation, not a public skill. The system runs on one Mac mini, against one Gmail label, for one buyer's spec — narrow on purpose. It exists to compress the daily 15-minute manual workflow of "open three tabs, check for new listings, judge each one" into a 30-second email Craig can read while leaving the office.

The forked Facebook Marketplace skill ([pjdoland/used-car-finder](https://github.com/pjdoland/used-car-finder)) provided the original judgment-framework scaffolding. The Marketplace ingestion path, curbstoner detection, and multi-make reliability heuristics were all gutted; what remains is the rubric structure repurposed for franchise-dealer GLS shopping.

## The driver

Third child due October 2026. Current household fleet (2022 Rivian R1T + 2021 Porsche Macan S) does not seat three kids. A 7-seat or 6-seat-captain's-chairs GLS must be in service before the due date. Working backward: the serious buy window closes late August 2026 to allow PPI, financing, and out-of-state transport if needed. The system exists to make sure no eligible candidate slips by during that window.

## Spec

Captured authoritatively in [`CONTEXT.md`](./CONTEXT.md). Summary:

- **Vehicle:** Mercedes-Benz GLS, model year 2024+ (verified via VIN position 10).
- **Trim:** GLS 580 (V8) preferred. GLS 450 (I6) acceptable only when priced ≥ $15K below comparable 580s.
- **Seating:** 7-seat bench OR 6-seat captain's chairs both qualify; 7-seat is the tiebreaker at equal ask.
- **Color:** Blue family — Emerald Green Metallic, Twilight Blue Metallic.
- **Geography:** 250-mile hard cap from 22180 (Vienna, VA). Beyond 250 → auto-Pass.
- **Mileage:** ≤ 40,000.
- **Title:** Clean only.
- **CPO:** Mercedes-Benz Certified Pre-Owned strongly preferred.

## How it works

Three logical layers, each invoked daily by launchd at 4 PM ET:

**C1 — Ingest.** [`scripts/ingest.py`](./scripts/) pulls candidates from two streams on every run:

1. **Mercedes-Benz USA inventory API** (primary). [`scripts/mbusa_inventory.py`](./scripts/) queries `nafta-service.mbusa.com/api/inv/v1/...` for current matching CPO inventory (2024+ GLS 450/580, blue/green, within driving distance of 22180). Records that pass the CONTEXT.md hard caps (≤250 mi, ≤40k mi, year≥2024) are queued with `source: "mbusa"`.
2. **Authorized email alerts** (secondary signal). Polls the `MB-Sentinel` Gmail label via IMAP; dispatches each unread email to a provider-specific parser (Cars.com, AutoTrader, CarGurus, or regex fallback). Cars.com emails contribute price-drop trajectory signal — [`scripts/email_signal_matcher.py`](./scripts/) joins each signal to a same-run MBUSA candidate by `(year, trim, mileage ±500 mi, price ±$2,000)` and attaches the price-drop delta to the matched VIN's history. AutoTrader and CarGurus emails continue to flow directly into the queue as candidates (they include VINs in the alert body, no fuzzy-match needed).

The dedup gate is metadata-aware — when CarGurus re-surfaces a known VIN with a price drop, the changed metadata triggers re-triage rather than getting silently filtered.

**C2 — Triage.** [`scripts/triage.py`](./scripts/) drains the queue and sends each candidate to Claude (Sonnet 4.6) with the full project rubric (CONTEXT.md + four references files) inlined into a cached system prompt. Claude returns a structured verdict via a forced tool-use schema: `ACTION` (worth contacting the dealer), `PASS` (not worth pursuing), or `NEEDS_HUMAN` (data missing or ambiguous, escalate). Verdicts land in `data/triaged.json` as an append-only history.

**C3 — Schedule + notify.** [`scripts/daily.py`](./scripts/) is the orchestrator launchd invokes at 4 PM ET each day. It runs ingest → triage → email summary in sequence. Partial failures are tolerated (failed ingest doesn't block triage; failed triage still produces an email reporting the failure). The summary email lands by ~4:01 PM with subject `[Sentinel] DATE — N ACTION, N NEEDS_HUMAN, N PASS` and a plaintext body covering every verdict produced today.

After installation, the system runs itself. No manual invocation required.

### Architecture history

The current architecture is the result of a May 2026 pivot. The original cars.com hydration path (fetching listing pages to extract VINs) was blocked by Cloudflare's bot-detection escalation. The MBUSA-primary architecture is documented in [`MBUSA_PIVOT.md`](./MBUSA_PIVOT.md) — that doc captures the diagnostic story, the API contract, the schema migration, and the commit-by-commit build sequence. Worth reading if you're picking up the project after a break.

## Setup

See **[`scripts/README.md`](./scripts/README.md)** for the full installation guide — Gmail app password, `.env` config, Python venv, launchd job, and the `pmset` scheduled-wake command. Five steps end-to-end.

## Layout

```
README.md                  this file
CONTEXT.md                 authoritative buyer spec
WORKSPACE.md               operating rules (sanctioned sources, secrets stay out of git, etc.)
CLAUDE.md                  Claude instructions for working on this project
MBUSA_PIVOT.md             May 2026 architecture pivot — decision doc + build log
NEXT_VEHICLE_HANDOFF.md    bootstrap doc for cloning the pattern for vehicle #2 (C6 Corvette)
SKILL.md                   skill manifest (legacy from fork; activates for manual queries)
LICENSE                    MIT, inherited from upstream fork

scripts/                   the autonomous pipeline
  README.md                full setup + run-mode documentation
  ingest.py                C1 — MBUSA poll + Gmail poll + parse + dedup + queue
  mbusa_inventory.py       C1 — MBUSA inventory API client (pagination, retry, jitter)
  email_signal_matcher.py  C1 — fuzzy-match cars.com EmailSignals to MBUSA candidates
  triage.py                C2 — Claude API + tool-use verdict
  daily.py                 C3 — daily orchestrator
  notify.py                C3 — email builder + Gmail SMTP
  state.py                 JSON I/O for seen-vins / queue / triaged; schema-v2 migration
  mail.py                  Gmail IMAP context manager
  llm.py                   Anthropic client + prompt assembly
  dev_capture_api.py       dev-only tool: ad-hoc MBUSA API capture for recon
  parsers/                 per-provider email parsers + regex fallback
  prompts/                 triage prompt template + tool-use schema
  tests/                   200+ unit tests, all mocked, no network access
  requirements.txt         python-dotenv + beautifulsoup4 + anthropic + httpx + h2

launchd/                   macOS scheduling
  com.craigpoland.mercedes-sentinel.plist
  install.sh               copy plist + launchctl bootstrap + print pmset instructions
  uninstall.sh             symmetric teardown

references/                buyer's playbook (loaded by triage AND used manually)
  dealer-tier-list.md         dealers within 250 mi, by drive time
  gls-trim-decoder.md         VIN positions + data card workflow
  mbusa-cpo-criteria.md       CPO eligibility + warranty math + verification
  comp-pricing-framework.md   trailing-90d valuation methodology
  carfax-reading.md           Carfax red flags for 2024+ GLS
  negotiation-framework.md    franchise-dealer negotiation playbook
  trim-id-guide.md            photo-based GLS option verification

data/                      runtime state (gitignored except .gitkeep)
  seen-vins.json              dedup memory with per-provider metadata snapshots
  queue.json                  FIFO of candidates awaiting triage
  triaged.json                append-only verdict log
```

## Operating rules

Captured in [`WORKSPACE.md`](./WORKSPACE.md). The non-negotiable ones:

- **Two sanctioned data sources, nothing else.** The MBUSA inventory API (consumer-facing, Akamai-cached, no auth) and authorized email alerts (Gmail label polling). No Facebook Marketplace, no Playwright, no browser automation against dealer sites, no TLS-fingerprint impersonation. Provider TOS and IP-block risk are the reasons; legal cleanliness is the third.
- **Secrets stay out of git.** All credentials live in `.env` at repo root, which is gitignored. `.env.example` documents the required keys.
- **Never delete files without explicit permission.** Renames and rewrites are fine; deletions require a yes.
- **Preserve the upstream LICENSE.** The fork is MIT; the LICENSE file remains intact crediting pjdoland.

## Scope

In scope: monitoring franchise-dealer inventory for one specific vehicle spec, in one specific geographic region, for one specific buyer with a hard deadline.

Out of scope: anything generalizable. This is a single-buyer, single-vehicle automation. The patterns are reusable; the configuration is not.

## License

MIT, inherited from the upstream fork. See [`LICENSE`](./LICENSE).

## Acknowledgments

Forked from [pjdoland/used-car-finder](https://github.com/pjdoland/used-car-finder). The judgment-framework scaffolding (verdict tiers, rubric layout, references/ structure) is theirs. The franchise-dealer ingestion pipeline, GLS-specific spec, Claude-API triage layer, and launchd scheduling are this fork's additions.
