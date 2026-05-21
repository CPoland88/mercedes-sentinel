# CONTEXT.md — Mercedes Inventory Sentinel

Single source of truth. Cowork reads this before every task. Edit the
`[CONFIRM]` fields once, then leave this file authoritative.

## Mission

Monitor franchise-dealer inventory for a used **Mercedes-Benz GLS, model
year 2024 or newer**. Surface actionable listings as they come online.
Score every candidate **Action / Watch / Pass** with a one-line rationale.

This is a **market-monitor against a tight spec**, not a scam filter.
The forked skill's curbstoner / Marketplace logic is being gutted —
see WORKSPACE.md.

## The Driver (hard timeline)

- Third child — **boy, due October 2026**.
- Current fleet (**2022 Rivian R1T**, **2021 Porsche Macan S**) does
  not seat a three-kid household.
- Vehicle must be **in service before the due date**.
- Working backward: serious buy window closes **late August 2026** to
  allow PPI, financing, and out-of-state transport if the car is remote.

## Vehicle Spec

### Non-negotiable

- **Model year:** **2024 or newer.** Verified via VIN position 10
  (`R` = 2024, `S` = 2025, `T` = 2026, and forward per FMVSS 565).
  Pre-2024 X167 cars (MY2020–2023) are out of scope.
- **Model:** Mercedes-Benz GLS
- **Trim:** **GLS 580 (4.0L V8 biturbo + EQ Boost, ~510 hp)** is the
  preferred default. GLS 450 (3.0L I6 turbo + mild hybrid, ~375 hp)
  is the alternative only when its ask is **≥ $15K below the
  comparable 580** — see Economic frame below.
- **Seating:** Either **7-seat (2nd-row bench)** or **6-seat (2nd-row
  captain's chairs)** passes the gate. **7-seat bench is the
  tiebreaker at equal ask.** Dealer listing data is unreliable on
  this — verify from photos and VIN/build, never from the listing's
  seating field alone.
- **Exterior:** Blue. Acceptable factory colors: **Emerald Green
  Metallic, Twilight Blue Metallic, MANUFAKTUR Signature Ireland
  Mid Green Metallic**.

### Economic frame

- **Katie strongly prefers the 580.** The V8 + standard upgraded
  suspension (AMG Line + Air Body Control on the 580 vs base
  AIRMATIC on the 450) make a meaningful day-to-day quality-of-
  life difference for her use case. **Treat 580 as the default
  Action candidate** when all other CONTEXT criteria pass.
- **The 450 is considered only on a striking deal.** Specifically:
  the candidate 450's ask must be **≥ $15K below the comparable
  580 ask** (similar mileage, trim, options, CPO status) to compete
  with the preference for the V8 platform. 450 candidates that
  don't clear the $15K trigger are Pass by default — not because
  they fail any other CONTEXT criterion, but because the 580 wins
  on Katie's QoL frame at any price gap below the trigger.
- 5-year TCO delta (fuel, insurance, tires, depreciation) favors
  the 450 by roughly $25K. The $15K acquisition discount + ~$25K
  TCO savings together meaningfully outweigh the QoL upgrade — at
  smaller gaps, they don't.
- Target **Mercedes-Benz Certified Pre-Owned (CPO)** where possible.
  Any 2024 or newer GLS sits well inside the CPO window (≤ 6 model
  years / ≤ 75K mi per `references/mbusa-cpo-criteria.md`). CPO
  extends comprehensive warranty and signals dealer-vetted condition
  — on non-CPO candidates, quantify the foregone warranty value as
  a negotiation lever.

### Thresholds

| Field | Value |
|:--|:--|
| Price ceiling — 580 (preferred default) | **$95,000 target (soft)**; effective ~**$105,000 cap** when pricing/options/CPO are clearly exceptional. Preserves financial discipline without forcing a hard wall. |
| Price ceiling — 450 (alternative only) | **$80,000** hard cap, AND the candidate must clear the **≥ $15K below comp 580** trigger (per Economic frame above). Otherwise Pass. |
| Mileage ceiling | 40,000 |
| Search radius | **~250 mi drive-able from Vienna, VA 22180 (612 Center St) — hard cap.** Tier A (≤60 mi), Tier B (60–150 mi), and Tier C (150–250 mi, escalation only) per `references/dealer-tier-list.md`. **>250 mi: auto-Pass** regardless of price/options — not worth the flight or week-long transport for inventory that turns up closer to home with regularity. |
| Title | Clean only — branded / salvage / lemon = auto Pass |
| Accident history | No structural or airbag-deployment events |
| Owner count | Single or low; flag fleet/rental history |

### Packages

GLS option groups that matter for this build (the package set is
stable across MY2024 and MY2025; verify per-candidate against the
window sticker / data card).

- **Pinnacle trim** (vs. Premium / Exclusive) — **Must-have**
- **Executive Rear Seat Package** — heated/ventilated/reclining rear
  captain's chairs, rear console; the Plus variant bundles the MBUX
  Rear Tablet — **Nice-to-have** (only applies to the 6-seat variant)
- **Driver Assistance Package** — **Nice-to-have**
- **Acoustic Comfort Package** — **Must-have**
- **Warmth & Comfort Package** — **Must-have**
- **Burmester 3D surround** — Nice-to-have
- **Air Balance / cabin fragrance** — Indifferent
- **Trailer hitch** — Indifferent

Quantify package deltas in **dollars vs. median comp** for negotiation
prep (e.g. "this 450 carries ~$4,200 more factory options than the
median comp at the same ask").

## Live Candidates (as of project start)

Track these against the same scoring rubric so the skill is calibrated
on real cars from day one.

- **GLS 450 — Fredericksburg, VA dealer** (VIN `4JGFF5KE0SB######`).
  **Pass per end-to-end calibration test** — three CONTEXT failures
  (off-spec Obsidian Black Metallic color, Premium trim not Pinnacle,
  Burmester claim contradicted by listing speaker count). Kept here
  as the calibration anchor; not a live pursuit.
- **GLS 580 — Midlothian, VA dealer** — **SOLD (no longer available).**
  Kept here as a marker of the first 580 candidate the project
  tracked; not a live pursuit.

Calibration-only (not live pursuits):

- **GLS 580 — Mercedes-Benz of White Plains, NY** (VIN
  `4JGFF8FE1RB057816`). 2024, $87,770 total, 13,872 mi, blue,
  likely Pinnacle, 7-seat bench, all CONTEXT must-have packages
  present. **Sold pending** at time of evaluation and **256 mi
  out** (past the 250-mi cap → auto-Pass on geography). Used as
  the calibration anchor for the inverted 580-preferred posture.

`[Add VIN, mileage, ask, package list, CPO status as live candidates appear.]`

## Sources (priority order)

1. **Saved-search email alerts** — Cars.com, AutoTrader, CarGurus.
   Primary ingestion path. No scraping.
2. **MBUSA inventory locator / CPO search** — authoritative for CPO.
3. **Reputable dealer groups, ~250-mi radius** — monitored directly.
   See `references/dealer-tier-list.md`.

Do **not** build a Facebook Marketplace or Playwright scraping layer.
Out of scope.

## Scoring Rubric (target behavior)

For each listing the skill should:

1. **VIN-decode** to verify actual build — never trust dealer-entered
   options or seating fields.
2. **Confirm seating config** (7-seat bench or 6-seat captain's
   chairs) from photos + build. Neither found = Pass. 7-seat is the
   tiebreaker at equal ask.
3. **Comp the ask** against trailing ~90-day market (CarGurus IMV as
   the clean free signal; note when an instrument is missing).
4. **Flag CPO status** + remaining factory warranty math.
5. **Score:** Action / Watch / Pass, one-line rationale.
6. On **Action**: produce a defect/option-anchored negotiation brief.

## Out of Scope

- Facebook Marketplace, Craigslist, private-party dynamics.
- Curbstoner / wire-fraud detection (franchise dealers).
- Sub-$15K reliability heuristics from the original skill.
- Any vehicle that is not a Mercedes-Benz GLS, model year 2024 or newer.
