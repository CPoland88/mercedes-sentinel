# Mercedes Sentinel → Next Vehicle Handoff

A condensed brief for starting a fresh Claude conversation about cloning the
Mercedes Sentinel pattern for the next vehicle pursuit (cheap C6 Corvette to
wrap as Lightning McQueen for the kids). Read top-to-bottom — should take
about 5 minutes.

---

## TL;DR

- Mercedes Sentinel is shipped and running autonomously at 4 PM ET each day on the Mac mini.
- For car #2 (C6 Corvette): **clone the repo, swap the per-vehicle profile, don't try to build an umbrella architecture yet.** Two examples make the refactor target obvious; one example makes it guesswork.
- `scripts/llm.py` was already parameterized in commit `f8e753e` for future umbrella mode — the function signatures accept per-vehicle overrides, defaults preserve current Mercedes behavior.
- Six open scoping questions need answers before scaffolding starts (see [Open questions for the C6 build](#open-questions-for-the-c6-build) below).
- Plan: clone for #2, refactor into a `sentinel-core` package for #3.

---

## What Mercedes Sentinel is (one-paragraph orientation)

Autonomous franchise-dealer monitor for a used 2024+ Mercedes-Benz GLS,
driven by the third-baby deadline of October 2026. IMAP-polls a dedicated
Gmail label every afternoon, extracts candidate listings from saved-search
alerts (Cars.com / AutoTrader / CarGurus), sends each candidate to Claude
Sonnet 4.6 with a project-specific rubric for triage, and emails a
structured daily summary categorized as ACTION / NEEDS_HUMAN / PASS. Built
across three commits (C1 ingest, C2 triage, C3 schedule + notify) and
deployed via launchd. Repo: `github.com/CPoland88/mercedes-sentinel`.

---

## Architecture in three layers

**C1 — Ingest.** `scripts/ingest.py` + `scripts/parsers/` poll the Gmail
label, dispatch each unread email to a provider-specific parser (or regex
fallback), extract VIN/URL/price/mileage/deal_badge, dedup against
`data/seen-vins.json` (metadata-aware — a price drop on a known VIN
re-triggers triage), and queue new candidates in `data/queue.json`.

**C2 — Triage.** `scripts/triage.py` drains the queue and sends each
candidate to Claude (Sonnet 4.6) via `scripts/llm.py`. The system prompt
is assembled by concatenating `scripts/prompts/system.md` with
`CONTEXT.md` and four `references/*.md` files, marked with
`cache_control: ephemeral` so the rubric is cached and billed at 10%
on subsequent calls within the 5-minute window. Forced tool-use
(`scripts/prompts/triage_tool.json`) returns a structured verdict —
`ACTION`, `PASS`, or `NEEDS_HUMAN` — with reasoning, key_factors, and
action_items. Verdicts append to `data/triaged.json`.

**C3 — Schedule + notify.** `scripts/daily.py` is the orchestrator
launchd invokes at 4 PM ET. It runs ingest → triage → email summary in
sequence, tolerant of partial failures (failed ingest doesn't block
triage; failed triage still produces an error email). `scripts/notify.py`
builds the daily digest and sends it via Gmail SMTP. The plist lives at
`launchd/com.craigpoland.mercedes-sentinel.plist`.

---

## What's reusable vs. what's per-vehicle

This is the key distinction for cloning.

**Reusable infrastructure (will not change between cars):**

- `scripts/state.py` — JSON state schema, dedup logic, per-provider metadata snapshots
- `scripts/mail.py` — IMAP context manager
- `scripts/ingest.py` — orchestration logic (Gmail label name is the only customization point)
- `scripts/parsers/cars_com.py`, `autotrader.py`, `cargurus.py`, `fallback.py` — work for any vehicle the dealer/seller lists; not Mercedes-specific
- `scripts/llm.py` — Anthropic client wrapper (now parameterized — see below)
- `scripts/notify.py` — email builder + SMTP sender, verdict-agnostic
- `scripts/daily.py` — orchestrator skeleton
- `scripts/prompts/triage_tool.json` — tool-use schema (may need minor per-car tweaks to `key_factors` fields but the core shape is reusable)
- `launchd/` — plist template + install/uninstall scripts
- Test harness in `scripts/tests/` — 82 tests, mostly reusable; a few assertions check Mercedes-specific strings and would need swapping

**Per-vehicle profile (must be replaced for each car):**

- `CONTEXT.md` — buyer spec (trim, year, mileage, color, geography, price ceiling, deadline)
- `references/*.md` — dealer-tier list, trim decoder, CPO criteria, comp-pricing framework, carfax-reading, negotiation framework
- `scripts/prompts/system.md` — system prompt template containing VIN decode rules, dealer brand examples, verdict definitions tuned to the buyer spec
- Gmail label name (hardcoded in `scripts/ingest.py`)
- `launchd/<name>.plist` — label, log paths, run hour
- `.env` `EMAIL_TO` (if different recipient)

---

## What's already parameterized for umbrella mode

Commit `f8e753e` parameterized three functions in `scripts/llm.py`:

- `assemble_system_prompt(rubric_files=, system_template_path=)`
- `triage(rubric_files=, system_template_path=, model=)`
- `estimate_input_tokens(rubric_files=, system_template_path=)`

Defaults fall back to the module-level constants (`RUBRIC_FILES`,
`SYSTEM_TEMPLATE_PATH`, `DEFAULT_MODEL`), which is the Mercedes profile.
A future umbrella orchestrator can call `triage()` with per-vehicle
overrides without modifying `llm.py`. For the C6 clone (not umbrella),
either edit the module constants in place or leave them and pass
overrides — both work. Five tests in `scripts/tests/test_llm.py` lock
the contract.

---

## Why clone, not umbrella

You have exactly one working example. The boundary between
"infrastructure" and "per-vehicle configuration" is only visible after
you build a second one and see what you actually had to change.
Abstracting from one example is guesswork — you'd be inventing
flexibility against problems you haven't seen yet. After two real
builds the duplication becomes obvious and the refactor target writes
itself. Plan: clone for #2, refactor into `sentinel-core` for #3.

The cost of cloning is low — most of the work for the C6 build is the
profile content (CONTEXT.md, references, system.md), which would need
to be written either way.

---

## The C6 Corvette pivot

**Goal:** Find a cheap C6 base Corvette (2005–2013) in driveable,
wrap-ready condition. Wrap it as Lightning McQueen and use as a
real-world kids' car for parades, school events, weekend fun.

**How this hunt differs structurally from the Mercedes hunt:**

- Market is enthusiast-heavy (Bring a Trailer, Cars & Bids, Corvette
  Forum classifieds, Facebook Marketplace, private listings on
  AutoTrader/CarGurus) — not franchise-dealer-dominated like a $90K
  Mercedes. Chevy dealers carry trade-ins but the deep inventory is
  elsewhere.
- No hard deadline. Passive cadence (weekly or every-few-days) is
  reasonable.
- Condition tolerance is higher. Cosmetic blemishes don't matter
  because you're wrapping over them. Focus shifts to clean title, no
  flood/salvage history, mechanically sound, accident-free
  structurally.
- Color is irrelevant — wrap covers it.
- CPO doesn't apply at this age.
- Price ceiling is much lower (roughly $15–25K depending on year/condition).
- Mileage tolerance is much higher — C6 drivetrains are stout, 100K+
  miles is fine on a clean LS3.
- Year/engine tradeoff: 2005–2007 LS2 is cheapest but has early
  valvetrain quirks. 2008+ LS3 is the sweet spot — more power, more
  refined, costs more. 2013 GS/Z06 is unobtainium at this budget.

**Things to keep in mind that are NOT obvious from the Mercedes build:**

- The "no scraping" rule in `WORKSPACE.md` was a Mercedes-specific
  decision driven by franchise-dealer TOS risk. For a C6 hunt, FB
  Marketplace is genuinely where many cheap project-grade cars live,
  but ingesting it would mean either browser automation (which breaks
  the no-scraping rule) or manually forwarding listings to Gmail
  (which is feasible but reduces the autonomous-ness).
- BaT and Cars & Bids both send email notifications for saved
  searches. Their email formats are very different from the
  dealer-aggregator parsers. Each would need ~1–2 days of parser work
  plus calibration tests.
- The triage rubric needs new dealer/seller heuristics — "is this a
  flipper or an enthusiast?" matters for C6 sellers in a way it
  doesn't for franchise MB dealers.

---

## Open questions for the C6 build

These block scaffolding. Answer in the new conversation before any
code work begins.

1. **Timeline.** Passive (whenever the right one shows up, weekly
   cadence), active 6-month hunt (daily cadence like the Mercedes),
   or dormant until Mercedes is bought (avoids two automations on the
   same Gmail account)?

2. **Listing sources.** Cars.com + AutoTrader + CarGurus only (zero
   parser work), and/or Bring a Trailer + Cars & Bids (each needs a
   new parser), and/or Facebook Marketplace (requires
   browser-automation rule change or manual forwarding)?

3. **Year/engine range.** 2008+ LS3 only, or open to 2005–2007 LS2
   for cost, or specifically targeting a year (e.g., 2008 sweet spot)?

4. **Transmission.** Manual only (more fun), automatic only (cheaper,
   kid-friendlier for parade duty), or either?

5. **Hard price ceiling.** Where does ACTION become PASS on price?

6. **Mileage ceiling.** Where does ACTION become PASS on miles?

A couple of softer questions worth touching on too: target geography
(same 250-mile cap from Vienna VA, or willing to fly-and-drive for
the right car?), and "kid-safety" considerations (e.g., requiring
backseat-deletion-friendly cars, or accepting only cars with no known
airbag recalls open).

---

## Recommended scope for the C6 sentinel (rough, pending answers above)

Assuming the simplest scope (Cars.com + AutoTrader + CarGurus only,
no BaT/C&B/FB):

- **C1 work:** ~zero. Existing parsers work as-is. Point at a new
  Gmail label.
- **C2 work:** Write new `CONTEXT.md` for C6 spec. Write 2–3 new
  references files (something like `c6-corvette-specifics.md`,
  `c6-known-issues.md`, `project-car-condition-framework.md`).
  Rewrite `scripts/prompts/system.md` for C6 VIN decode + private-
  seller-vs-dealer heuristics + verdict definitions tuned to
  wrap-ready condition rather than CPO eligibility.
- **C3 work:** Copy launchd plist with new label, log paths, and a
  different run hour (e.g., 5 PM) so the two pipelines don't collide
  on the same Gmail mailbox.
- **New repo:** `github.com/CPoland88/corvette-sentinel` (or similar).
  Fresh `data/` directory, separate Gmail label, separate `.env` if
  desired.

If Bring a Trailer / Cars & Bids are in scope, add ~1–2 days of
parser work each plus calibration tests.

---

## Where things live

- **Project root:** `/Users/craigpoland/Documents/Claude/Projects/Mercedes Sentinel`
- **GitHub:** `https://github.com/CPoland88/mercedes-sentinel`
- **Mac mini deployment:** running via launchd at 4 PM ET daily, logs at `~/Library/Logs/MercedesSentinel/`
- **Gmail label currently monitored:** `MB-Sentinel`
- **Test count baseline:** 82 tests, all green at commit `f8e753e`
- **Working partner instructions (`CLAUDE.md`):** "Before any task, read CONTEXT.md and WORKSPACE.md. Propose a plan before editing; never delete files without asking."

---

## How to start the next conversation

In a fresh Claude conversation, attach or reference this file:

> I'm cloning Mercedes Sentinel for a C6 Corvette pursuit. Read
> `NEXT_VEHICLE_HANDOFF.md` at the project root for context, then ask
> me the six open scoping questions before proposing a build plan.

Claude can then read this file, get oriented in ~5 minutes, ask the
open scoping questions, and propose a clone plan without rebuilding
context from scratch.
