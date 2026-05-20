# Comp-pricing framework — trailing-90d valuation for a 2024 GLS

Comping a 2024 GLS in 2026 has one structural challenge: **the spec
is tight, so the comp set is thin**. CONTEXT narrows the universe to
2024-only, Pinnacle trim, blue-preferred, ~250 mi drive-able. Even
at the national level, this slices into low-volume luxury inventory
where a single platform's "instant market value" can be imputing as
much as it's measuring.

This file gives the skill a defensible methodology: which tools to
trust, how to read them, how to handle thin-comp configs, and how to
plug the CPO foregone-value math from `mbusa-cpo-criteria.md` into
the apples-to-apples comparison.

## CarGurus IMV — primary anchor

**CarGurus Instant Market Value (IMV)** is the default trailing-90d
signal. It's a daily-updated regression over CarGurus's own current
and recently-sold listing inventory across 70+ vehicle data points,
regionally adjusted across 150+ US markets. IMV on a listing
reflects **that listing's local market**, not the shopper's
location — search radius controls which listings you see, not the
comp set powering each IMV.

| IMV property | Reality |
|:--|:--|
| Update frequency | Daily |
| Geographic adjustment | Per-listing, automatic across 150+ markets |
| Comp count behind a specific IMV | **Not exposed in the UI** — known limitation |
| Retail API | None — browser-only |
| Reliability sweet spot | High-volume configs in metro markets |
| Reliability weak zone | Rare trims, low-volume colors, post-MSRP-change windows, recall windows — squarely where a 2024 GLS Pinnacle in a specific color lives |

### Deal-label thresholds (CarGurus does not publish exact cutoffs)

Reverse-engineered directional bands; treat as approximate, not
load-bearing:

| Label | Price vs IMV |
|:--|:--|
| Great Deal | ~10%+ under IMV |
| Good Deal | ~5–10% under IMV |
| Fair Deal | within ~5% of IMV |
| High Price | ~5–10% over IMV |
| Overpriced | 10%+ over IMV |

For verdict-block use: **report the ask as N% under / over IMV in
dollars**, not the CarGurus label. The label hides the underlying
percent and bakes in dealer-reputation weighting we can't see.

## Days-on-lot / days-on-market signals

| Platform | What it shows | Cross-platform aging |
|:--|:--|:--|
| **CarGurus** | Both "days at the dealership" AND "days on CarGurus" (cumulative across rooftops if traded). **Gap between the two is signal** — a big gap means the car has bounced. | Most useful single source |
| **AutoTrader** | "Newly Listed" badge (≤7 days) and "Reduced" badge (≤7 days after a significant cut). No posted-date field. | Weak |
| **Cars.com** | No public days-on-lot field. Deal badges (Great/Good/Fair) shift as prices drop — that's the indirect aging signal. | Weak |

**No reliable consumer-side method to reconcile cross-platform.**
Best heuristic: pull the VIN, check all three sites, take the
**maximum** of (CarGurus days-on-platform, first-seen-on-your-saved-
search date).

### Stale-listing thresholds for a 2024 GLS in 2026

Luxury 3-row SUVs move slower than midsize sedans. Do not apply
30-day stale heuristics from compact-sedan data.

- **<30 days on CarGurus:** fresh; dealer has no pressure
- **30–45 days:** typical age; first dealer cut often lands here (1.5–3%)
- **45–60 days:** aging; second cut common (additional 2–4%)
- **60–75 days:** stale; meaningful negotiation room opens
- **75–100 days:** strong leverage; dealer holding cost ($40–$85/day in interest + insurance + depreciation) is biting
- **100+ days:** maximum leverage; the car is a problem on the dealer's books

These cadences are market-wide averages; calibrate against any
specific dealer's behavior as we observe it.

## Cross-check matrix

When CarGurus IMV is thin or you need a second opinion. Ranking
matters — pick the right tool for the question:

| Tool | Methodology | Retail access | Use when |
|:--|:--|:--|:--|
| **KBB Fair Market Range — CPO Retail tier** | Dealer transactions + auctions + listings + analytics; weekly update; 100+ regions. **Only mainstream tool with an explicit CPO retail band.** | Free, web | **Primary cross-check given the binary CPO posture.** Use the CPO retail range, not private-party or non-CPO dealer-retail. |
| **Cars.com deal badges** | XGBoost regression on 1 yr of used listings; published methodology. List price is NOT a model input (so the badge doesn't circular-anchor). | Free, web | Independent second regression; useful because it's not CarGurus |
| **CarMax instant offer** | Algorithmic; biased toward CarMax inventory need | Free, web | Wholesale-floor anchor for negotiation framing ("this car would fetch $X as trade-in") |
| **Carvana instant offer** | Same model class as CarMax; typically ~$1K below CarMax on SUVs | Free, web | Second wholesale-floor data point |
| **TrueCar** | Dealer-network-driven; pulls from 13K+ certified dealers | Free, web | Cross-check for dealer-side margin and transaction averages |
| Edmunds Suggested Price (formerly TMV) | Transaction-data-driven; weaker for used luxury due to thinner listing inventory | Free, web | Tertiary only; skip if CarGurus + KBB agree |
| AutoTrader "Price Predictor" | Now KBB-backed | Free, web | Redundant with KBB direct |
| Black Book | Dealer/wholesale only | **Not retail-accessible** | Skip |
| Manheim MMR | Auction wholesale only | **Dealer-gated** | Skip |

**Default stack for every serious candidate:**
1. CarGurus IMV (primary)
2. KBB Fair Market Range — CPO tier (CPO cross-check) or non-CPO
   dealer-retail tier (non-CPO cross-check)
3. Cars.com deal badge (second regression)
4. CarMax + Carvana instant offers (wholesale floor for negotiation)

If two of the first three disagree by more than ~5%, the comp set
is thin or the car is mispriced. Investigate before scoring.

## Thin-comp-set failure mode

The CONTEXT spec is genuinely narrow. Expected CarGurus comp counts:

| Filter scope | Approx comp count | Reliability |
|:--|:--|:--|
| 2024 GLS 450 Pinnacle, any color, any seating, ≤40K mi, US-national | 80–150 | Adequate — IMV stable |
| Narrowed to Mid-Atlantic (DC/MD/VA/DE/PA/NJ) | 15–35 | Thin but computable |
| Narrowed to 6-seat captain's chairs only, regional | 3–10 | **Below reliability threshold** |
| Narrowed to 6-seat captain's chairs + specific color, regional | 0–3 | Unusable — IMV is imputing |

When the comp count is visibly thin (no Action verdict if effective
comps < ~10):

1. **Drop the seating filter.** Get IMV on 2024 GLS 450 Pinnacle
   regardless of 2nd-row config. Apply a manual seating premium:
   **6-seat captain's typically commands $500–$1,500 over 7-seat
   bench** in used market. Verify against any active 6-seat
   listings.
2. **Drop the color filter.** Apply a color discount/premium:
   Emerald Green Metallic and Twilight Blue Metallic are low-
   volume; expect **±$0–$1,500 vs Obsidian Black / Polar White**
   (the volume colors).
3. **Pull KBB Fair Market Range — CPO tier** as an independent
   anchor. KBB uses dealer transactions across more channels than
   CarGurus's own listing pool.
4. **Cross-platform aggregation.** Pull AutoTrader and Cars.com
   2024 GLS 450 Pinnacle within 250 mi, hand-build a median ask.
   With CarGurus, that's three independent samples of 5–15 comps
   each.
5. **MSRP-decay curve as last resort.** 2024 GLS 450 Pinnacle
   window-sticker ~$92–98K well-optioned; 2024 GLS 580 Pinnacle
   ~$113–120K. At 18–24 months, luxury 3-rows typically retain
   **62–72% of MSRP** when CPO. That yields a $57–71K envelope for
   the 450 and $70–86K for the 580. Too wide to be the only
   instrument; useful as a sanity check.

Mark the comp confidence in the verdict block's rationale line when
fallback methodology was used. Don't pretend a 3-comp IMV is the
same as a 100-comp IMV.

## Geographic weighting

**Mid-Atlantic price variance vs national: under 1%.** Used GLS
prices are largely nationally set because flatbed transport on a
$70–95K vehicle is $1,000–$1,800 — a tolerable arbitrage cost
relative to the asset price, so dealers and wholesalers move them
across regions.

| Question | Answer |
|:--|:--|
| Default search radius | **250 mi from 22182** (matches Tier A/B in `dealer-tier-list.md`) |
| Set IMV reference geography directly? | **No** — CarGurus computes IMV per listing based on that listing's local market |
| Should we manually re-region IMV? | No — trust each listing's local IMV |
| Mid-Atlantic premium adjustment in the verdict block | **None** |
| When to widen search to nationwide | Thin-comp configs (≤10 comps in 250 mi). Accept that you'll see listings you can't drive to; use the broader comp set to validate the local IMV. |
| Variance threshold worth investigating | More than ~2% deviation between local IMV and national median |

## The comp workflow

For each candidate, run this sequence:

1. **Pull the listing.** Note URL, dealer, ask, mileage, listed
   options, claimed CPO status, days on platform.
2. **Decode the VIN** per `references/gls-trim-decoder.md`. Confirm
   year, engine, plant.
3. **Pull MBUSA window sticker** for the VIN. Get the original
   MSRP and the packages-as-built.
4. **Pull CarGurus IMV** for the listing. Note the IMV, the ask
   delta in dollars and percent, the days on CarGurus, and the
   days-at-dealership gap.
5. **Cross-check KBB Fair Market Range** for the year/trim/miles.
   Pull the **CPO retail** tier if CPO; the dealer-retail tier if
   non-CPO.
6. **Cross-check Cars.com deal badge** for the same VIN if listed
   there, or a comparable in inventory.
7. **Pull CarMax + Carvana instant offers** on the VIN if possible
   (some configs accepted, some not). These set the negotiation
   floor.
8. **Compute the options delta** (next section).
9. **Apply the CPO foregone-value adjustment** if comparing a
   non-CPO candidate against CPO comps (section after next).
10. **Output a fair-value range**, not a point estimate.
11. **Fill the verdict block** with named instruments on every
    numeric field.

## Options-delta math

The verdict block has an "Options delta vs median comp" field. To
fill it, the skill needs MSRP values for each option/package and a
residual-decay multiplier to translate them into 2026 used-market
dollars.

### Known MSRPs for 2024 GLS packages

| Package | Original MSRP (2024 GLS) | Confidence |
|:--|:--|:--|
| Acoustic Comfort Package | $1,100 | High |
| Warmth & Comfort Package | $1,100 | High |
| Driver Assistance Package | ~$1,950–$2,250 | Medium (band, not point — verify per window sticker) |
| Burmester 3D Surround | $4,550 | High |
| Executive Rear Seat Plus (6-seat only) | $3,750 | High |
| Trailer hitch (factory) | ~$550–$650 | Low — verify per window sticker; could be factory pre-wire vs dealer-installed |

**MBUX Rear Tablet** is **not a stand-alone option** on the 2024
GLS — Mercedes consolidated it into Executive Rear Seat Plus (which
is 6-seat only). (CONTEXT now annotates this directly on the
Executive Rear Seat Package line.)

### Residual decay rule

Factory options on luxury SUVs depreciate **faster than the car
itself**. Used-market residual at 18–24 months:

- **Default multiplier: 0.40** (40% of original MSRP)
- **0.45** if the candidate is unusually well-optioned **and** CPO
  (the package mix becomes a marketing asset for the dealer)
- **0.35** if the options are MBUX-tech-heavy (faster-depreciating
  tech relative to interior comfort)

### The formula

```
Options delta vs median comp = sum(per-package MSRP delta) × decay_multiplier
```

Where `per-package MSRP delta` = MSRP of packages on THIS candidate
minus MSRP of packages on the median comp.

### Worked options-delta numerator

Hypothetical: this 450 candidate has Acoustic Comfort, Warmth &
Comfort, Driver Assistance, AND Burmester 3D. The median comp in
the IMV pool has Acoustic Comfort and Warmth & Comfort only.

- This candidate: $1,100 + $1,100 + $2,100 + $4,550 = **$8,850 MSRP**
- Median comp: $1,100 + $1,100 = **$2,200 MSRP**
- Delta: $6,650 MSRP × 0.40 = **+$2,660 used-market value**

Verdict-block line: `Options delta vs median comp: +$2,660`

## CPO foregone-value adjustment (apples-to-apples)

When comparing a **non-CPO candidate** to a CPO comparable, apply
the foregone-CPO adjustment from `references/mbusa-cpo-criteria.md`
**before** running the comp. The adjustment subtracts from the
non-CPO ask:

| Candidate state | Foregone-CPO subtraction |
|:--|:--|
| Low miles (<30K), well inside NVLW window | $1,500–$2,500 |
| Mid miles (30–45K), most of NVLW used | $2,500–$3,500 |
| High miles (45K–75K), at/past NVLW exhaustion | $3,500–$5,000 |
| **Default point estimate when one number needed** | **$3,000** |

Apples-to-apples non-CPO comparable ask = listed non-CPO ask −
foregone-CPO subtraction.

If the non-CPO car is not at least foregone-CPO dollars cheaper
than the CPO comp, the CPO car wins on dollars before any risk
adjustment.

## Worked example — Fredericksburg 450

Using the VIN-decoded data we have (`4JGFF5KE0SB######` = 2024 GLS
450 4MATIC, Tuscaloosa-built). Placeholder rows mark what to
populate when the listing data lands.

```
Listing: [TBD-paste-URL]
Dealer: Mercedes-Benz of Fredericksburg (Tier A, ~55 mi)
Ask: [TBD-from-listing]    Mileage: [TBD-from-listing]
Days on CarGurus: [TBD]    Days at dealership: [TBD]    Gap: [TBD]
CPO claim: [TBD-listing]   CPO verified: [TBD — call 1-800-FOR-MERCEDES with VIN]

CarGurus IMV (this listing's local market):  [TBD-pull]
Ask vs IMV:  [N% under / over]  = $[delta]

Cross-checks:
  KBB Fair Market Range, CPO retail tier (if CPO):  $[low] – $[high]
  KBB Fair Market Range, dealer-retail tier (if non-CPO):  $[low] – $[high]
  Cars.com deal badge:  [Great / Good / Fair / High Price / Overpriced]
  CarMax instant offer:  $[wholesale floor]
  Carvana instant offer:  $[wholesale floor]

Comp count flags:
  [count] CarGurus comps in 250 mi for 2024 GLS 450 Pinnacle
  [count] comps if narrowed to seating-config-match
  Confidence: [High / Medium / Low]
  Fallback methodology applied: [None / dropped-seating-filter / dropped-color-filter / KBB-only / MSRP-decay]

Options analysis:
  Packages on this candidate (from window sticker): [list]
  Packages on median comp (from CarGurus search): [list]
  MSRP delta:  $[delta]
  Decay multiplier:  0.40 (default) / 0.45 / 0.35
  Options delta vs median comp:  [+/-$N]

CPO adjustment (if non-CPO):
  Mileage band:  [low/mid/high]
  Foregone-CPO subtraction:  $[N]
  Apples-to-apples adjusted ask:  $[ask - subtraction]

Trim preference (per CONTEXT economic frame):
  - If THIS is a 580 candidate: preferred default; no trigger check.
  - If THIS is a 450 candidate: verify ask ≥ $15K below comparable
    580 in the local market. Pass if trigger fails (the 580 wins
    on Katie's QoL frame at any smaller gap).

Color note:  CONTEXT-acceptable colors are Emerald Green Metallic
and Twilight Blue Metallic. Confirm exact paint code from window
sticker and flag any deviation on the verdict block.
```

**Next step after pulling the listing and the window sticker:**
fill the placeholders above, then move to the verdict block in
`SKILL.md`'s output format with named instruments on every
numeric field.

## Open calibration items

- **CarGurus comp counts above are field estimates** based on
  CarGurus's aggregate page showing ~3,200 used GLS-Class
  nationally across all years. Real per-filter counts will differ;
  calibrate against actual searches as we run them.
- **6-seat vs 7-seat used-market premium** ($500–$1,500) is
  directional, not measured against 2024 GLS-specific data. Sharpen
  once we observe actual matched-pair listings.
- **Color premium / discount** for Emerald Green Metallic and
  Twilight Blue Metallic relative to volume colors is anecdotal;
  the ±$0–$1,500 band is a placeholder pending real comp work.
- **Driver Assistance Package MSRP** for 2024 GLS specifically was
  not findable in a single authoritative source; the $1,950–$2,250
  band is the typical MB range. Verify per window sticker on each
  candidate.
- **Trailer hitch MSRP** varies materially based on whether it's
  factory pre-wire vs dealer-installed; verify per window sticker.

## Cross-references

- `CONTEXT.md` — thresholds, packages, geography, color
  preferences. The MBUX Rear Tablet line in CONTEXT is technically
  wrong (no longer a stand-alone option on 2024 GLS) but doesn't
  affect scoring.
- `references/gls-trim-decoder.md` — VIN decode and data-card
  workflow. Pull the window sticker before running comp work.
- `references/mbusa-cpo-criteria.md` — CPO verification + foregone-
  CPO dollar math feeding the apples-to-apples adjustment.
- `references/dealer-tier-list.md` — dealer tier drives travel
  cost; for Tier C candidates, add transport cost ($800–$1,800)
  into the comp comparison.
- `references/negotiation-framework.md` *(to be rewritten)* — the
  comp output feeds the negotiation case; CarMax/Carvana wholesale
  floor anchors the offer floor.
