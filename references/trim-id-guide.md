# 2024 GLS — photo-verification reference

Pre-drive triage for dealer listing photos. Use this to decide which
candidates are worth a phone call or PPI trip and which fail before
the gas money is spent. **Build sheet beats photo every time** — when
something matters, demand the Monroney or VeDoc rather than squinting
at a JPEG. Each claim below carries a confidence rating; anything
**Low** should be marked `needs-validation` against the first real
2024-or-newer GLS the skill scores.

---

## Photo-fetching workflow — surface URLs, view via user paste-back

When a listing has an internal conflict (e.g., feature list claims
both "6-seat captains" and "7-seat configuration") or any question
is **photo-resolvable**, the skill should **identify the specific
diagnostic image URLs and surface them to the user for paste-back**,
rather than defer with a generic "request more photos from the
dealer."

**Why paste-back instead of direct fetch:** Cowork's `web_fetch`
provenance system only accepts URLs that originated in a user
message (or a prior `web_fetch` result the system trusts). CDN paths
the skill discovers inside a dealer-page fetch (e.g., `vehicle-
images.carscommerce.inc/...`) are **not** auto-added to the
provenance set, so direct `web_fetch` or `bash curl` against them
both return 403. The same restriction blocks the Linux sandbox's
network egress. Empirically verified during the White Plains
calibration round.

Mechanics:

1. **Identify diagnostic photo(s).** Most resolutions only need
   one or two specific shots (e.g., a 2nd-row interior view for
   seating; a B-pillar sticker close-up for paint code; a wheel
   face for curb-rash check).
2. **Surface the image URLs to the user** as a short copy-paste
   block — typically the lead image plus the 2–3 diagnostic
   close-ups, with a one-line explanation of what each resolves.
3. **User pastes the URLs back into chat.** Pasting them in a user
   message adds them to the provenance set; subsequent `web_fetch`
   calls then succeed and the skill views the images directly via
   its vision capability.
4. **Only escalate to "demand from dealer"** when the diagnostic
   photo genuinely isn't in the listing set and can't be inferred
   from the available frames.

When NOT to use this workflow:
- **Build-sheet-only items** (Pinnacle trim, Driver Assistance
  Package, Acoustic Comfort) — pull the Monroney instead. No photo
  evidence is dispositive for these.
- **CPO verification** — call 1-800-FOR-MERCEDES.

Alternative paths considered and currently rejected:

- **Claude in Chrome** (`claude.com/claude-for-chrome`) would let
  the skill drive a Chrome browser to navigate dealer pages and
  screenshot images. The catch: Chrome must be **running in the
  background** for the extension to function. Adds a persistent
  process tax for what's currently a paste-back workflow. Revisit
  if (a) MBUSA window-sticker pulls require interactive workflow,
  or (b) bulk triage of 10+ candidates per session becomes routine.
- **Direct image upload** by the user (Save Image As → drag into
  chat) — works but is more steps than URL paste-back.

This adds maybe one extra exchange per candidate with a photo-
resolvable question and eliminates whole categories of "unverified"
downgrades in the verdict block.

---

## 1. Trim level visual tells — Pinnacle vs Premium vs Exclusive

The 2024 GLS US market sells three "trim levels" (Premium, Exclusive,
Pinnacle) layered on top of either the 450 or 580 model. They are
**equipment bundles, not bodywork** — exterior sheetmetal is shared
across all three. Most of the diagnostic difference is inside.

**Wheels.** Standard wheel on the 2024 GLS 450 is a 21-inch alloy;
the 580 ships with 22-inch wheels standard. The AMG Line option
substitutes 21-inch AMG wheels (450) or larger AMG designs.
**Confidence: Medium.** The MBUSA configurator confirms 21" base and
22" on 580 but **does not call out a Pinnacle-specific wheel**. In
practice Pinnacle cars on US dealer lots commonly carry the AMG Line
package (and therefore the AMG wheels) but Pinnacle does not *require*
it. **Do not infer trim from wheel size alone.**

**Interior materials.** Three-tier ladder:

- **Premium (450 base):** standard upholstery is **MB-Tex** (Mercedes'
  branded leatherette). Leather is an extra-cost option.
- **Exclusive:** upgrades to leather standard; adds multi-contour
  front seats with massage and heated 2nd-row seats.
- **Pinnacle:** layered on Exclusive — adds Air Balance cabin air
  system, heated/cooled front cupholders, Head-Up Display, MBUX
  Interior Assistant (gesture sensing), and door-projected Mercedes
  star pattern courtesy lights.
- **GLS 580** ships with leather standard regardless of trim package
  (the 580 has no MB-Tex configuration in the US).

Nappa leather ("Exclusive Nappa") is a separate paid upgrade above
standard leather on all three trims — it is **not** synonymous with
the Exclusive trim package. The photo tell for Nappa is leather that
wraps the **dashboard top and upper door panels**, not just the seats.
**Confidence: Medium-High.**

**Headliner.** Standard is microfiber/cloth in black, crystal grey,
or macchiato beige. A true Alcantara/suede headliner is part of the
optional **Black Exclusive Nappa Leather** package, not a Pinnacle-
standard item. From photos, suede headliner looks distinctly
napped/velvety in oblique light versus the flatter weave of standard
microfiber. **Confidence: Medium** — hard to call confidently from a
single dealer interior shot; ask for a close-up of the A-pillar.

**Exterior trim / badging.** No exterior badge announces Pinnacle —
the only rear badging is `GLS 450 4MATIC` or `GLS 580 4MATIC`.
Chrome window surrounds are the default; the **Night Package**
swaps them and the roof rails for high-gloss black, and the **AMG
Line** adds restyled bumpers, body-color cladding, and the diamond-
block grille (vs. Pinnacle-standard louvered chrome grille).
**Confidence: High** on the badging absence; **Medium** on which
chrome bits are universal vs. package-dependent.

**Lighting signature.** Standard 2024 GLS headlight is **LED High
Performance / Multibeam LED**. The MULTIBEAM signature has a
distinctive horizontal LED bar with subordinate brackets above. True
**Digital Light** (the multi-pixel projection system that can paint
lane lines and warning symbols on the road) is **not standard on
Pinnacle in the US** — Mercedes manuals and dealer literature treat
it as an optional or rare feature on this model year. From photos
the two systems look nearly identical when off; with the lights on
you can sometimes spot Digital Light by the much finer pixel
texture in the projector lens. **Confidence: Low** — practically
impossible to confirm from a typical static dealer photo. Treat as
`needs-validation` from the build sheet.

**Illuminated running boards.** Listed as a feature of the GLS 580
and as an available option on lower configurations. Not exclusively a
Pinnacle feature. Photo tell: a horizontal LED strip on the upper
edge of the running board, visible in a side or low-angle shot with
the door open. **Confidence: Medium.**

**Bottom line on trim verification:** No exterior tell distinguishes
Pinnacle from Premium/Exclusive. Interior tells (Air Balance vents,
HUD, door-star projectors, multi-contour seat upholstery pattern)
help but are easy to miss in typical dealer interior shots. **Verify
Pinnacle from the Monroney, not photos.**

---

## 2. Package presence tells from dealer photos

How to read the buyer's must-have and nice-to-have packages off
standard listing photography. "Listable" = you can usually see it in
the basic photo set; "Demand close-up" = you need to call and ask.

**Burmester 3D Surround Sound** (nice-to-have). Two Burmester systems
exist on the X167 GLS: standard Burmester (13 speakers) and the 3D
high-end system (26 speakers, or 29 in some configurations, with
LED-illuminated tweeters and 6 height-channel drivers in the
headliner). Photo tells:

- **Speaker count:** 3D system adds visible grilles in the A-pillars,
  the headliner above the front row, and a center speaker grille on
  the dashboard top. Standard system lacks the headliner drivers.
- **Illuminated tweeters:** the 3D system's tweeters in the
  A-pillars and front doors **light up** with an amber/white halo
  when the ignition cycles. Some dealer photos catch this; if so,
  it is high-confidence proof of the 3D system.
- **Door panel badge:** both systems carry an etched `Burmester`
  badge on the front door speaker grille. **Standard Burmester also
  has this badge** — its presence does not prove the 3D upgrade,
  only that some Burmester system is installed.

**Confidence: High** on the badge meaning; **Medium** on counting
headliner speakers from typical photos (you need a front-of-cabin
overhead shot). **Listable.**

**Acoustic Comfort Package** (must-have). Laminated acoustic glass on
front and rear side windows plus extra door insulation. Visual tells:

- A **small mesh pattern** etched into the windshield (and sometimes
  the front side glass) where the toll transponder / radar sees
  through the metallized acoustic film. Documented on MBWorld for
  the 2024 GLS 450 — a roughly fingertip-sized clear/mesh window in
  the upper windshield.
- Side glass laminated marking: most laminated automotive glass
  carries a small etched code in the lower corner of each window
  (look for "Lam" or "AS-1" instead of "AS-2"). Standard tempered
  side glass is marked "AS-2."

**Confidence: Medium.** The windshield mesh is real and photographable
but rarely featured in dealer shots. Side-glass etching is
theoretically visible in a close-up of the lower corner but never in
a standard listing photo. **Demand close-up** of the windshield-top
and a lower-corner shot of a rear side window.

**Warmth & Comfort Package** (must-have). Adds heated front and rear
armrests, heated steering wheel, and rapid front-seat heating. (The
heated rear seats themselves come with the Exclusive trim package on
the 2024 GLS, so do not double-count.) Photo tells:

- **Heated steering wheel button:** small steering-wheel-with-waves
  icon in the row of steering-wheel control buttons on the lower left
  spoke. Photographable in any clear close-up of the steering wheel.
- **Heated rear armrest:** no visible exterior control; the heat
  switch lives in the climate menu on the MBUX screen. **Not
  photographable.**
- **Heated front armrest:** same — software-controlled, no visible
  button.

**Confidence: Medium-High** on the steering wheel button; **Low** on
the armrests. **Demand close-up** of the steering wheel hub if the
package is critical to scoring.

**Driver Assistance Package** (nice-to-have). Adds Distronic active
cruise, Active Lane Change, Active Brake Assist with cross-traffic,
and Active Steering Assist. Hardware tells:

- **Stereo camera mount** on the windshield behind the rear-view
  mirror. **Every 2024 GLS has the basic camera housing** for the
  standard ADAS features, so its presence does not prove the package.
  The Driver Assistance pack adds processing software, not visible
  hardware.
- **Radar emitter** is behind a body-color panel in the lower
  front bumper grille — also present on the base car.
- **Distronic button** on the steering wheel left spoke is a
  reasonable software-presence tell on the dashboard close-up, but
  again is wired to underlying hardware that's standard.

**Confidence: Low** for photo verification. This package is almost
impossible to confirm visually — go to the Monroney. **Demand build
sheet.**

**Executive Rear Seat Package / Plus** (nice-to-have, 6-seat only).
The package itself requires the captain's-chair configuration. Tells:

- **Center console between captain's chairs** — a fixed console with
  cupholders, USB ports, wireless charging pad, and (Plus variant)
  the MBUX rear tablet in a high-gloss black docking station.
- **Pillow headrests** on the captain's chairs (Plus variant) — large,
  squared, separately-pillowed leather headrest covers vs. the
  standard integrated headrest shape.
- **Five-zone climate panel** mounted on the rear of the front
  center console with its own MBUX-style touch screen.
- **Power rear sunshades** — Plus variant only — the manual pull
  shades on the rear side windows are replaced by powered shades
  with a button at the rear of the front console or on the rear
  door switch panel.

**Confidence: High.** The center console between captain's chairs is
the cleanest single tell — if a listing shows captain's chairs
**without** the fixed console, the car lacks the Executive Rear Seat
package even if the dealer claims otherwise. **Listable** in the
typical 2nd-row interior shot.

**Trailer hitch (factory).** Mercedes' factory trailer-hitch option
on the X167 GLS uses a **receiver that is hidden behind a small,
removable lower-bumper plate** when not in use, not an always-exposed
ball mount. Increased-towing option 557 is factory-only and can't be
retrofitted. Photo tells:

- A horizontal **seam or trim panel** in the lower rear bumper just
  below the license plate area is the access door for the receiver.
  Cars without the option have a smooth lower bumper here.
- The receiver tube itself is not visible from a standard rear photo.

**Confidence: Medium** — the bumper seam is photographable but easy
to miss and easy to confuse with normal panel gaps. Demand a straight-
on rear photo at bumper height if a hitch is a hard requirement.

---

## 3. Seating configuration verification — 7-seat vs 6-seat

CONTEXT.md tags this as the most failure-prone listing field; verify
from photo, never from the dealer's "seating capacity" entry.

**Diagnostic photo: 2nd-row interior shot through an open rear door,
shot roughly from hip-height looking across the cabin.** This is the
single most useful image. If it is not in the listing, request it
explicitly before any further work.

**Bench (7-seat) tells:**
- One continuous cushion across the full cabin width with a
  visible center seatbelt anchor / buckle in the seat itself.
- Three headrests visible from behind when the rear hatch is open.
- A pull-down center armrest (when deployed) is integrated into the
  bench and folds flat when not in use.
- One-touch power-fold buttons in the cargo area collapse all three
  rows.

**Captain's chairs (6-seat) tells:**
- Two clearly separate seat shells with a **gap between them**.
  Either a fixed center console (with Executive Rear Seat Package)
  or an open pass-through to the third row (without the package).
- Two headrests visible from behind.
- Each chair has its own armrests on **both** sides.
- Easy-access "tip-and-slide" feature works on the passenger side
  only; on the bench layout it works on both sides.

**Year-specific note for 2024.** The X167 GLS hasn't changed seating
hardware since the 2020 launch, so 2020–2024 photo references are
all directly applicable. No mid-cycle redesign of the 2nd row.
**Confidence: High.**

**Reconfiguration risk.** Captain's chairs **cannot be swapped for a
bench by the dealer** — they are different body harness, different
floor mounts, different seat tracks, and the option is locked at the
factory. A car built as 6-seat stays 6-seat for life and vice versa.
Photo evidence of either configuration is therefore a permanent fact
about that VIN. **Confidence: High.**

---

## 4. Color verification and 2024 GLS factory color codes

Door-jamb data plate location: **driver's-side B-pillar sticker**,
fourth row of values, labeled with a paint code (sometimes prefixed
`Farbe` or just listed as a 3- or 4-digit number). Mercedes paint
codes for current production are 3-digit numeric (`989`, `197`, `775`)
with an optional 4-digit metallic-suffix variant (`6989` for metallic
emerald green, `5842` for metallic twilight blue).

### 2024 GLS factory blue / green colors of interest

| Color name | Paint code(s) | Notes / confusion risk |
|:--|:--|:--|
| Emerald Green Metallic | 989 / 6989 | The buyer's target green. Deep jewel green, reads near-black in shade. |
| Twilight Blue Metallic | 842 / 5842 | The buyer's target blue. Mid-saturation dusk navy. |
| Brilliant Blue Metallic | 896 / 5896 | **Confusion risk** — brighter, more saturated royal blue. Common on 2024 dealer lots; easy mistake for Twilight in studio lighting. |
| Cavansite Blue Metallic | 890 / 5890 | Bluish-green / teal lean. Distinct from both targets but sometimes mistakenly labeled "blue" in dealer feeds. |
| Sodalite Blue (Manufaktur) | Manufaktur paid color | Very deep navy, near-black. Rare on US 2024 GLS — premium Manufaktur option. |

**Confidence: High** on Emerald Green and Twilight Blue codes (cross-
referenced across PaintRef and TouchUpDirect for 2024 Mercedes).
**Medium** on the full 2024 blue lineup — Cavansite and Brilliant
Blue availability varies year to year; confirm against the Monroney
or build sheet on any candidate that isn't clearly Emerald Green or
Twilight Blue.

**Photo-color verification tricks:**
- **Always compare two photos in different light** — one exterior
  daylight, one shadow or garage. Twilight Blue stays clearly blue
  in both. Emerald Green can read near-black in shade but should
  show green hue at the panel highlights even then.
- **Watch for HDR/post-processing flattening.** Heavy edit pulls
  midtones toward neutral grey — colors look more muted than reality.
  The reverse trick (oversaturated showroom photo) makes a Brilliant
  Blue look near-Twilight.
- **Reflection check:** look at how the body color reads in the
  curved reflections on neighboring cars' paint or the dealer lot
  asphalt. A real metallic shows fine sparkle in direct sun; a
  HDR-flattened photo loses the flake.
- **Demand a paint-code photo of the B-pillar sticker** for any
  serious candidate. This is the only source of ground truth.

---

## 5. Common dealer photo tricks — counter-moves

Patterns to flag in franchise-dealer listings. None of these prove
fraud — they are just standard photo-merchandising practices that can
hide real defects. For each, a specific photo request that defeats it.

- **Stock-photo substitution.** Listing uses MBUSA marketing renders
  or a different VIN's photos. **Counter:** demand a photo of the
  driver-side door jamb sticker (VIN, paint code, plant code legible)
  and a photo of the odometer showing current mileage. Both must
  match the listed VIN and mileage.

- **Cropped wheel shots hiding curb rash.** Wheels photographed from
  3/4 angle only, never straight-on, or always cropped at the spoke.
  **Counter:** demand four straight-on photos, one per wheel face,
  shot perpendicular to the wheel. Curb rash will be obvious on the
  outer rim lip.

- **Studio lighting / heavy retouch masking paint condition.**
  Polished-glass-on-asphalt look, no dust, no reflection variance,
  unrealistic body line definition. **Counter:** demand a daylight
  outdoor photo at three angles (front 3/4, straight side, rear
  3/4) shot **before wash and detail**, or after the car has sat in
  the sun for an hour. Swirl marks, paint chips, and orange peel show
  up in flat outdoor light that studio retouch can't hide.

- **Shared rooftop photography.** Dealer groups (AutoNation, Sonic,
  Lithia) often have one regional photo lot and rotate inventory
  through it. Photos look stylistically identical across dozens of
  cars. The car may have moved since photography. **Counter:** ask
  when photos were taken and whether the car is physically at the
  selling location today. Demand a fresh phone photo of the car
  in its current parking spot.

- **Overhead-only or no straight-side photo.** Three-quarter
  marketing angles only; no perpendicular side shot. Hides door dings,
  rocker-panel damage, and ride-height irregularities. **Counter:**
  demand one straight-side photo per side, shot from roughly fender
  height at 90 degrees to the centerline.

- **Angle bias hiding a specific damage zone.** Every photo is from
  front-3/4 left — the entire passenger rear is unseen. **Counter:**
  request all eight clock positions (12, 1:30, 3, 4:30, 6, 7:30, 9,
  10:30) shot at standing eye level.

- **Old delivery-day photos reused for resale.** Listing photos look
  immaculate; Carfax shows 15,000 miles and three service visits. The
  car may have been photographed at original delivery and never
  reshot. **Counter:** demand date-stamped photos taken in the last
  7 days, plus an odometer photo. EXIF data on the supplied images
  (if not stripped) confirms the date.

- **Interior over-shadowed to hide wear.** Front seats and steering
  wheel photographed in low contrast, dark areas crushed. Hides
  bolster wear, steering-wheel rub-through, and seat-edge cracking.
  **Counter:** demand a flash or daylight close-up of the driver's
  outer seat bolster, the steering wheel hub (top arc — the highest-
  wear zone), and the driver's-side accelerator pedal rubber.

---

## 6. Worked example — Fredericksburg 450 candidate

VIN `4JGFF5KE0SB######` (production sequence redacted; full VIN held
in session context). VIN-decode confirms **2025 GLS 450 4MATIC**,
Tuscaloosa-built (year-letter `S` = 2025 per FMVSS 565).

### Findings confirmed by end-to-end calibration test

The candidate was evaluated against the live dealer listing at
Mercedes-Benz of Fredericksburg and against direct photo inspection.
Confirmed:

- **Year:** 2025 (per VIN position 10 = `S`). Within scope per
  CONTEXT "MY2024 or newer" — but originally a Pass under the
  pre-widening 2024-only spec.
- **Color:** Obsidian Black Metallic. **Off-spec** per CONTEXT
  acceptable factory colors (Emerald Green Metallic, Twilight Blue
  Metallic). Resolved from listing metadata, not from a color-
  ambiguous photo.
- **Seating:** **6-seat captain's chairs** (confirmed by direct
  photo inspection of the listing's 2nd-row image set). The
  listing's feature list claimed BOTH "Captain Chairs (6 seater)"
  AND "7-Seat Configuration" — a classic dealer-data-pipeline
  conflict; photos resolve it.
- **Trim:** Almost certainly **Premium** (not Pinnacle). The
  listing's feature list explicitly includes "MB-Tex Upholstery,"
  which is the Premium-base upholstery; Exclusive upgrades to
  leather standard, and Pinnacle layers on top of Exclusive. The
  listing never claims Pinnacle. **Fails CONTEXT must-have.**
- **Burmester:** Listing claims "Burmester High End 3D Surround"
  but also lists "13 Speakers" — the 3D system has 26-29
  speakers. **The claim is contradicted by the spec** in the same
  listing; it's almost certainly just standard Burmester.
- **CPO:** Claimed by dealer in listing badging. NOT
  independently verified — needs 1-800-FOR-MERCEDES call with VIN
  per `references/mbusa-cpo-criteria.md`.

**Net verdict per CONTEXT:** PASS on three independent grounds
(off-spec color, Premium trim not Pinnacle, dealer-pipeline
inconsistency on Burmester). The model year is now in-scope after
the year-scope widening commit but the other three failures hold.

### Photo-request sequence (retained for future Fredericksburg candidates)

Retained as a workflow reference for any future Fredericksburg
candidate that clears the initial CONTEXT spec and warrants deeper
photo inspection beyond what the listing exposes. Send to the
Internet Sales / Product Specialist contact for the listing.
Suggested phrasing:

> "I'm interested in this GLS but need a few additional photos before
> I make the trip. Could you send the following, ideally taken in the
> next day or two with the car in its current parking spot?"

1. **Driver-side B-pillar door-jamb sticker.** VIN, paint code,
   plant code must be legible. (Confirms VIN + paint code +
   identifies the car as the one in the listing.)
2. **Current odometer reading.** Date-stamped if possible.
3. **Straight-on exterior, both sides.** Perpendicular, daylight,
   roughly fender height. (Catches door dings, rocker panel
   damage.)
4. **Four wheel faces straight-on.** One per wheel. (Catches curb
   rash.)
5. **Front cabin overhead through the open driver door.** Shows
   headliner speakers (Burmester 3D vs standard), dashboard top
   material (Nappa vs standard leather).
6. **Steering wheel hub, close-up.** Shows heated-wheel button
   (Warmth & Comfort indicator), Distronic button (Driver
   Assistance software tell).
7. **2nd-row through open rear door, hip-height across cabin.**
   Diagnostic for 7-seat bench vs 6-seat captains. If 6-seat,
   shows whether the Executive Rear Seat console is present.
8. **Windshield-top close-up.** Shows Acoustic Comfort metallic
   mesh window if present.
9. **Lower rear bumper, straight-on at bumper height.** Shows
   trailer-hitch access seam if present.
10. **A-pillar interior close-up.** Shows headliner material
    (microfiber vs suede) — relevant if shopping Nappa Exclusive
    option.

### What this enables

- **Confirms seating config** (independent of dealer claim).
- **Confirms color spec deviation** specifically — paint code from
  B-pillar settles whether it's Brilliant Blue, Cavansite, or
  something else loosely labeled "blue."
- **Confirms Burmester 3D** vs standard via headliner speaker count.
- **Confirms Warmth & Comfort** via heated-wheel button.
- **Confirms presence/absence of trailer hitch.**
- **Catches photo tricks** — date-stamped recent photos defeat
  stock-photo and old-delivery-photo issues.

### What this does NOT confirm

- **Pinnacle trim** — no exterior tell. Verify via Monroney pull.
- **Driver Assistance Package** — photo-invisible. Verify via Monroney.
- **Acoustic Comfort Package** — windshield mesh helps but is not
  definitive. Verify via Monroney.
- **CPO status** — independent verification via MB Customer
  Assistance Center (1-800-FOR-MERCEDES) with VIN, per
  `references/mbusa-cpo-criteria.md`.

### Read on dealer responsiveness

Note in `references/dealer-tier-list.md` how Fredericksburg responds
to this photo request. A dealer who sends all 10 photos within 48
hours without fuss is **KNOWN-GOOD**; one who pushes back, sends
only a subset, or claims "the car's already detailed, we don't have
time for that" is a signal — these are standard, reasonable requests
for a $75K+ purchase. Pattern of evasion on photos correlates with
pattern of evasion on data card and CPO inspection sheet later.

---

## Cross-references

- `CONTEXT.md` — packages, color preferences, seating policy. This
  file confirms the spec from photos.
- `references/gls-trim-decoder.md` — VIN decode and data-card
  workflow. Photo verification + data card together are the full
  Stage 3 verify pass.
- `references/mbusa-cpo-criteria.md` — CPO verification is a
  separate independent channel; photos don't speak to CPO status.
- `references/comp-pricing-framework.md` — package presence (from
  this file's photo tells) feeds the options-delta calculation in
  comp work.
- `references/dealer-tier-list.md` — dealer responsiveness to
  photo requests is a tier-list-updating signal.
- `references/negotiation-framework.md` *(to be rewritten)* —
  photo-confirmed cosmetic issues (curb rash, paint condition,
  interior wear) feed defect-anchored negotiation levers.

---

## Open calibration items

- **Pinnacle-specific wheel design.** MBUSA configurator does not
  break out a Pinnacle-only wheel option separately from 450/580
  standard. May not exist as a discrete option. Verify against the
  first real Pinnacle candidate.
- **Suede-headliner photo distinction** vs standard microfiber is
  Medium confidence; sharpen against a real example.
- **Trailer-hitch lower-bumper seam visibility** depends on lighting
  and camera angle. Confirm against a real factory-hitch candidate.
- **2024 blue lineup** — Cavansite and Brilliant Blue availability
  varies year to year; verify against MBUSA's 2024 GLS configurator
  archive if a candidate's paint code doesn't match the four
  expected codes above.

---

## Sources

- [MBUSA — 2024 GLS SUV future-vehicle page](https://www.mbusa.com/en/future-vehicles/2024-mercedes-benz-gls-suv)
- [MBUSA — Build Your Own GLS SUV configurator](https://www.mbusa.com/en/vehicles/build/gls/suv)
- [MBUSA — 2024 GLS Owner's Manual PDF](https://www.mbusa.com/content/dam/mb-nafta/us/owners/manuals/2024/2024-owners-manuals/MY24_GLS%20SUV%20Owner's%20Manual.pdf)
- [MBUSA — Driving Assistance package (2024 GLS MBUX)](https://www.mbusa.com/en/owners/manuals/gls-suv-2024-03-x167-mbux/quick-guide/functions-of-the-driving-assistance-package)
- [Mercedes-Benz Cutler Bay — 2024 GLS Trim Level Comparison](https://www.mbcutlerbay.com/2024-mercedes-benz-gls-suv-trim-level-comparison/)
- [Mercedes-Benz of Kansas City South — 2024 GLS Trim Levels and Price](https://www.mbkcsouth.com/2024-mercedes-benz-gls-trim-levels-and-price/)
- [Edmunds — 2024 GLS-Class Trims Comparison](https://www.edmunds.com/mercedes-benz/gls-class/2024/trims/)
- [MBWorld — 2024 GLS 450 Windshield showing metallic mesh / Acoustic Comfort](https://mbworld.org/forums/gls-class-x167/872755-2024-gls-450-windshield-showing-metallic-mesh-acoustic-comfort-package.html)
- [MBWorld — GLS 6 vs 7 seat arrangement question](https://mbworld.org/forums/gls-class-x167/785705-6-vs-7-seat-arrangement-question.html)
- [MBWorld — GLS regular AMG vs Night Package vs no AMG](https://mbworld.org/forums/gls-class-x167/847190-gls-regular-amg-package-night-package-no-amg.html)
- [Burmester — GLS audio systems](https://www.burmester.de/en/automotive/mercedes-benz/gls/)
- [PaintRef — Mercedes Emerald Green 989/6989 cross-reference](https://paintref.com/cgi-bin/colorcodedisplay.cgi?color=Emerald+Green&con=1&make=Mercedes&rows=50)
- [PaintScratch — Emerald Green 989 touch-up for 2024 GLS](https://www.paintscratch.com/touch_up_paint/Mercedes-Benz/2024-Mercedes-Benz-GLS-Emerald-Green-989.html)
- [TouchUpDirect — Mercedes-Benz GLS-Class paint codes](https://touchupdirect.com/touch-up-paint/mercedes-benz/gls-class/)
- [Mercedes-Benz of Scottsdale — 2024 GLS exterior color options](https://www.mbscottsdale.com/blog/what-are-the-exterior-color-options-for-the-2024-mercedes-benz-gls-suv/)
- [Mercedes-Benz of Denver — GLS SUV seating configurations](https://www.mercedesbenzofdenver.com/blog/2024/december/23/what-are-the-different-seating-configurations-for-the-mercedes-benz-gls-suv.htm)
