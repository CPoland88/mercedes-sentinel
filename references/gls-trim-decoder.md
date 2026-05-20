# 2024 GLS — VIN decoder and data-card workflow

Most of what you need to score a 2024 GLS candidate (trim level,
packages, color, seating config) is **not** in the VIN. The VIN tells
you year, engine variant, plant, and production sequence — full stop.
Everything else lives on the **data card** (also called the Vehicle
Master Inquiry, VMI, or "VeDoc print") that the dealer can pull from
Mercedes' XENTRY system in 30 seconds.

This file covers both halves: VIN-decode for what is encoded, and the
data-card workflow for everything else.

## Quick reference — what the VIN tells you

Mercedes-Benz VIN is 17 characters. Position-by-position for a US-
spec 2024 GLS (chassis code **X167** — current generation since 2020,
sometimes cited as W167 in older documentation):

| Pos | Value on 2024 GLS | Meaning | Confidence |
|:--|:--|:--|:--|
| 1–3 | `4JG` | WMI: Mercedes-Benz built in Tuscaloosa, AL (also covers GLE and Maybach GLS) | High |
| 4–5 | `FF` | Body series: X167 GLS-Class (long-wheelbase 3-row SUV) | Medium |
| 6–7 | `5K` (450) or `8F` (580) | Engine + drivetrain variant — see Engine table below | High for 450, Medium for 580 |
| 8 | varies | Restraint / market / drive code (encodes 4MATIC + US-market airbag config). MB does not publish the byte legend. | Medium |
| 9 | calculated | Check digit (validates the other 16 per FMVSS 565). Not informational. | High |
| 10 | `R` | Model year 2024. Per FMVSS 565 the 30-year cycle skips I, O, Q, U, Z, 0. Adjacent codes: `P` = 2023, `R` = 2024, `S` = 2025, `T` = 2026. | High |
| 11 | `B` | Plant code: Tuscaloosa. (Older Mercedes US SUV production used `A`; current MY23+ GLS lines show `B`.) | Medium-High |
| 12–17 | numeric | Sequential production number | High |

A clean decode produces: "2024 Mercedes-Benz GLS [450 / 580] 4MATIC,
built in Tuscaloosa, AL, production sequence ######."

## Engine variant — 450 vs 580 from the VIN

Positions 6–7 carry the variant code. The differentiation matters:
the 450 (M256 inline-6 with EQ Boost mild hybrid) and the 580 (M177
biturbo V8 with EQ Boost) are economically distinct cars per
CONTEXT — 5-year TCO delta is ~$25K favoring the 450.

| Pos 6–7 | Variant | Engine | Notes |
|:--|:--|:--|:--|
| `5K` | GLS 450 4MATIC | M256 3.0L I6 turbo + 48V mild hybrid, ~375 hp | Confirmed against multiple real MY24 VINs |
| `8F` | GLS 580 4MATIC | M177 4.0L biturbo V8 + EQ Boost, ~510 hp | MY24 variant code; MY20–MY23 used `8G` |
| `8H` | Maybach GLS 600 4MATIC | Out of scope per CONTEXT.md | — |
| `8K` | AMG GLS 63 4MATIC+ | Out of scope per CONTEXT.md | — |

If positions 6–7 are anything else on a "2024 GLS" listing, the
listing is mislabeled or the VIN is wrong — escalate before scoring.

## What the VIN does NOT tell you

These come from the data card, never from the VIN:

- **Trim level** — Pinnacle vs Premium vs Exclusive
- **Individual package selections** — Acoustic Comfort, Warmth &
  Comfort, Executive Rear Seat, Driver Assistance, Burmester 3D,
  MBUX Rear Tablet, Air Balance, Trailer Hitch
- **Second-row seating configuration** — 7-seat bench vs 6-seat
  captain's chairs (sometimes inferable from variant + standard
  packaging, never guaranteed without the data card)
- **Exterior color** and its factory paint code
- **Interior color and material**
- **Wheel size and style**
- **Standalone options** that do not roll up into named packages

For any of the above, demand the data card.

## Getting the data card (VeDoc / VMI)

Priority order for a pre-purchase, non-owner US retail buyer:

1. **Pull the MBUSA window sticker yourself first.** Free, no dealer
   contact required. `https://www.mbusa.com/en/vehicle-information`
   accepts a VIN and returns the Monroney PDF. Shows packages and
   MSRP, covers the CONTEXT must-haves. Doesn't expose every
   internal SA code. **Default first step for every new candidate.**
2. **Ask the selling dealer's Parts department** (not Sales) for a
   "VeDoc data card print" or "Vehicle Master Inquiry / VMI
   printout." Suggested phrasing:
   > "Can your Parts department pull a VeDoc data card / VMI for
   > VIN ______? I'm evaluating the vehicle for purchase."
   The modern Mercedes dealer system is **XENTRY / VeDoc** (replaced
   the older NetStar / DCS branding). It is at dealer discretion;
   relationship helps. A dealer that refuses without good reason is
   itself a signal — note it in `references/dealer-tier-list.md`.
3. **Third-party Monroney services** ($5–$20) as backup:
   monroneylabels.com, vinanalytics.com, premiumvin.com,
   detailedvehiclehistory.com. Quality varies; many scrape the MBUSA
   tool. Useful when MBUSA's tool errors out on a specific VIN.
4. **MBUSA Customer Assistance** (1-800-FOR-MERCEDES) confirms major
   build info given a VIN but generally won't email a full data card
   to a non-owner. Useful for recall verification.
5. **Mercedes me / owner portal** is owner-only. Skip pre-purchase.

Third-party VIN decoders (mb-decoder, Stat.vin, Bumper,
vindecoderz.com) are good for cross-checking VIN structure but do
not reproduce the dealer-side data card.

## Mapping data-card codes to CONTEXT must-haves

Mercedes uses 3-digit **SA codes** (special-equipment codes) on the
data card. MBUSA does not publish the canonical 2024 tables; the
codes below are compiled from enthusiast wiki sources (MBWorld,
BenzWorld) and dealer Monroney examples. **Treat every code below
"High" confidence as `needs-validation` until you've confirmed it
against the data card for a real 2024 GLS.** Codes rotate
year-to-year.

| Package (per CONTEXT) | Likely SA code | Confidence | Notes |
|:--|:--|:--|:--|
| **Pinnacle trim** (top tier) *— must-have* | `U25` | Low | Often shown as a trim bundle, not a single SA. Likely combined with several `P##` package codes that ship as standard inside Pinnacle. `needs-validation` |
| **Acoustic Comfort Package** *— must-have* | `P64` | Medium | Carried from MY22/23 into MY24 per MBWorld threads. `needs-validation` |
| **Warmth & Comfort Package** *— must-have* | `P65` | Medium | Same provenance as P64. `needs-validation` |
| **Driver Assistance Package** *— nice-to-have* | `P21` (sometimes `23P`) | Medium-High | Stable across MB platforms; verify the MY24 variant (Plus is a different SA) |
| **Executive Rear Seat Package** *— nice-to-have, 6-seat only* | `P50` base / `P52` Plus | Low-Medium | "Plus" adds massage + extended console + door sunshades. `needs-validation` |
| **MBUX Rear Tablet / rear-seat entertainment** *— indifferent* | `873` or `864` | Low | Feature is real on MY24 GLS per MBUSA owner's manual; SA code not publicly cataloged. `needs-validation` |
| **Burmester 3D Surround Sound** *— nice-to-have* | `811` | High | Confirmed in MBWorld threads — 29 speakers, 1,160W. (`810` is the lower-tier Burmester Surround on other MB models.) |
| **Air Balance / cabin fragrance** *— indifferent* | `287` | Medium | Often standard on Pinnacle. If standard, won't appear as a separate line item. `needs-validation` |
| **Trailer hitch** *— indifferent* | `550` (US) or `Q41` (EU) | Low-Medium | `550` is the long-standing MB US-spec trailer-hitch SA. `needs-validation` |
| **7-seat bench** (2nd row) | `U10` or no-cost default | Low | Standard config. `needs-validation` |
| **6-seat captain's chairs** (2nd row) | `U17` | Low-Medium | No-cost option that gates `P50` / `P52`. `needs-validation` |

**Calibration:** when a real 2024 GLS data card is pulled (especially
from the Fredericksburg 450 or Midlothian 580 candidates), promote
the matched codes from `needs-validation` to **High** confidence and
update this table. The first real data card we pull is the
calibration event for the entire reference.

## Quick sanity checks (listing-vs-VIN reconciliation)

Run these on every alert before doing real work:

- **VIN position 10 ≠ `S`** → not a 2024 → auto-Pass per CONTEXT.
- **VIN positions 6–7 ≠ `5K` and ≠ `8F`** → not a US-spec 450 or 580
  → escalate before scoring.
- **VIN positions 6–7 say `8F` but the listing says "GLS 450"** (or
  vice versa) → **the VIN wins**. Demand the data card; the listing
  is wrong about a fundamental fact.
- **VIN positions 1–3 ≠ `4JG`** → not a Tuscaloosa-built US car;
  could be a gray-market import. Escalate.
- **VIN position 11 ≠ `B`** (or rarely `A`) → plant code inconsistent
  with a US-market 2024 GLS. Escalate.
- **Listing mileage < most recent Carfax service mileage** →
  odometer suspect. Cross-reference `references/carfax-reading.md`
  (once rewritten) and walk before contacting the dealer.

## Worked example — Fredericksburg 450 candidate

VIN: `4JGFF5KE0SB######` (production sequence redacted for repo
visibility; full VIN held in session context).

Decode:

- `4JG` → Mercedes-Benz built in Tuscaloosa, AL ✓
- `FF` → X167 GLS-Class ✓
- `5K` → **GLS 450 4MATIC**, M256 3.0L I6 turbo + EQ Boost mild
  hybrid, ~375 hp ✓
- `E` → 4MATIC + US-market restraint config
- `0` → check digit (validates the VIN)
- `S` → **2025 model year** (NOT 2024 — earlier published version of
  this file incorrectly mapped `S` to 2024; per FMVSS 565 the
  correct mapping is `R` = 2024, `S` = 2025, `T` = 2026)
- `B` → **Tuscaloosa** plant ✓
- `######` → production sequence

**Result:** confirmed 2025 GLS 450 4MATIC, US-built, US-market.
Engine and plant clear CONTEXT.md non-negotiables. **Year does
NOT** clear the original CONTEXT spec ("Model year: 2024") and
required a CONTEXT scope decision — see the year-scope widening
commit and CONTEXT.md.

**Still required from the data card** before this candidate can be
scored past Stage 2:

- Trim level (must be Pinnacle per CONTEXT)
- Acoustic Comfort Package presence (must-have)
- Warmth & Comfort Package presence (must-have)
- Second-row seating (7-seat or 6-seat — either acceptable per
  CONTEXT, 7-seat preferred at equal ask)
- Exterior color (CONTEXT lists Emerald Green Metallic or Twilight
  Blue Metallic as acceptable factory colors; user has separately
  noted this candidate is off-spec on color — confirm the exact
  paint code from the data card and flag the deviation on the
  verdict block)
- Package deltas vs the median comp for negotiation prep

**Next step:** pull the MBUSA window sticker for this VIN (Source #1
above). If unavailable or incomplete, request the VeDoc data card
from Mercedes-Benz of Fredericksburg's Parts department using the
phrasing in Source #2. Score the candidate in Stage 3 once the data
card is in hand.
