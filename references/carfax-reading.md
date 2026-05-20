# Carfax reading for a 2024 GLS

For a 2024 GLS candidate, the Carfax is necessary but not sufficient.
The dealer-side **XENTRY / VeDoc** service record is more complete
for MB-specific items (software updates, recall stamps, warranty
work, TSB applications). **Pull both** — see section 12 below for
the workflow.

This file covers what to extract from each, ordered by what most
often kills a candidate at this price point and model year.

## What to extract, in order

1. **Owner count and ownership pattern**
2. **Title history (state-by-state)**
3. **Accident records**
4. **Service-record density and consistency**
5. **Service A / Service B (ASSYST PLUS) stamps**
6. **MB-specific service items beyond A/B** (9G-Tronic ATF, 4MATIC
   transfer case, brake fluid, AIRMATIC history, 48V mild-hybrid
   for the 450)
7. **M256 (450) and M177 (580) known-issue service records**
8. **Mileage progression**
9. **Inspection / registration history**
10. **Open recalls** (lookup against NHTSA + MBUSA by VIN)
11. **Cross-check Carfax against XENTRY / VeDoc**

## 1. Owner count: reconcile with the seller's claim

The Carfax owner count and the seller's claim can both be honest and
disagree. Carfax counts every title transfer, including dealer-to-
dealer flips. A "second owner" claim from a private seller may
ignore those.

**Rule:** ignore the raw owner count. Look at the gap between owner
transitions. For a 2024 GLS shopped in 2026 (1–2 years old), most
candidates will have one retail owner. A 2-year-old GLS with 3+
owners is a hot potato — ask why.

## 2. Title history

- **All in one state**: green flag. Local car, easier to verify.
- **Multiple states**: not bad if each transition is a real move.
  State-hopping to clean a branded title is a known trick — if the
  Carfax shows "title issue" anywhere in history, it stays.
- **Branded title at any point** (salvage, rebuilt, flood, lemon-law
  buyback): **auto-Pass** per CONTEXT. Also automatically disqualifies
  from MB CPO per `references/mbusa-cpo-criteria.md`.

## 3. Accident records

Carfax accident records come from police reports, insurance claims,
body shops (only some), and DMV records (only severe). **"No
accidents reported" is not the same as "no accidents."**

For a 2024 GLS specifically:

- **Any accident with airbag deployment**: **auto-Pass** per CONTEXT.
- **Structural damage reported**: **auto-Pass** per CONTEXT.
- **Minor damage to one panel** with continued service afterward:
  acceptable; price-anchor the cosmetic remediation if visible in
  photos (per `references/trim-id-guide.md`'s cosmetic checks).
- **Bodywork without a reported accident** (panel respray, paint
  thickness inconsistent in photos): yellow flag. Ask the dealer.
  At a 1–2 year-old MB price point, undisclosed body repair is a
  meaningful concern.

## 4. Service-record density and consistency

The headline number to look for on a 2024 GLS at 15K–35K miles:

| Mileage | Expected service-record count | Pattern |
|:--|:--|:--|
| 0–10K | 1 (PDI + first oil) | Single MB-dealer entry |
| 10K–15K | 1–2 (PDI + Service A) | Mostly MB dealer |
| 15K–25K | 2–3 (PDI + A + possibly B) | Should be all MB-dealer for a CPO candidate |
| 25K–35K | 3–4 (PDI + A + B + A) | All MB-dealer or specialist independent |

**Good pattern:** all MB dealer or one MB-specialist independent.
Regular Service A/B cadence (see section 5). Records start at PDI or
delivery and continue without gaps.

**Bad pattern:** sparse (1–2 stamps on a 25K+ mi 2024 GLS), service
at many random shops, gaps > 10K miles between services, multiple
visits for the same issue.

## 5. Service A / Service B (ASSYST PLUS)

The 2024 GLS uses Mercedes' **ASSYST PLUS** service-interval system
(the US successor to the European-market "FSS" terminology). It
calculates the next service adaptively but is capped at hard
ceilings.

| Service | Interval | What's done |
|:--|:--|:--|
| First Service A | 10,000 mi or 1 year, whichever first | Synthetic oil + filter, fluid top-off, multi-point inspection, wiper blades, reset |
| Subsequent A ↔ B alternation | ~10,000 mi or 1 year between each | A then B then A then B, alternating |
| Service B (extra items vs A) | every ~20,000 mi cumulative | Cabin filter, **brake fluid flush**, more detailed inspection. Engine air filter on B is dealer-variable |
| Annual time ceiling | 1 year max regardless of miles | The car will flag "service due" by time even if miles are low |

**What a 2024 GLS at 20K–25K mi should show on Carfax:** 2–3 service
stamps — roughly Service A ~10K, Service B ~20K, possibly a third
Service A in progress. Absence is a real flag; the car either was
neglected (rare on warranty MB) or had services done at a non-MB
shop that didn't report to Carfax.

**Brake fluid caveat:** brake-fluid replacement is bundled into
Service B every 2 years, and is **the most commonly skipped Service
B item** per MBWorld and BenzWorld threads. Dealers sometimes
invoice Service B without performing the flush. **Verify** that the
line item appears in the detailed service record — if all you see is
"Service B performed," ask the dealer to confirm brake fluid was
actually replaced. Confidence: Medium on the skip-rate claim
(anecdotal but well-attested).

## 6. MB-specific service items beyond A/B

Items not on the standard ASSYST PLUS schedule but worth checking
for at the 2024 GLS mileage band:

### 9G-Tronic transmission fluid (725.0 / 725.1)

- **MB official:** "lifetime fill" — no scheduled service.
- **Specialist consensus** (MBWorld, Blauparts, YouCANic,
  themercedesservice.com): drain-and-fill at 40,000 mi; full service
  60,000–80,000 mi.
- **Fluid spec:** MB 236.17 (ATF 134 FE), ~9–11 L capacity.
- **Cost (US 2026):** $600–$1,100 indy / $900–$1,500+ MB dealer.

**What to expect on Carfax for a 2024 GLS:** nothing. Absence is
normal; presence (especially from an MB-specialist independent) is a
positive signal of a proactive prior owner.

### 4MATIC transfer case fluid

- **Not on MB scheduled maintenance.** Owner-discretion.
- **Specialist consensus:** ~40,000 mi.
- **Fluid spec varies by transfer case variant:** standard uses MB
  236.12; Torque-on-Demand multi-disc clutch variant uses MB 239.41
  (Ravenol TF-0870 / MB DTF-1). **Verify which variant the VIN has
  before quoting fluid spec.**
- **Cost:** $150–$350.

**What to expect on Carfax:** typically nothing at 20K–40K mi.
Absence is normal.

### Brake fluid (2-year cadence)

Already covered in section 5 (bundled into Service B). Worth
explicitly verifying because of the skip pattern.

### AIRMATIC air suspension service history

The 2024 GLS ships with **AIRMATIC standard**. Pattern matters:

**Failure modes** (extrapolated from MY20–23 X167; insufficient MY24
data in 2026):

- **Leaking front struts** — most common X167 issue. Symptoms:
  vehicle sagging overnight, compressor running long after key-on,
  "Vehicle level low / Visit workshop" warnings.
- **Compressor failure** — usually secondary to a leaking strut
  overworking the pump. Primary compressor failure is rarer pre-60K.
- **Control module / software faults** — common enough that MB's
  TSB `LI32.22-P-073368` calls out software updates as the first
  remedy before mechanical replacement.

**Cost (US 2026, dealer):**

- Single front strut: $1,800–$2,500 installed
- Rear strut: similar to slightly less
- Compressor: parts $300–$600, installed $800–$1,400
- Control module: $200–$500 + diagnostic

**Carfax red flags:**

1. Any "suspension" or "AIRMATIC" line within first 30K mi →
   unusual at this mileage, investigate
2. **Multiple** AIRMATIC visits → likely chronic leak chasing
3. A single TSB / software-update visit → benign, often the fix
4. Compressor replacement without simultaneous strut inspection →
   may not be fully resolved

### 48V mild-hybrid system (GLS 450 only)

The 450's M256 inline-6 includes an **ISG (Integrated Starter-
Generator)** + 48V system + eBooster. Carfax entries to look for:

- **"Starter-generator" / "ISG" R&R** — significant red flag at any
  mileage. ISG R&R is $2,000–$3,000.
- **48V battery replacement** — $2,000–$3,000.
- **eBooster diagnostic** — occasional; acceptable as a single
  documented visit.
- **Recall 24V-207 completion** (48V ground connection / fire risk)
  — see section 10. MY24 GLS 450 is **mostly excluded** from the
  original VIN range but verify per candidate.

## 7. M256 (450) and M177 (580) known-issue records

**Confidence framing:** nearly all of the items below are
**extrapolated from MY19–MY23 patterns**. MY24 vehicles in 2026 are
0–2 years old, mostly under warranty, and not enough have reached
failure-prone mileage to call any of this "documented for MY24."
Treat as risk vectors, not certainties. Mark
`extrapolated-from-prior-MY needs-validation` in any verdict that
cites these.

### M256 (GLS 450)

| Known issue | Typical onset | Carfax signal to watch for |
|:--|:--|:--|
| Oil consumption / piston ring wear | 40K+ mi | Frequent oil top-offs invoiced; consumption test |
| Electric coolant pump failure | Varies; early MY had wiring chafe TSB | Coolant pump R&R line item |
| ISG faults | Reported, not epidemic | "Starter-generator" / "48V system" R&R |
| 48V battery failure | Reported | 48V battery replacement |
| eBooster faults | Occasional | Diagnostic + R&R |
| Timing chain noise | Higher-mileage (60K+) | Rare pre-60K |

### M177 (GLS 580)

| Known issue | Typical onset | Carfax signal to watch for |
|:--|:--|:--|
| Valve cover gasket / oil cooler O-ring leaks | 50K+ mi | Valve cover gasket R&R, oil cooler line |
| Oil cooler line crimp-fitting seepage | 50K+ mi | Same as above |
| Engine-mounted water-to-air intercooler leaks | Variable | Intercooler R&R, coolant top-off pattern, misfire codes |
| Carbon buildup on intake valves (DI engine) | 60–80K mi | Rare on Carfax pre-50K |
| Timing chain stretch | 80K+ mi | Rare pre-80K |
| Lifter rattle / collapsed lifters | Documented on M178 (AMG GT) and M177 in C63/E63/G63 contexts; **not** pattern-documented on GLS 580 M177 specifically | "Top end noise" diagnostic visits |

## 8. Mileage progression

Look at the mileage column over time. It should increase monotonically
at a roughly consistent rate.

- **Rate of accumulation:** typical MB SUV is 8K–14K mi/year. Under
  5K/yr is grandpa/garage-queen territory (often good). Over 20K/yr
  is road-warrior commuter (more wear).
- **Mileage that goes backwards:** odometer rollback. **Walk first,
  then report.** Do not confront the seller in person. Report to the
  state AG and the NHTSA odometer fraud line.
- **Long flat periods:** car was parked. Could be normal; could be
  theft / impound / collision. Investigate.

Compare the most recent Carfax mileage to the odometer in the
listing photos. If the photo shows less mileage than the most recent
Carfax record, the car has been driven backwards or the listing is
stale.

## 9. Inspection / registration history

Less applicable to a 2024 GLS at 1–2 years old than to an older car
— most states don't require inspection until the car is older. For
states that do (VA among them), a fresh state safety inspection
sticker visible in photos is a small positive signal.

## 10. Open recalls

**Two lookup channels by VIN:**

- **NHTSA:** `https://www.nhtsa.gov/recalls` — authoritative for US
  safety recalls.
- **MBUSA:** `https://www.mbusa.com/en/recall` — also surfaces
  non-safety service campaigns.
- **MBUSA Customer Assistance:** 1-800-367-6372.

**Current recall picture for 2024 GLS (as of 2026):**

| NHTSA Campaign | Subject | MY24 GLS applicability |
|:--|:--|:--|
| **24V-207** | 48V ground connection under passenger seat — fire risk | Mostly 2019–2023; **MY24 GLS 450/580 largely excluded** — verify by VIN |
| **24V-118** | TCU software / 9G-Tronic behavior | 2020–2023 GLE/GLS 450 — **MY24 explicitly excluded** |
| **Mid-2025 windshield bonding** | Multi-purpose camera + interior mirror may separate from windshield | **Includes 2024 GLS 450 4MATIC built Jun 5 – Oct 12, 2024** — very narrow VIN window; verify per candidate |

**Recall lists are time-sensitive.** New recalls publish monthly. The
skill should treat any frozen list as stale on a 60-day horizon —
always re-check NHTSA by VIN at the time of evaluation.

Open recalls are not deal-breakers (the dealer performs them free),
but should be completed before the title transfers if possible. A
non-CPO car with open recalls AND no dealer-side service history for
recall completion is a yellow flag — pull the XENTRY record to
verify.

## 11. Specific service events to look for

Pull these out and note when last done. Use mileage at time-of-
service, not date.

| Service | MB interval | Why it matters at this MY |
|:--|:--|:--|
| Engine oil + filter | Service A interval | Most-recent should be recent |
| Cabin filter | Service B (~20K) | If absent at 20K+, ask |
| Brake fluid flush | Service B (every 2 yr) | Most-skipped item — verify line item |
| Brake pads (front) | 30K–50K | Note current measurement if PPI done |
| Brake pads (rear) | 60K–100K | Often original at 30K |
| Tires | OEM Continental / Pirelli, typically 30K–40K life | DOT date code matters; replace if >4 yr regardless of tread |
| 12V battery | 5–7 yr | Note if replaced (especially relevant for 48V-equipped 450) |
| Differential / transfer case fluid | Owner discretion ~40K | Bonus if done |
| 9G-Tronic ATF | MB "lifetime"; specialist 40K | Absence normal at 20–40K |
| AIRMATIC compressor/strut | None scheduled | Any entry is signal |

For each service: subtract the last-done mileage from current
mileage. If at or past the typical interval, budget for that service
in the negotiation case (per
`references/negotiation-framework.md` once rewritten).

## 12. Carfax vs XENTRY / VeDoc — pull both

The dealer-side XENTRY system captures items that often don't flow
to Carfax. This is the single most important point on this page for
a 2024 GLS evaluation.

**What XENTRY captures that Carfax often misses:**

- Software updates and TSB applications (rarely flow to Carfax)
- Warranty repairs not coded as "service" by the dealer's DMS
- Recall completion stamps (sometimes delayed or absent on Carfax)
- Pre-delivery inspection (PDI) and port-installed options
- Goodwill repairs

**What Carfax captures that XENTRY misses:**

- Independent shop visits (XENTRY only sees MB-dealer activity)
- State inspections, emissions, title events
- Accident / airbag records
- Tire shop / alignment shops

**Recommendation:** pull both. Workflow:

1. **Carfax** (or AutoCheck) from the selling dealer or via your own
   account — covers ownership, accident, title, indy-shop history.
2. **XENTRY Digital Service Booklet / VeDoc report** from the
   selling MB dealer's Parts or Service department. Suggested
   phrasing:
   > "Could your Service department print the XENTRY Digital
   > Service Booklet / VeDoc record for VIN ______? I want to
   > review the full MB-dealer service history including any
   > recall and software-update status."
3. If the seller is a private party or non-MB dealer, ask **MBUSA
   Customer Assistance (1-800-367-6372)** to look up the VIN's
   service history, **or** ask any MB dealer's service writer to
   print VeDoc for the VIN — most will do it on request, though
   policy varies by dealer.

A dealer who refuses to print VeDoc without good reason is a signal
worth noting in `references/dealer-tier-list.md`.

## 13. Carfax vs AutoCheck

Carfax is the dominant report; AutoCheck (Experian) sometimes
catches events Carfax misses, especially auction history (AutoCheck
has stronger Manheim integration). If a Carfax looks suspiciously
clean given the car's history, AutoCheck is ~$25 and worth the
second opinion.

The actual paper title is the definitive document. Verify at meet-up
that VIN matches, name matches the seller's ID, and there are no
liens or brands.

## 14. Summary output template

When given a Carfax + XENTRY for a 2024 GLS candidate, return:

```
Carfax + XENTRY summary — [VIN, year/trim/dealer]:

Ownership:
- Owners: N (pattern: single retail / hot-potato / fleet history)
- Title: clean across all states / branded in [state] in [year]

Accidents:
- Carfax: none / N reported (severity per record)
- Photo cross-check: clean / panel respray suspected / visible damage

Service history density:
- Carfax records: N over Y months
- XENTRY records: N over Y months (delta from Carfax: M items)
- Pattern: all-MB-dealer / mixed / sparse

Service A/B history (ASSYST PLUS):
- Service A stamps: [dates / mileages]
- Service B stamps: [dates / mileages]
- Brake fluid verified in last B: yes / no / unable to confirm

MB-specific items:
- 9G-Tronic ATF: not done (normal at this mileage) / done at [date / mi]
- 4MATIC transfer case: not done / done at [date / mi]
- AIRMATIC entries: none / [list]
- 48V/ISG entries (450): none / [list]

Known-issue records (extrapolated-from-prior-MY needs-validation):
- M256 (if 450): [oil consumption / coolant pump / etc., or "none"]
- M177 (if 580): [valve cover / oil cooler / etc., or "none"]

Mileage:
- Progression: consistent / suspicious / rollback
- Photo odometer vs latest Carfax: matches / mismatch

Open recalls (NHTSA lookup by VIN):
- [list], all complete / N open: [list]

Risk summary: [1–2 sentences]
Negotiation levers: [list of dated, specific defects or upcoming services]
Near-term spend (first 12 months): $X to $Y
```

## 15. Worked example — Fredericksburg 450 candidate

VIN `4JGFF5KE0SB######` (production sequence redacted; full VIN held
in session context). 2024 GLS 450 4MATIC, Tuscaloosa-built. Mileage
TBD from listing.

**Pull sequence:**

1. **Carfax** — request from Fredericksburg Sales as part of the
   standard pre-purchase package. CPO listings typically include
   Carfax free per `references/mbusa-cpo-criteria.md`.
2. **XENTRY Digital Service Booklet / VeDoc** — request from
   Fredericksburg Service department per section 12 phrasing.
3. **NHTSA recall lookup** — paste VIN at
   `https://www.nhtsa.gov/recalls` to verify the windshield/mirror
   recall window (Jun 5 – Oct 12, 2024 build). Any candidate built
   in that window must show the recall completed before scoring
   past Stage 3.

**What to fill in once data lands:**

- Owner count + pattern
- Any accident records (with severity)
- Service A / B stamp count at current mileage (expectation: 2–3
  stamps for typical 20K–25K mi range)
- Brake fluid verified in last Service B
- Any AIRMATIC entries (auto-flag if more than one)
- Any 48V/ISG entries (auto-flag for further investigation)
- Recall completion status for 24V-207 and the windshield-bonding
  campaign if applicable

**Dealer-responsiveness read:**

Note in `references/dealer-tier-list.md` how Fredericksburg
responds to the VeDoc request. A Parts/Service writer who pulls it
in 30 seconds without fuss is **KNOWN-GOOD**; one who deflects or
claims they "can't share that" is a signal that correlates with
other transparency issues later.

## Cross-references

- `CONTEXT.md` — title and accident thresholds (clean only;
  no structural or airbag deployment events).
- `references/mbusa-cpo-criteria.md` — CPO eligibility excludes
  branded titles and ties to service-history continuity. CPO
  listings should include Carfax; ask if not provided.
- `references/gls-trim-decoder.md` — the data-card workflow
  pairs with the XENTRY request; both come from the same dealer
  Parts/Service contact.
- `references/trim-id-guide.md` — photo cross-check against
  Carfax accident records (mismatched paint, panel-gap issues).
- `references/comp-pricing-framework.md` — overdue services and
  near-term-spend estimates feed the comp-adjustment math.
- `references/dealer-tier-list.md` — dealer responsiveness on
  Carfax / VeDoc requests is a tier-list-updating signal.
- `references/negotiation-framework.md` *(to be rewritten)* —
  dated defects and overdue services are the lever inputs.

## Open calibration items

- **MY24-specific known-issues data** for M256 and M177 is
  extrapolated from MY19–23 patterns. As MY24 vehicles age and
  warranty repairs become public, this list will sharpen.
- **2024 GLS US Maintenance Booklet exact wording** for Service A/B
  scope — verify against the PDF at MBUSA's owner-manual portal if
  the dealer disputes a line item.
- **Transfer case variant per VIN** — standard vs Torque-on-Demand
  multi-disc clutch — affects fluid spec; confirm via VIN before
  quoting service costs.
- **Recall list is time-sensitive** — refresh against NHTSA on every
  candidate evaluation, even if the file was updated recently.
- **Dealer willingness to print VeDoc for non-customers** varies by
  rooftop and individual writer. Track per-dealer responses in
  `references/dealer-tier-list.md` as data accumulates.
