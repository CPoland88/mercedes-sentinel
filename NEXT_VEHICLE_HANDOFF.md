# Mercedes Sentinel → Next Vehicle Handoff
## Reference architecture and per-vehicle playbook for future car-search clones

A condensed reference for starting a fresh Claude conversation about
cloning the Mercedes Sentinel pattern for the next vehicle pursuit.
Read top-to-bottom — should take about 7 minutes.

---

## TL;DR

- Mercedes Sentinel is shipped and running autonomously at 4 PM ET each day on the Mac mini.
- For each new vehicle: **clone the repo, pick the source mix that fits the vehicle archetype, swap the per-vehicle profile, wire the new primary-source ingest.** Don't build an umbrella architecture until you have 3+ clones to refactor against.
- The infrastructure splits in three tiers: **truly reusable** (state / mail / llm / notify / daily / launchd), **reusable with reshape** (parsers + ingest orchestration, currently shaped for API-primary post-MBUSA pivot), and **per-vehicle** (CONTEXT.md, references, system.md, primary-source client).
- The MBUSA inventory API path is largely Mercedes-specific. Future older / non-CPO vehicle searches will lean on **dealer-aggregator emails + auction emails + forum classifieds** as primary sources — closer to the pre-pivot architecture than the current one.
- Plan: clone for vehicles #2–3, refactor into a `sentinel-core` package once the duplication makes the seams obvious.

---

## What Mercedes Sentinel is (one-paragraph orientation)

Autonomous franchise-dealer monitor for a used 2024+ Mercedes-Benz GLS,
driven by the third-baby deadline of October 2026. Polls MBUSA's
consumer inventory API every afternoon for matching CPO listings,
joins them with price-drop signals extracted from Cars.com / AutoTrader
/ CarGurus saved-search emails, sends each candidate to Claude Sonnet
4.6 with a project-specific rubric for triage, and emails a structured
daily summary categorized as ACTION / NEEDS_HUMAN / PASS. Built across
two architectural eras — email-first (C1/C2/C3) then MBUSA-API-first
(Architecture B pivot, 2026-05-21) — and deployed via launchd. Repo:
`github.com/CPoland88/mercedes-sentinel`. See `MBUSA_PIVOT.md` for the
architectural pivot history.

---

## Architecture today (post-pivot)

Three layers, after the MBUSA pivot.

**Primary candidate stream — MBUSA API.** `scripts/mbusa_inventory.py`
polls the MBUSA inventory JSON endpoint
(`nafta-service.mbusa.com/api/inv/v1/...`) with the SPA's exact query
parameters, returns matching CPO / pre-owned records, and produces a
canonical candidate shape. `scripts/ingest.py` queues these against
`data/seen-vins.json` (schema v2 — per-VIN `email_signals` sub-record).

**Secondary signal layer — email parsers.** `scripts/parsers/`
(`cars_com`, `autotrader`, `cargurus`, `fallback`) extract VIN +
price-drop deltas from saved-search emails.
`scripts/email_signal_matcher.py` attaches these signals to existing
MBUSA candidates by VIN. Emails no longer act as the primary candidate
source — they enrich candidates the API surfaced.

**Triage + notify (unchanged through the pivot).** `scripts/triage.py`
sends queued candidates to Claude Sonnet 4.6 via `scripts/llm.py`, with
`cache_control: ephemeral` on the rubric blocks (CONTEXT.md + four
references files) so re-runs within 5 minutes bill at 10%. Forced
tool-use returns ACTION / NEEDS_HUMAN / PASS verdicts.
`scripts/daily.py` is the launchd-invoked orchestrator;
`scripts/notify.py` builds and sends the daily digest via Gmail SMTP.

**Important framing for future clones:** this API-primary +
email-signal-secondary shape only applies when the manufacturer
exposes a usable consumer inventory API. **For older or non-CPO
vehicles — the future for this project — the more relevant baseline
is the pre-pivot architecture: parsers emit candidates directly,
email is the primary source.** Future ingests will more often look
like commits at or before `f8e753e` than like `951c515`.

---

## The source-pattern taxonomy

Every vehicle pursuit uses some mix of these patterns. Each has
distinct cost, reliability, and architecture implications.

**Manufacturer inventory APIs (MBUSA pattern).** Consumer-facing JSON
the manufacturer's own SPA hits. Validated working for MBUSA. Cost to
add a new one: 1–2 days of recon + client + tests, depending on how
discoverable the parameter contract is. Most relevant only for
newer-vehicle CPO hunts; less applicable to older-vehicle searches
where dealer / private inventory dominates. Architecture slot: primary
candidate stream.

**Dealer-aggregator email alerts (Cars.com / AutoTrader / CarGurus).**
Saved-search digest emails. Cost: ~zero for these three (parsers
exist); ~1 day per new aggregator. Reliability: high — aggregators
want to deliver these. Architecture slot: signal layer in the Mercedes
config; **returns to primary for older-vehicle hunts.** Coverage
caveat: aggregators index dealer inventory broadly but lag private-
party listings.

**Enthusiast auction emails (Bring a Trailer, Cars & Bids).**
Saved-search auction emails. Cost: ~1 day per parser; format diverges
sharply from dealer aggregators. Reliability: high. **Architecture
slot: primary for collector / project-car hunts** where most
interesting inventory transacts through auction sites rather than
dealer lots.

**Forum classifieds (Corvette Forum, Rennlist, AudiWorld, Pelican
Parts).** Vehicle-specific forums where enthusiasts post for-sale ads.
Many forums expose RSS for their classifieds sections. Cost: ~half day
per RSS feed. Scraping is out of scope per WORKSPACE.md. **Architecture
slot: secondary, or primary for niche / model-specific hunts** where
the most knowledgeable sellers cluster.

**Private marketplace (Facebook Marketplace, Craigslist).** Cost: high
— both require browser automation, which is out of scope per
WORKSPACE.md. Status: requires a rule change or manual forwarding to a
monitored Gmail label. Manual forwarding is the only sanctioned path
today; feasible but reduces autonomous-ness. For older / project-grade
vehicles this is often where the cheap finds live, so worth budgeting
for the rule-change conversation when the time comes.

---

## Vehicle archetype taxonomy

How the source mix changes by what you're hunting. Each archetype has
a different reuse rate against the current Mercedes infrastructure.

**Luxury franchise-dealer hunt (Mercedes GLS pattern).** Manufacturer
API primary + aggregator emails secondary. Deadline-driven, low-volume,
dealer-dominated. Highest reuse of current code. **Probably a one-off
for this project given the older-vehicle focus going forward.**

**Enthusiast project car (C6 Corvette, NA/NB Miata, 996/997 911).**
Aggregator emails primary + auction emails secondary. Forum classifieds
become valuable. Private marketplace would help but is out of scope.
No deadline, condition-tolerant, mixed seller types. Requires reshape
work to move parsers back to candidate-emission (~1–2 days).

**Collector / auction-grade (vintage Porsche, R32 GT-R, air-cooled
911, early Land Cruiser).** Auction emails primary (BaT, Cars & Bids),
aggregator secondary, forum classifieds secondary. New parser work for
auction sources (~2 days each). Forum integration likely required.
Comp pricing is harder — auction results matter more than dealer asks.

**Driver-grade muscle / sports (C5 Corvette, S2000, fox-body Mustang).**
Aggregator primary + forum classifieds secondary + private marketplace
if rule changes. Volume is high enough that triage rubric tuning
matters more than source breadth.

---

## What's reusable vs what's per-vehicle

Three tiers, replacing the prior two-tier framing.

**Truly reusable infrastructure (no per-vehicle work).**

- `scripts/state.py` — JSON state schema v2, dedup, per-VIN `email_signals`
- `scripts/mail.py` — IMAP context manager
- `scripts/llm.py` — Anthropic client wrapper, parameterized for multi-profile use (commit `f8e753e`)
- `scripts/notify.py` — email builder + SMTP sender, verdict-agnostic
- `scripts/daily.py` — orchestrator skeleton
- `scripts/parsers/fallback.py` — generic VIN-pattern extraction
- `scripts/prompts/triage_tool.json` — tool-use schema (occasional `key_factors` tweaks per vehicle, but core shape is stable)
- `launchd/` — plist template + install / uninstall scripts
- Test harness scaffolding in `scripts/tests/` — 204 tests at `bb9aa90`, most are reusable

**Reusable with reshape (work required to fit a new vehicle).**

- `scripts/parsers/cars_com.py` — currently emits `EmailSignal` shape (post-MBUSA pivot). For any vehicle without a primary API, either revert to candidate-emission or wrap signals as standalone candidates in `ingest.py`.
- `scripts/parsers/autotrader.py`, `cargurus.py` — same shape question.
- `scripts/email_signal_matcher.py` — architecturally generic but presumes a primary stream exists to match against. Skip entirely for email-primary vehicles.
- `scripts/ingest.py` — orchestration logic is reusable, but the primary-source call is wired to `mbusa_inventory.py`. Swap in the new primary source, or restructure to "parsers-as-primary" if no API exists.

**Per-vehicle (must be rebuilt every clone).**

- `CONTEXT.md` — buyer spec
- `references/*.md` — domain knowledge for the vehicle (trim decoder, condition framework, comp-pricing approach, negotiation framework)
- `scripts/prompts/system.md` — triage rubric tuned to the spec
- Gmail label name (hardcoded in `scripts/ingest.py`)
- `launchd/<name>.plist` — label, log paths, run hour
- `.env` `EMAIL_TO` if different recipient
- **The primary-source client itself** — `scripts/mbusa_inventory.py` is the Mercedes-specific instance of this slot. For a non-API vehicle there is no equivalent module, and the parsers-as-primary path replaces it.

---

## What's already parameterized for umbrella mode

Commit `f8e753e` parameterized three functions in `scripts/llm.py`:

- `assemble_system_prompt(rubric_files=, system_template_path=)`
- `triage(rubric_files=, system_template_path=, model=)`
- `estimate_input_tokens(rubric_files=, system_template_path=)`

Defaults fall back to the module-level constants (`RUBRIC_FILES`,
`SYSTEM_TEMPLATE_PATH`, `DEFAULT_MODEL`), which is the Mercedes
profile. A future umbrella orchestrator can call `triage()` with
per-vehicle overrides without modifying `llm.py`. **The primary-source
layer is the largest unparameterized boundary remaining** — each new
vehicle either gets a new client module or wires parsers as primary in
`ingest.py`. Five tests in `scripts/tests/test_llm.py` lock the
`llm.py` contract.

---

## Why clone, not umbrella

You have exactly one working example. The boundary between
"infrastructure" and "per-vehicle configuration" is only visible after
you build a second one and see what you actually had to change.
Abstracting from one example is guesswork — you'd be inventing
flexibility against problems you haven't seen yet. After two real
builds the duplication becomes obvious and the refactor target writes
itself. Plan: clone for vehicles #2–3, refactor into `sentinel-core`
for #4.

The cost of cloning is low — most of the work for any new vehicle is
the profile content (CONTEXT.md, references, system.md) and any new
primary-source client, both of which would need to be written either
way.

The source-pattern taxonomy above is itself a hint at where the
eventual `sentinel-core` seams will land: primary-source clients slot
behind a common interface, parsers stay as-is, triage and notify stay
reusable, profiles become an injected configuration object.

---

## Universal scoping questions

Apply these to any new vehicle before scaffolding begins. They replace
the prior C6-specific list as the load-bearing pre-build checklist.

1. **Timeline cadence.** Daily (Mercedes pattern, deadline-driven), weekly (passive hunting), event-driven (only ping when a match appears), or dormant (paused while another sentinel runs)?
2. **Source mix.** Which of the five source patterns are in scope? Are new parsers required? Any out-of-scope-today sources worth a rule-change conversation?
3. **Source architecture.** Is there a primary-source API? If not, do parsers emit candidates directly, or do we promote `EmailSignals` to candidates via an adapter? **This is the load-bearing question post-pivot.**
4. **Spec parameters.** Which CONTEXT.md fields apply? Year range, trim, mileage ceiling, price ceiling, color, transmission, condition tolerance, must-have / nice-to-have packages.
5. **Geography.** Radius from home? Willing to fly-and-drive? Same 250-mi cap as Mercedes or different?
6. **Concurrency.** Will this run alongside other vehicle sentinels on the same Gmail account? Same launchd? Different run hours to avoid IMAP collisions?

---

## Worked example — C6 Corvette

The next vehicle Craig is eyeing is a cheap C6 base Corvette (2005–2013)
in driveable, wrap-ready condition, to be wrapped as Lightning McQueen
as a real-world kids' car. **This is one instantiation of the framework
above** — illustrative for future vehicle conversations, not the only
path.

**Archetype:** Enthusiast project car.

**How the universal scoping questions land for the C6 specifically:**

- **Timeline.** No hard deadline. Passive (weekly or every-few-days) is reasonable. Could be dormant until Mercedes is bought to avoid two automations on the same Gmail account.
- **Source mix.** Cars.com / AutoTrader / CarGurus emails (parsers exist); Bring a Trailer + Cars & Bids (each needs new parser, ~1 day each); Corvette Forum classifieds (RSS, half day); Facebook Marketplace where many cheap project cars live but requires WORKSPACE.md rule change or manual forwarding.
- **Source architecture.** No GM equivalent of the MBUSA API in scope. **Parsers-as-primary is the right call.** Reshape `cars_com.py` / `autotrader.py` / `cargurus.py` back to candidate-emission, or write a thin adapter that promotes `EmailSignals` into the candidate queue in `ingest.py`. ~1–2 days of work.
- **Spec parameters (C6-specific decisions still open):**
  - Year / engine range — 2008+ LS3 (sweet spot, more power, costs more) vs. 2005–2007 LS2 (cheapest, early valvetrain quirks).
  - Transmission — manual (more fun) vs. automatic (cheaper, kid-friendlier for parade duty).
  - Hard price ceiling (rough range: $15–25K).
  - Mileage ceiling (LS platform tolerates 100K+ fine).
  - Color irrelevant (wrap covers it).
  - CPO doesn't apply at this age.
- **Geography.** Same 250-mi cap from Vienna VA, or willing to fly-and-drive for the right car?
- **Concurrency.** Different run hour from Mercedes (e.g., 5 PM) to avoid same-Gmail IMAP collisions.

**Things to keep in mind that are NOT obvious from the Mercedes build:**

- The no-scraping rule in WORKSPACE.md was a Mercedes-specific decision driven by franchise-dealer TOS risk. For a C6 hunt, FB Marketplace is genuinely where many cheap project-grade cars live — worth the rule-change conversation explicitly.
- BaT and Cars & Bids both send email notifications for saved searches; format diverges sharply from dealer-aggregator parsers.
- The triage rubric needs new seller-type heuristics — "is this a flipper or an enthusiast?" matters for project-car sellers in a way it doesn't for franchise MB dealers.

**Recommended scope (simplest version — Cars.com + AT + CarGurus only, no BaT / C&B / FB):**

- **Primary-source decision:** parsers-as-primary (no API for GM in scope). Reshape parsers or build `EmailSignal`→candidate adapter (~1–2 days).
- **Profile work:** new `CONTEXT.md` for C6 spec; 2–3 new references files (e.g., `c6-corvette-specifics.md`, `c6-known-issues.md`, `project-car-condition-framework.md`); rewrite `scripts/prompts/system.md` for C6 VIN decode + private-seller-vs-dealer heuristics + verdict definitions tuned to wrap-ready condition rather than CPO eligibility.
- **Deployment:** copy launchd plist with new label, log paths, and a different run hour (e.g., 5 PM). Separate Gmail label. Fresh `data/` directory.
- **New repo:** `github.com/CPoland88/corvette-sentinel` or similar.

If BaT / C&B / forum classifieds are added, budget ~1–2 days per new source.

---

## When to refactor into `sentinel-core`

After two clones the duplication patterns become visible. Likely seams
(best guess from the source-pattern taxonomy):

- **Primary-source interface.** `MbusaInventoryClient`, `BatEmailClient`, `ParserPrimaryAdapter` all conform to a `CandidateSource` protocol returning `Candidate[]`.
- **Vehicle profile object.** `CONTEXT.md` + references + system.md + Gmail label + launchd config become an injectable `VehicleProfile`.
- **Orchestrator generalization.** `daily.py` takes a `VehicleProfile` + `CandidateSource[]` and runs the same ingest → triage → notify pipeline.

Build none of this until clone #2 reveals which of these guesses are
right and which are over-engineered.

---

## Where things live

- **Project root:** `/Users/craigpoland/Documents/Claude/Projects/Mercedes Sentinel`
- **GitHub:** `https://github.com/CPoland88/mercedes-sentinel`
- **Mac mini deployment:** running via launchd at 4 PM ET daily, logs at `~/Library/Logs/MercedesSentinel/`
- **Gmail label currently monitored:** `MB-Sentinel`
- **Test count baseline:** 204 tests, all green at commit `bb9aa90`
- **MBUSA pivot history:** `MBUSA_PIVOT.md` at project root
- **Working partner instructions (`CLAUDE.md`):** "Before any task, read CONTEXT.md and WORKSPACE.md. Propose a plan before editing; never delete files without asking."

---

## How to start the next conversation

In a fresh Claude conversation, attach or reference this file:

> I'm cloning Mercedes Sentinel for a `<vehicle>` pursuit. Read
> `NEXT_VEHICLE_HANDOFF.md` at the project root for the reference
> architecture, then identify the archetype, recommend a source mix,
> and ask me the six universal scoping questions before proposing a
> build plan.

Claude can then read this file, get oriented in ~7 minutes, identify
the archetype, recommend a source mix, ask the universal scoping
questions, and propose a clone plan without rebuilding context from
scratch.
