# Mercedes-Benz CPO — criteria, warranty math, and verification

CPO status is one of the biggest single levers on a 2024 GLS
valuation. Per CONTEXT.md, the buyer's policy is **binary: CPO or
nothing.** Any warranty extension happens inside the MB CPO program
(the optional Extended CPO Limited Warranty sold by MB Financial
Services) — never via third-party or separately-purchased non-CPO
warranty products.

This file covers the four things the skill needs to score CPO
correctly on every candidate: who qualifies, what the buyer
actually gets, how to verify CPO status independent of the dealer's
claim, and the dollar math for the foregone-warranty value on a
non-CPO car.

## CPO eligibility window (current as of 2026)

A used Mercedes can be MB CPO-certified only if **all** of the
following are true:

| Criterion | Rule | Confidence |
|:--|:--|:--|
| Max age | ≤ 6 model years from in-service date | High |
| Max mileage | ≤ 75,000 total miles | High |
| Title | Clean only — salvage, rebuilt, flood = auto-exclude | High |
| Lemon buyback / reacquired vehicles | Effectively excluded (MB sells these via a separate program, not CPO) | Medium |
| Fleet / rental / livery / commercial use | Effectively excluded via the service-history gate | Medium-High |
| Service history | Scheduled maintenance per MB intervals; gaps must be cured at the certifying dealer | High |
| Inspection | Must be completed at an authorized MB dealer by MB-trained tech. A third-party PPI does **not** count. | High |

For a 2024 GLS being shopped in 2026, the age and mileage gates are
non-issues — every in-scope car easily clears both. **The binding
constraint at this point in the car's life is history**: title
brand, fleet/rental use, or service gaps. Carfax is the first thing
to pull, before the data card.

## CPO warranty coverage — what the buyer gets

| Item | Coverage | Confidence |
|:--|:--|:--|
| CPO Limited Warranty (base) | **12 months / unlimited miles**, beginning at NVLW expiration | High |
| Underlying NVLW (carries over) | 4 yr / 50K mi from in-service date | High |
| Separate powertrain extension | **None** — MB does not match Lexus's 7yr/100K powertrain layer | High |
| Deductible | **$0** per visit | High |
| Transferability | Yes, free, to a private buyer for remainder of term | High |
| Optional Extended CPO Limited Warranty | **+1 yr or +2 yr / unlimited miles**, sold by MB Financial Services as an add-on at point of CPO sale or during the base CPO LW period. **In-scope per CONTEXT — this is the user's only sanctioned warranty-extension path.** | High |
| Roadside assistance | 24/7 for life of warranty (jump, tire, fuel, tow) | High |
| Trip interruption | Up to **$300/day for 3 days** ($900 max) if disabled more than 100 mi from home | Medium-High |
| Loaner / rental during repair | **NOT a guaranteed program benefit** — dealer courtesy only, do not promise it on a verdict | Medium-High |
| Carfax | Included | High |
| SiriusXM trial | 3-month complimentary | Medium |
| 7-day / 500-mi exchange | Yes, for another CPO unit at the same dealer | High |

**Coverage exclusions (standard wear-and-tear):** brake pads, brake
rotors past wear limit, wiper blades, tires, glass, body panels,
paint, upholstery, 12V battery (often pro-rated separately), bulbs,
fuses, alignment, cosmetic trim. The CPO LW mirrors NVLW's covered-
component list — major mechanical and electrical, not consumables.

## The 165-point inspection — scope

MBUSA's current wording is **"165+ points"**. The "+" exists because
additional EV-specific items have been added on top of the core 165;
for an ICE 2024 GLS (450 I6 or 580 V8), think of it as the standard
165 across these categories:

- **Road test** — drivetrain behavior, transmission shifts, brake
  feel, NVH, HVAC under load, electronics in motion
- **Under-hood mechanical** — engine, cooling, fuel system, belts,
  mounts, fluids, leaks, emissions
- **Underbody** — suspension, steering, exhaust, driveline,
  frame/structure integrity
- **Brakes** — pads, rotors, lines, parking brake
- **Tires and wheels** — tread depth, wear pattern, DOT date, OEM
  spec confirmation
- **Electrical and electronics** — battery, alternator, lights,
  infotainment, MBUX, cameras, ADAS calibration, all switches
- **Body and paint** — panel gaps, paint thickness, glass, trim,
  structural integrity
- **Interior** — seats, belts, headliner, controls, climate, even
  "scent and moisture"
- **Documentation** — service history, recalls performed, key count,
  owner's manual present

The signed-off document is the **CPO Inspection and Certification
Report** (also "CPO certification form" or "check sheet"). It is
dated and names the certifying dealer code plus the technician.

**Reasonable expectation:** the dealer hands the buyer a copy of
this report **before money changes hands**. A dealer who says
"we'll send it later" is the most common cover for a not-yet-
completed inspection on a car listed and marketed as CPO. Treat
"we'll send it later" as a red flag, not a logistics quirk.

Expected bay time: 3 to 6 hours including road test. (MBUSA doesn't
publish a precise number; this is anecdotal from dealer service
departments.)

## How to verify CPO status independent of the dealer's claim

Treat every dealer "CPO" claim as a hypothesis. Confirm via at
least one channel below before treating CPO as load-bearing on a
verdict.

1. **MB Customer Assistance Center (1-800-FOR-MERCEDES /
   1-800-367-6372).** Single most authoritative channel. Call with
   the VIN, ask whether the car has been certified and the CPO
   warranty has been registered against the VIN. A non-owner can
   make this call. *(Forum-reported as reliable; not promised in
   writing by MBUSA, so confidence: Medium-High.)*
2. **MBUSA CPO inventory search** at
   `https://www.mbusa.com/en/cpo/inventory`. A VIN appearing here
   means the dealer has uploaded the car into the CPO feed —
   **necessary but not sufficient**. This is the dealer's own
   self-assertion of certification, surfaced through MBUSA's site,
   not an independent MBUSA verification.
3. **Signed CPO Inspection and Certification Report** from the
   selling dealer. The formal document, dated and signed. Ask for
   it pre-deposit; the dealer who can't produce it pre-deposit
   hasn't done the work.
4. **Second MB dealer's service department.** Any MB dealer's
   service department can pull the VIN in MB's national service
   system and tell you whether a CPO warranty contract has been
   registered against it. Useful when shopping a dealer you don't
   trust — call a different MB dealer in the area as a sanity check.
5. **MBUSA window-sticker tool** at
   `https://www.mbusa.com/en/vehicle-information`. **Does NOT
   reliably flag CPO status** — CPO is post-sale metadata, not part
   of the original build record. Useful for the data-card pull
   workflow (see `gls-trim-decoder.md`), not for CPO verification.

**The trick this defeats:** dealer lists car as CPO and prices it
as CPO; inspection hasn't actually been completed; if the deal
closes, the dealer rushes the inspection (or skips items); if the
deal falls through, they de-list and re-list it as non-CPO at a
lower price. Defense: insist on the signed Inspection and
Certification Report **before deposit** and cross-check the VIN
with the Customer Assistance Center.

## The CPO valuation math

Per CONTEXT, the verdict block carries a `CPO:` field. When CPO is
**Yes**, fill the remaining warranty months. When CPO is **No**,
quantify the foregone-warranty value in dollars.

### When CPO is Yes — remaining warranty math

Compute two numbers and pick the later one as the warranty cliff:

- **NVLW expiration date** = in-service date + 48 months
- **NVLW expiration on miles** = car hits 50,000 miles (pull from
  Carfax service records to project)
- **CPO LW expiration date** = NVLW expiration date + 12 months
  (unlimited miles)

The CPO LW starts when NVLW expires (date or mileage, whichever
comes first), and runs 12 months from that point. For the verdict
block:

```
CPO: Yes — NVLW exp [date / mi], +12 mo CPO LW to [date]
```

If the buyer is considering the Extended CPO LW add-on (+1yr or
+2yr), note it as a follow-on decision, not part of the candidate's
baseline CPO valuation.

### When CPO is No — foregone-warranty value math

The buyer is forfeiting:

1. The 12 months / unlimited miles of CPO LW coverage
2. The dealer-conducted 165-point inspection (out-of-pocket cost to
   replicate via independent PPI: $200 to $400 at an MB specialist)
3. Roadside, trip interruption, and the 7-day/500-mi exchange
4. Access to the Extended CPO LW add-on path (you cannot buy the
   Extended CPO LW on a non-CPO car)

**Dollar anchor:** $2,500 to $4,000 directional range for the
foregone-CPO value on a 2024 GLS in 2026. Use **$3,000 as the point
estimate** when the skill needs a single number for the verdict
block.

Refine the point estimate based on the car's position relative to
NVLW expiration:

| Candidate state | Foregone-CPO value | Why |
|:--|:--|:--|
| Low-miles (<30K), well inside NVLW window | $1,500 to $2,500 | Mostly losing the 12-month tail; NVLW still has 18+ months and 20K+ miles left |
| Mid-miles (30K to 45K), most of NVLW used | $2,500 to $3,500 | Tail extension does meaningful work; reconditioning value rises |
| High-miles (45K to 75K), at or past NVLW exhaustion on miles | $3,500 to $5,000 | CPO LW becomes the only warranty coverage immediately; full risk-transfer value |

For the verdict block:

```
CPO: No — foregone-warranty value ~$N (12-mo CPO LW tail + 165-point
inspection + ancillary benefits forfeited)
```

### Apples-to-apples adjustment

When scoring a non-CPO candidate against a CPO comparable in
`references/comp-pricing-framework.md` (once written), **subtract
the foregone-CPO dollar figure from the non-CPO asking price**
before doing the comp. If the non-CPO car is not at least
foregone-CPO dollars cheaper than the CPO comp, the CPO car wins
on dollars before any risk adjustment.

## For a 2024 GLS specifically

Worked math for the typical 2024 GLS being shopped in 2026:

- **In-service date range:** late 2023 through late 2024
- **Original NVLW window:** 4 years / 50K miles from in-service
- **Typical NVLW remaining at mid-2026 purchase:**
  - In-service mid-2024 + 15K miles → ~24 months / ~35K miles left
  - In-service mid-2024 + 35K miles → ~24 months / ~15K miles left
  - In-service late-2023 + 40K miles → ~17 months / ~10K miles left
- **CPO LW adds 12 months unlimited miles on top of NVLW expiration**

The mileage side of the NVLW expires faster than the time side for
most 2024 GLS candidates in the CONTEXT ceiling (40K miles). A car
at 35K miles bought mid-2026 will hit NVLW mile-exhaustion well
before the 4-year date — CPO LW then provides 12 months of
unlimited-mileage cover starting from that point. **For a high-
mileage 2024 GLS, CPO is doing more work; foregone-CPO value sits
in the higher band ($3,500 to $5,000).**

## Red flags / common dealer tricks

- **"CPO eligible" listed as "CPO" in the headline.** Eligible means
  the car could be certified; certified means the inspection is
  done and the warranty contract is registered. Treat as non-CPO
  until verified via the Customer Assistance Center.
- **Inspection report dated after sale-pending date.** The
  inspection was not done at the time of listing. The car was
  marketed as CPO on a hypothesis.
- **"Certified" without the full "Mercedes-Benz Certified Pre-
  Owned" branding.** May be a dealer-only certification (worth ~$0
  in warranty terms — no MB factory backing).
- **Coverage exclusions buried in fine print.** Always confirm what
  is NOT covered (battery, wear items, alignment) before treating
  CPO as a complete warranty product.
- **Loss-leader CPO pricing on a base trim to anchor you, then
  bait-and-switch to a non-CPO Pinnacle.** Verify CPO status on
  the specific VIN you're actually buying, not the headline car
  that drew you in.
- **"We'll send the inspection sheet later."** Most common cover
  for a not-actually-done inspection. Insist pre-deposit.

## Cross-references

- `CONTEXT.md` — CPO is named as a non-negotiable preference; the
  foregone-warranty value figure here feeds the verdict block's
  CPO field.
- `references/gls-trim-decoder.md` — the data-card workflow
  (MBUSA window sticker, VeDoc from the dealer) pairs with the CPO
  verification workflow above. Pull both for any serious candidate.
- `references/comp-pricing-framework.md` *(to be written)* — the
  apples-to-apples adjustment using foregone-CPO dollars belongs in
  that file's comp-pulling routine.
- `references/negotiation-framework.md` *(to be rewritten)* — on a
  CPO car, the dealer's CPO premium is anchored by the inspection
  + warranty + reconditioning work they've done; on a non-CPO car,
  the foregone-CPO value is a negotiation lever that subtracts
  directly from the ask.

## Open calibration items

- **Exact 2026 inspection point count.** MBUSA still says "165+";
  no public update changing the number from 165. Treat 165 as
  current.
- **Lemon-buyback exclusion.** Inferred from the existence of MB's
  separate buyback program, not explicitly enumerated on the public
  CPO page. Treat as hard exclusion.
- **Loaner during CPO warranty repair.** Dealer courtesy, not a
  program benefit. Do not promise it on a verdict.
- **GLS-specific CPO premium dollars.** No published MB or third-
  party number isolates the GLS. The $2,500 to $4,000 range above
  is extrapolated from general luxury-CPO premium data; recalibrate
  once `comp-pricing-framework.md` runs real comps on live 2024 GLS
  inventory.
