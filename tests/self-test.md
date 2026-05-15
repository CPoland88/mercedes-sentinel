# Skill self-test

This is a regression test for the `used-car-finder` skill. Run these
synthetic listings past Claude with the skill loaded; verify the
verdict matches the expected output.

To run: paste each listing block (between the `===` markers) into a
fresh conversation with the skill loaded. Ask Claude: "Evaluate this
listing." Compare to the expected verdict.

A regression is when Claude's verdict differs from the expected one in
the **VERDICT line** or the **Next step**. Wording variations in the
explanation are fine.

---

## Test 1: Tier 1 grandpa car

```
===
2008 Buick LeSabre Custom Sedan
$3,400
68,000 mi
Posted 5 weeks ago in Akron, OH

Selling my late father's LeSabre. He bought it new in 2008 and drove it
mostly to church and the grocery store. Garage kept its whole life.
I'm the executor of the estate.

Clean title, no accidents. 68K original miles. Service records from the
Buick dealership through 2022 are in the glove box; after that he just
went to the same indie shop in town for oil changes.

Cloth seats, no leather. Steel wheels with covers (the base trim).
Radio works, AC blows cold, all power options work. Some small scratches
on the rear bumper.

Selling because we're settling the estate. Price is firm. I'm not
interested in trades and don't have time to ship or hold for finance
contingencies. Cash, local pickup in Akron.

Seller: Margaret Whitfield. Joined FB 2011. 2 Marketplace ratings (both
positive, both from non-vehicle sales). One active listing (this car).
No timeline activity except occasional family photos.
===
```

**Expected verdict:** TIER 1 (potentially TIER 2 because LeSabre is
older/grandpa rather than mainstream). Engine: 3800 Series II V6, chain.
Seller signal: GREEN. Body text: highly specific personal narrative,
honest cosmetic disclosure, real estate-sale context. Estimated fair:
$3,000 to $4,000 depending on regional pricing. Next step: VIN +
Carfax + PPI (focus on intake manifold gasket, common 3800 issue).

---

## Test 2: Curbstoner

```
===
2013 Honda Civic LX Sedan
$8,900
89,000 mi
Posted 1 day ago in Phoenix, AZ
Excellent condition

Beautiful Honda Civic LX, runs and drives perfect!! Clean title in
hand, no accidents, one owner garage kept!! Brand new tires, fresh oil
change, new brakes all around!! Cold AC!! Power everything works!!
Must see in person!! Serious buyers only!! Cash deal only!! Title in
hand ready to transfer!!

Seller: Carlos Mendez. Joined FB 5 months ago. 22 Marketplace ratings
(all from vehicle sales). Active listings: this Civic, a 2014 Nissan
Sentra, a 2011 Toyota Corolla, a set of 16" rims, a Honda K24 starter
motor. Recently sold: 2009 Mazda3, 2012 Hyundai Elantra, 2008 Honda
Accord, three tires.
===
```

**Expected verdict:** KILL (curbstoner). 3 vehicles + parts +
new-account/high-ratings combo + marketing-copy text. Auto-eliminate
without engaging.

---

## Test 3: Wire-fraud scam

```
===
2017 Toyota 4Runner SR5
$10,500
85,000 mi
Posted today in Salt Lake City, UT
Like new condition

Reluctant sale of my late father's 4Runner. He passed away last month
and I'm settling his estate. Truck is in storage in Salt Lake City; I
live in Florida and cannot travel.

Clean title, full Toyota dealer service. Selling well below market to
move it quickly. I can arrange shipping through a service that will
hold payment in escrow and let you inspect for 5 days. Contact me at
[gmail address] for photos and to discuss.

Seller: Patricia Lee. Joined FB 2 weeks ago. 0 ratings. One listing
(this 4Runner). No timeline. Stock-image profile photo.
===
```

**Expected verdict:** KILL (scam). Price 50%+ below market for a 2017
SR5 4Runner with 85K. Deceased-relative + out-of-state + storage +
escrow + Gmail combo. Brand new account. Do not engage.

---

## Test 4: Risky model, otherwise green-flag seller

```
===
2013 Jeep Compass Latitude
$5,200
102,000 mi
Posted 2 weeks ago in Burlington, VT

Selling my 2013 Compass. I bought it new in 2013 and have driven it as
my daily ever since. Maintenance has been at the Jeep dealer every 5K.
Clean title, no accidents. The CVT was replaced under warranty in 2019
at 65K (under the extended powertrain).

Tires are about 50% worn, brakes were done last year. Some rust on the
rocker panels (it's Vermont). AC blows cold, heat works, 4WD engages.

Selling because I'm switching to a small EV for commute. Cash, local
pickup. Happy to share records.

Seller: David Park. Joined FB 2009. 8 Marketplace ratings, all
non-vehicle. One active listing (this Jeep). Family photos in
timeline.
===
```

**Expected verdict:** WATCH or KILL. Seller profile is GREEN (real
person, honest disclosures, dated maintenance). But the model is
explicitly on the AVOID list: Jeep Compass has documented CVT
failures, electrical issues, and poor long-term value. CVT was already
replaced once at 65K; on a CVT-Compass that's normal and the second
one fails too. Rust on rockers is a Vermont reality. Recommend the
user pass and look at a Tier 1 alternative in the same price range
(Civic, Corolla, Mazda3, Forester).

---

## Test 5: Established account, no ratings, real owner

```
===
2009 Toyota Matrix S
$4,100
145,000 mi
Posted 3 weeks ago in Sacramento, CA

2009 Toyota Matrix S, 4-cyl, automatic. I'm the second owner; I bought
it in 2014 from the original owner with 60K. Cosmetically it's rough
(California sun has faded the clear coat on the roof), but mechanically
it's been bulletproof.

Service: oil changes every 5K (used to be Jiffy Lube, now Walmart).
Transmission fluid done at 90K and 130K. Coolant flushed at 100K.
Spark plugs at 120K. Front brakes 60K and 130K. Set of Continental
tires at 130K, still have most of the tread. 12V battery 2022.

No accidents (one parking-lot scrape on the rear bumper that I never
bothered fixing). Title clean and in my name.

Selling because my daughter is getting her license and we're getting
her something newer. Asking $4,100, will consider reasonable offers
once you've seen the car. Cash, local pickup. PPI welcome at any shop
you pick.

Seller: Jim Hendrickson. Joined FB 2014. 0 Marketplace ratings. One
active listing (this car). Timeline: lots of personal posts, family,
work, hobbies. Real-looking profile.
===
```

**Expected verdict:** TIER 1. Engine 2ZR-FE 1.8L chain (reliable). 0
ratings is a yellow flag offset by detailed personal narrative, dated
specific maintenance, and authentic profile. Fair value $3,800 to
$4,500 for an S trim at 145K. Cosmetic rough = mild negotiation lever
($200 to $300 off). Next step: VIN + Carfax + PPI (check for 2AR oil
consumption history; the 2ZR is mostly fine but worth confirming).

---

## How to run the test

1. Open a new Claude conversation.
2. Make sure the `used-car-finder` skill is loaded (e.g., paste the
   SKILL.md contents, or have it available via skill autoloading).
3. Paste one of the listing blocks between the `===` markers.
4. Ask: "Evaluate this listing."
5. Compare the VERDICT line and the Next step to the expected output.

If any verdict regresses, check the reference file most relevant to
the failure mode (scam-patterns for scams, curbstoner-playbook for
curbstoners, reliable-makes for model classification) and refine.

## Scoring

Pass: VERDICT matches and Next step matches the spirit of the expected
output.
Soft pass: VERDICT matches but reasoning is incomplete.
Fail: VERDICT differs (e.g., labels a scam as TIER 1).
