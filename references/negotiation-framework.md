# Negotiation framework — franchise-dealer 2024 GLS

The right offer is anchored to **specific defects, missing options,
foregone-CPO value, and verified comps** — not "I'd like to pay
less." A defect/options-anchored offer is hard for a dealer to argue
with because each dollar off has a published number behind it.

This is a **franchise-dealer** framework, not private-party. Different
mechanics, different leverage, different counterparties. Key
differences from the upstream private-party version:

- The anchor is **CarGurus IMV + KBB CPO Fair Market Range**, not KBB
  private-party Fair.
- The counterparty is the **Internet Sales Manager (ISM)**, not a
  guy in a driveway.
- The conversation happens by **email-first**, not at a meet-up.
- The **F&I gauntlet** is a real stage of the deal — separate from
  car-price negotiation.
- **Cash-handoff safety, VIN-verification-at-meet, and curbstoner
  tactics are out of scope** — the dealer handles title and
  registration paperwork.

## 1. The anchor

Per `references/comp-pricing-framework.md`, the primary anchor for
every offer is **CarGurus IMV trailing-90d** on the listing's local
market. Cross-check with **KBB Fair Market Range — CPO Retail tier**
because CONTEXT's binary CPO posture demands the CPO-specific band,
not the generic dealer-retail tier.

Wholesale-floor data points for negotiation framing only:

- **CarMax instant offer** and **Carvana instant offer** on the
  candidate VIN (some configs accepted, some not). These set "what
  the car would fetch as a wholesale trade today" — useful as a
  rhetorical floor, not as an offer target.

A franchise dealer's reasonable margin over IMV is **$0–$3,000** for
a CPO 2024 GLS in normal conditions. Aged inventory (>60 days on
lot) carries more room (**$2,000–$5,000** of negotiation space) per
`references/comp-pricing-framework.md` stale-listing thresholds.

## 2. The math

Start with **CarGurus IMV** for the verified trim and mileage. This
is the price a reasonable dealer should expect.

**Subtract:**

- Cost of every defect found on the PPI or in photos, at the local
  MB-specialist quoted price (see defect-cost table below)
- Cost of every overdue scheduled service (Service B if missed,
  brake fluid if skipped per `carfax-reading.md`, tires near
  end-of-life)
- **Options delta** vs the median comp — if THIS candidate is
  missing must-have packages relative to comps at the same ask,
  subtract the residual-decay value (per
  `references/comp-pricing-framework.md` options-delta math at 0.40
  multiplier)
- **Foregone-CPO adjustment** if non-CPO: subtract $1,500–$5,000
  per `references/mbusa-cpo-criteria.md` mileage band; default
  point estimate $3,000
- **Days-on-lot discount** for aged inventory: 1.5–3% off IMV at
  30–45 days, additional 2–4% at 60–75 days, deeper at 100+ days
- **450 trigger check** (450 candidates only): per CONTEXT, Katie
  prefers the 580; a 450 only competes if its ask is **≥ $15K
  below the comparable 580**. Before running any subtraction math
  on a 450 candidate, confirm the trigger is cleared. A 450 that
  fails the trigger is a Pass regardless of how clean it is — the
  580 wins on Katie's QoL frame at any smaller gap.
- **Negotiation cushion**: $500–$1,500 for the dealer to feel they
  got somewhere

The result is your **walk-away offer** before the OTD wrap (doc
fee, sales tax, registration).

## 3. Lever categories that ARE valid

- **Days on lot.** Use CarGurus's "days at the dealership" + "days
  on CarGurus" pair per `comp-pricing-framework.md`. **75+ days =
  meaningful leverage. 100+ days = strong leverage.** Dealer
  holding cost ($40–$85/day in interest + insurance + depreciation)
  is biting.
- **Missing-options-vs-comp in dollars.** Per the options-delta
  formula. "Your ask is at IMV but the median comp at this price
  has Burmester 3D and Acoustic Comfort — this one doesn't. That's
  ~$2,400 of forgone value at typical residual."
- **CPO foregone-value adjustment.** Per `mbusa-cpo-criteria.md`:
  "Your ask is competitive with the CPO comps in the area, but
  this car is non-CPO. The foregone 12-mo CPO LW + inspection +
  ancillary benefits adds ~$3,000 of risk to me — needs to come
  off the ask."
- **End-of-month / end-of-quarter timing.** Still real at MB
  stores in 2026. June 30, Sept 30, Dec 31 are the strongest
  points; last 3 days of any month is meaningful.
- **Markup above IMV.** "CarGurus IMV for this exact VIN is $X.
  Your ask is $Y. The gap needs to close."
- **Wholesale floor from CarMax / Carvana on the candidate VIN.**
  Rhetorical only — "Carvana would buy this car today at $W. Your
  $Y ask is $Y-W above what the market will pay you tomorrow if I
  walk."
- **Inspector / photo-flagged items the dealer didn't disclose.**
  "Your listing said 'pristine condition' but the wheel close-ups
  I requested show curb rash on the front-left. That's $300 of
  refinishing the listing should have priced in."
- **Recent price reductions.** Already-reduced inventory will
  reduce again. Use CarGurus's price-history graph.
- **Underrated lever: trade Extended CPO LW attach for price
  reduction.** F&I product attach matters to dealer compensation.
  "I'll buy the MB Extended CPO LW +2yr through your F&I office at
  a fair price IF the OTD on the car drops to $X." Can move
  $500–$1,500 on the car price.

## 4. Things that are NOT levers

- **"I saw it cheaper online."** The dealer will say "go buy that
  one." If true, you should. If you're still here, your leverage
  is in the comp data, not the comparison shopping.
- **General market conditions.** Specific instruments only.
- **Your budget.** The dealer doesn't care.
- **"I'm pre-approved for $X."** Useful for closing speed, useless
  for car-price negotiation.
- **Asking for a discount because you're paying cash.** Cash is
  the dealer's preferred outcome only when they can't earn
  finance-reserve commission — which is the case for many luxury
  buyers, but the dealer won't reward you for it. Don't pitch it
  as a lever.
- **Friendliness / building rapport.** Pleasant to be around, but
  it doesn't move price. The ISM doesn't have authority to
  discount because you're nice.

## 5. Conversation tactics — email-first, written-offer

**Email-first is more effective in 2026 than in 2022, not less.**
Internet Sales Manager (ISM) departments are now the primary
inbound channel at MB stores and have authority to quote OTD
prices. Use email until there's an agreed OTD on paper.

**Right contact:** Internet Sales Manager or Internet Sales
Director. Avoid the GM (too senior, won't engage on one CPO unit)
and avoid generic "Contact Us" web forms (route to the BDC; you get
a phone call back, not a price). If the ISM bounces you, escalate
to Sales Manager.

**Opening email template that works:**

> **Subject:** 2024 GLS [450/580] Pinnacle CPO — Stock #[####] — Out-the-Door Quote Request
>
> Hi [Name],
>
> I am a serious buyer in 22182 ready to transact this month on the
> right 2024 GLS Pinnacle CPO. Stock #[####] looks like a fit.
> Please send a written OTD quote including:
>
> - Selling price
> - VA SUT (4.15%) calculation
> - Doc / processing fee
> - VA title and registration
> - Any pre-installed dealer add-ons itemized (I will decline anything not factory or MB CPO)
> - MB Extended CPO Limited Warranty +2yr quote as a separate line (I may add this)
>
> I am comparing three dealers within 250 miles. I can be at your
> store with funds [day] if your number is the best. Please respond
> by email with line items — no phone call needed at this stage.
>
> Thanks,
> [Name]

**Common dealer counters and the response:**

| Dealer counter | Your response |
|:--|:--|
| "Come in and we'll talk numbers" | "I'll come in to sign once we have an agreed OTD on paper. Until then, email." |
| "Our pricing is best in person" | "Then I'll work with the dealer who'll commit on paper." |
| "We have multiple parties interested" | Ignore. Standard pressure tactic; if true, the unit will be gone in 24 hrs. |
| Padded OTD with add-ons you declined | "Resend with [X], [Y], [Z] removed per my original email." |
| "I can do that price IF you finance with us" | "Send me both the cash and financed OTD. I'll evaluate." |

**Run parallel candidates from day one.** Email 3–5 dealers within
250 mi simultaneously. Mention you are comparing offers (do NOT
name competing dealers). Your 250-mi radius covers all Tier A and
Tier B dealers in `references/dealer-tier-list.md`.

## 6. The F&I gauntlet

When you sit in the F&I office to close, you will get pitched a
stack of add-ons. **The FTC CARS Rule (effective July 30, 2024) is
your legal anchor for refusing pre-installed items** — they cannot
be required for the purchase, and you can demand removal from the
contract.

| Product | Typical pitch | Verdict | Refusal phrasing |
|:--|:--|:--|:--|
| **GAP Insurance** | $700–$1,200 | Skip if paying cash or financing under 80% LTV. Worth ~$300–$500 from your own insurer if needed. | "I'm paying cash / financing under 80%, no GAP." |
| **MB Extended CPO Limited Warranty (+1yr or +2yr)** | $2,000–$3,500 for +1yr, up to $4,000 for +2yr | **The only sanctioned add-on per CONTEXT.** +2yr at ~$3,500 = ~$1,750/yr — fair given GLS repair exposure. Worth comparing to out-of-area MB dealers (Tafel MB, Elmbrook MB known to discount 20–30%) before committing locally. | "I'll consider the MB Extended CPO Limited Warranty +2yr. Quote me MSRP and your best discount." |
| Third-party / aftermarket extended warranty | $2,500–$5,000+ | **Prohibited by policy.** | "Policy is MB factory CPO Extended only. Hard no on third-party." |
| MB Star Prepaid Maintenance | $1,500–$2,400 | Marginal on a CPO car that has Service A/B covered under the base CPO 1-yr unlimited warranty. Only worth it if you'll keep the car past CPO expiry. | "Skip. I'll pay-as-I-go at Service B intervals." |
| Theft / VIN Etching | $200–$400 | Cost to dealer ~$25. Refuse pre-installed. | "Per FTC CARS Rule this is optional. Remove from contract." |
| Paint/Fabric Protection (Xzilon, Permaplate, Ceramic Pro) | $600–$2,000 | Near-zero value; factory clear coat suffices. | "No. Decline." |
| Tire & Wheel Coverage | $800–$1,500 | Marginal for 21"/22" wheels on pothole-rich NoVA roads; still skip — pay-as-you-go is cheaper. | "No." |
| Key Replacement Coverage | $300–$600 | MB key fob is ~$400–$600 to replace at dealer; coverage rarely pencils. | "No." |
| Nitrogen Tire Fill | $200–$400 | Worthless. Air is 78% nitrogen. | "Remove. Not paying." |

## 7. Doc fees, sales tax, and dealer-add-on handling (VA-specific)

| Line item | VA / NoVA reality | Negotiable? |
|:--|:--|:--|
| **Doc / processing fee** | **$799–$999 typical in NoVA; no statutory cap.** Among the highest in the US. *Calibration: Mercedes-Benz of Fredericksburg confirmed at $999 — top of the range.* | Yes in practice; dealers resist but will eat $200–400 on a big deal. Ask explicitly. |
| **VA Sales and Use Tax (SUT)** | **4.15% of gross sales price, $75 minimum.** | Not negotiable. |
| **Trade-in tax credit** | Ambiguous in VA — language is unclear and dealer practice varies. **Confirm in writing on the OTD quote** before relying on it for math. | N/A but verify treatment. |
| **VA title fee** | ~$15 | Not negotiable. |
| **VA registration** | ~$45–$60 depending on weight | Not negotiable. |
| **Pre-installed wheel locks** | $150–$300 | Refuse or refund per FTC CARS Rule. |
| **Pre-installed window VIN etching** | $200–$400 | Refuse. |
| **Pre-installed paint sealant / Permaplate** | $600–$1,500 | Refuse. |
| **Pre-installed GPS / LoJack** | $400–$900 | Refuse unless legitimately on-lot factory option. |
| **"Market Adjustment" / ADM** | Variable | Always negotiable; effectively gone on used in 2026 except on AMG/63 in tight inventory windows. |

**Pattern:** for every "pre-installed" item on the sticker, the
correct posture is "remove from contract." A dealer who claims they
"can't" remove a pre-installed item is testing you. The FTC CARS
Rule says they can.

## 8. Trade-in mechanics

CONTEXT mentions a 2022 Rivian R1T and 2021 Porsche Macan S in the
current fleet. If trading one:

**The math: sell separately wins almost every time.**

- **CarMax instant offer** and **Carvana instant offer** are both
  free and fast. As of early 2026, **Carvana typically offers
  $2,200–$3,600 more than CarMax on luxury vehicles** — get both,
  use the higher.
- **Dealer trade-in offer** typically runs 10–15% below the higher
  of Carvana / CarMax on luxury vehicles. On a $55K Carvana offer
  for the Macan, expect ~$47–49K from the MB dealer.
- **VA trade-in tax credit math:** if it applies (verify per
  section 7), the credit is only **4.15% × trade-in value**. On a
  $5K shortfall between dealer trade and Carvana, that's
  **$207.50** of tax-credit makeup. Nowhere near closing the gap.

**When trade-in still wins:** you can't be home for Carvana pickup
logistics, you owe more than market on the trade and need rollover
into a new loan, or the dealer offers within 2–3% of Carvana to
close a hot deal.

**Recommended:** keep the trade-in conversation entirely separate
from the car-price negotiation until the OTD on the car is locked.
Bundling them lets the dealer pad one side while shaving the other.

## 9. Defect-cost reference (US 2026)

Cosmetic and routine-service items most likely to come up on a 2024
GLS PPI or photo inspection. AIRMATIC and engine items are in
`references/carfax-reading.md`.

| Defect / service | Cost range (2026 US, dealer / specialist) | Confidence |
|:--|:--|:--|
| Curb rash repair, cosmetic blend (per wheel, 21"/22") | $200–$350 | Medium |
| Curb rash repair, full refinish (per wheel, 21"/22") | $300–$500 | Medium |
| Paint chip touch-up (per chip, small DIY) | $20–$60 | High |
| Paint chip — panel respray (per panel, luxury surcharge) | $400–$800 | Medium |
| Bumper scuff, cosmetic blend (no ADAS) | $300–$600 | High |
| Bumper scuff + ADAS recalibration | $650–$1,100 | Medium |
| PDR door ding (per dent, small/medium) | $200–$500 | High |
| Windshield replacement + ADAS recal (2024 GLS) | $1,400–$2,400 total | Medium-High |
| Tire set of 4, OEM 21" Pirelli/Continental | $1,400–$1,800 installed | High |
| Tire set of 4, OEM 22" Pirelli/Continental | $1,700–$2,400 installed | Medium |
| MBUX software update at dealer (out of warranty) | $150–$250 | Low — based on shop labor; sharpen against real quote |
| Brake fluid flush at MB dealer | $140–$220 | High |
| 12V battery replacement (580, dealer installed) | $400–$600 | High |
| 12V battery replacement (450 — 12V side) | $400–$600 | High |
| 48V battery replacement (450) | $1,500–$3,000 placeholder | **Low — too few real-world replacements to source cleanly; verify per quote** |

## 10. Sizing the offer

Two postures based on PPI / photo / Carfax / VeDoc outcome:

**Action posture — clean candidate, committed to close:**
- Open at IMV minus the sum of (defect costs + overdue services +
  options delta + foregone-CPO if applicable + $500–$1,500
  cushion + days-on-lot discount if applicable)
- Be ready to land at IMV minus (defect costs + options delta +
  foregone-CPO)
- Pair with concrete commitment: "Cash, picked up [day], MB
  Extended CPO LW +2yr through your F&I office at fair pricing."

**Watch posture — interesting candidate, willing to walk:**
- Open at the same number but framed as the only number
- One counter, then walk
- Run parallel candidates so walking has no opportunity cost

**For 580 candidates specifically:** 580 is the preferred default
trim per CONTEXT (Katie's QoL preference for V8 + Air Body Control).
A 580 priced at typical market ($88–98K, with effective ~$105K cap
for clearly exceptional candidates) is an Action candidate by
default when all other CONTEXT criteria pass. No special TCO-anchor
discipline required — just the standard math.

**For 450 candidates specifically:** verify the **≥ $15K below comp
580 trigger** before any subtraction math. A 450 ask must be at
least $15K below the comparable 580 in the local market to even
enter consideration; a 450 ask that falls inside that gap is a Pass
because the 580 wins on QoL at that price point. Once the trigger
is cleared, run the standard subtraction math; the 450 also has the
$80K hard ceiling on top of the trigger.

## 11. When the dealer won't move

Different from private-party. The franchise dealer holding firm on
a specific unit will rarely "come back" on the same car — but they
will come back on a comparable unit, or a different dealer will hit
your number. Run parallel from day one; don't get sentimentally
locked on one VIN.

- **One counter, then walk.** The pattern: anchor → first dealer
  counter → your one counter → silence and exit. After your one
  counter, anything more is bidding against yourself.
- **Same-unit callback horizon:** 7–21 days IF the unit is aging
  and you left a credible email trail with the ISM. Aged inventory
  >60 days on lot is your highest-leverage situation.
- **Sales Manager escalation:** only after the ISM has bounced you
  twice on the same item, or when the OTD includes pre-installed
  add-ons the ISM "can't remove." SM has authority the ISM
  doesn't on add-on stripping and on doc-fee concessions.
- **MBUSA Customer Assistance (1-800-FOR-MERCEDES) is not useful
  for purchase negotiation.** They handle warranty disputes,
  service complaints, and CPO certification eligibility questions.
  Don't waste a call here pre-purchase.

## 12. Closing

When the OTD is agreed in writing:

1. Read the contract before signing. Verify the agreed selling
   price, doc fee, VA SUT, title, registration, any Extended CPO
   LW line item. Anything else gets removed.
2. Verify the **VIN on the contract matches the VIN you've been
   negotiating against** (per `references/gls-trim-decoder.md`).
3. Verify the **CPO Inspection and Certification Report has been
   provided** (per `references/mbusa-cpo-criteria.md`). If it
   hasn't, refuse to sign until it is in your hand.
4. Funds via wire transfer to the dealer's title-clerk account or
   cashier's check from your bank. No carrying $80K in cash to a
   dealership.
5. Get a copy of every signed document. Confirm title transfer
   will be handled by the dealer's title clerk per VA standard.
6. Retain the OTD email trail with the ISM as documentation that
   you declined add-ons in writing — defends against any
   contract-padding attempts.

## 13. Worked example — Fredericksburg 450

VIN `4JGFF5KE0SB######` (production sequence redacted; full VIN
held in session context). 2024 GLS 450 4MATIC, Tuscaloosa-built.
User reports color off-spec. Mileage, ask, and CPO status TBD.

**Template offer-build once data is in hand:**

```
Listing: [URL]
Dealer: Mercedes-Benz of Fredericksburg (Tier A, ~55 mi)
Ask: $[X]    Mileage: [N]    Days on CarGurus: [D]
CPO status: [verified Yes / verified No / unverified]

Anchor:
  CarGurus IMV (local): $[A]
  KBB CPO Fair Market Range (or dealer-retail if non-CPO): $[B] - $[C]
  Wholesale floors (CarMax / Carvana on VIN): $[W1] / $[W2]

Subtractions from IMV:
  - PPI/photo defects (if any): -$[N1] (specific items)
  - Overdue services (if any): -$[N2]
  - Options delta vs median comp: -$[N3] (per comp-pricing formula at 0.40)
  - Foregone-CPO adjustment (if non-CPO, mileage band): -$[N4]
  - Days-on-lot discount (if >60 days): -$[N5]
  - Color spec deviation: -$[N6] (negotiation lever — listing didn't show off-spec color prominently, materially affects resale, $500-1,500 range)
  - Cushion: -$500 to -$1,500

Walk-away offer (before OTD wrap): $[walk-away]

Email-first opening offer (Action posture): $[opening, slightly under walk-away]

OTD wrap:
  Selling price: $[final]
  VA SUT 4.15%: $[tax]
  Doc fee (negotiate $200-400 off NoVA standard $799-999): $[doc]
  VA title + registration: ~$60-75
  Total OTD: $[total]

F&I add to consider:
  MB Extended CPO LW +2yr: quote separately, $2,000-3,500 budget;
  cross-check Tafel MB / Elmbrook MB out-of-area pricing
```

**Pre-negotiation checklist:**

1. ✅ VIN decoded (per `gls-trim-decoder.md`)
2. Pull MBUSA window sticker for VIN — confirms options
3. Pull Carfax + request VeDoc (per `carfax-reading.md`)
4. Verify CPO via 1-800-FOR-MERCEDES (per `mbusa-cpo-criteria.md`)
5. Request photo set (per `trim-id-guide.md` worked example)
6. Pull CarGurus IMV + KBB CPO Range + Carvana/CarMax floors
7. Compute options delta vs median comp
8. Compute foregone-CPO subtraction (if non-CPO)
9. Note days-on-lot for leverage framing
10. Identify 2-3 parallel candidates at other Tier A/B dealers

Send the opening email per section 5 template. Run parallel.
Negotiate in writing only. Sign nothing until the CPO Inspection
and Certification Report is in your hand and the OTD line items
match what you agreed by email.

## Cross-references

- `CONTEXT.md` — price ceilings ($95K soft / ~$105K cap on 580
  preferred default; $80K hard cap on 450 + $15K-below-comp-580
  trigger), seating policy, geography, the 580-default trim frame
  with Katie's QoL preference.
- `references/comp-pricing-framework.md` — IMV methodology,
  options-delta math, days-on-lot signal interpretation, KBB CPO
  tier as primary cross-check.
- `references/mbusa-cpo-criteria.md` — CPO verification (single
  most important pre-negotiation check), foregone-CPO dollar
  table, Extended CPO LW as the only sanctioned warranty add-on.
- `references/gls-trim-decoder.md` — VIN decode, window-sticker
  pull, data-card workflow.
- `references/trim-id-guide.md` — photo verification, dealer photo
  trick patterns, dealer-responsiveness as tier-list signal.
- `references/carfax-reading.md` — Carfax + VeDoc pull, AIRMATIC
  / 48V / M256 / M177 known-issue records, recall lookup.
- `references/dealer-tier-list.md` — dealer geography tiers,
  responsiveness tracking.

## Open calibration items

- **VA trade-in tax credit treatment** — statutory language is
  ambiguous; confirm with the selling dealer in writing on the OTD
  quote before baking into the math.
- **MB Extended CPO LW +2yr price for 2024 GLS specifically** —
  ranges $2,000–$4,000; varies by VIN, mileage at sale, and dealer
  discount. The out-of-area discount channels (Tafel MB, Elmbrook
  MB, etc.) are anecdotal — worth pricing before committing locally.
- **48V battery replacement cost on GLS 450** — placeholder
  $1,500–$3,000 based on thin data; sharpen against a real quote
  if a candidate ever has a 48V service-history entry.
- **MBUX software update cost out of warranty** — placeholder
  based on shop labor rates; verify against real quote.
- **2024 GLS Pinnacle-specific CPO markup over IMV** — based on
  broader CarGurus data, not Pinnacle-trim-isolated forum threads.
  Recalibrate as real-candidate IMV pulls accumulate.
