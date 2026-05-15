# Curbstoner detection playbook

A **curbstoner** is an unlicensed dealer posing as a private seller on
Facebook Marketplace. They buy auction cars, salvage rebuilds, or trade-in
rejects, do cosmetic work, and resell them. They hide title problems,
flip-pattern, and prior commercial use.

State licensing exists specifically to make this harder; curbstoning is
illegal in most US states. But enforcement is thin, and FB Marketplace is
the easiest venue.

This guide walks the user through verifying that a private seller is
actually private.

## The core rule (highest signal)

**Count the vehicles on the seller's profile, including recently sold.**

Open the seller's profile from the listing. Look at both "Active listings"
and "Marketplace history" (or "Listings"). Count every vehicle listing in
both buckets.

- **Zero other vehicles**: green. They are selling their car.
- **One other vehicle (active or recently sold)**: yellow. Could be the
  spouse's car, could be a curbstoner. Look at body-text and account-age
  signals.
- **Two or more other vehicles total**: red. Auto-eliminate. Real private
  sellers do not flip cars on the side.

This single rule subsumes "this person is a mobile mechanic," "this person
runs a body shop," and "this person is a sequential flipper." Service
sellers always have a trail of sold cars; sequential curbstoners have one
active car at a time but a long history.

## Auxiliary rule: car parts for sale

If the seller has **car parts** (fenders, coil packs, fuel pumps, tires,
wheels, headlights) listed alongside the car, eliminate. They are parting
out other cars. This catches curbstoners who run a fresh profile per car
sale and so pass the vehicle-count rule.

## Account-age vs ratings calibration

Facebook shows two numbers on the seller's profile: when the account
joined Facebook, and the number of Marketplace ratings (the small "(N)"
next to the seller's name).

**Green flag combinations:**

- Joined 2008 to 2020, has a normal-looking timeline with photos, 0 to 15
  Marketplace ratings, real-person profile description. This is a regular
  person who occasionally sells things.
- Joined any year, very salty tone in the listing ("NO DEALERS!! I WILL
  NOT ACCEPT TRADES!! PRICE IS FIRM!!"). Counterintuitively, this is a
  strong green flag. Curbstoners try to sound welcoming and professional.
  Real private sellers are annoyed by tire-kickers.
- Detailed enthusiast description with personal context ("I bought this
  for school in 2020, upgrading to something bigger"). Specific dates and
  personal narrative are hard to fake.

**Yellow flag combinations (verify with other signals):**

- Established account (joined 2008 to 2020) but no Marketplace ratings.
  Could be a first-time seller, or could be a new curbstoner profile on
  an old account.
- New account (joined within last 12 months) with a normal profile and no
  ratings. First-time user is possible; verify with body text.

**Red flag combinations (auto-eliminate unless extraordinary):**

- Account joined within the last 12 months AND 8+ Marketplace ratings.
  Real new users do not accumulate ratings that fast.
- Any account with 20+ ratings where most are from vehicle sales.
- Marketing-copy tone in the description ("Beautiful one-owner garage-kept
  must-see clean title runs and drives great new tires brakes" etc.). Real
  private sellers do not write press releases.
- Account name is generic ("Mike Smith" with no profile photo and no
  timeline visible).

## Profile photo and timeline

Click into the seller's profile from the listing. Look at:

- Profile photo: is it a real person? A logo or stock car photo is a flag.
- Timeline: any non-Marketplace activity? Real people post about their
  lives. A profile that is 100% car listings is a flag.
- Friends list visible: usually a green flag.

## Listing body-text patterns

See `scam-patterns.md` for the full list. The curbstoner-specific ones:

- "Title in hand" (real owners say "clean title" or just nothing)
- "Runs and drives great" (filler phrase, signals nothing about the car
  and is a curbstoner verbal tic)
- "Selling for a friend" (escape hatch for not knowing service history)
- "Just got it from auction" (auction is fine to disclose, but flagged)
- Price-firm bumpers, all-caps NO TRADES, but the price has been reduced
  twice. The salty tone is performance.
- Listed in multiple cities (use FB's "view listing in original city"
  link to check).

## Title status claims

- "Clean title" stated explicitly: verify with the actual title document at
  meet-up. Curbstoners lie about this.
- "Rebuilt title," "salvage title," "branded title": this is a project car.
  Insurance is harder. Resale is harder. Walk unless user is shopping
  projects.
- "Title in hand": fine, but no extra credit. Curbstoners use this phrase
  to imply legitimacy.
- No title mentioned: ask.
- "Bill of sale only" or "lost title": run. Either the car is stolen, or
  the seller does not legally own it.

## Multi-state listing trick

A curbstoner with inventory may list the same car in multiple metro areas
to maximize reach. FB shows the original posting city in small text. If
the original city is 200+ miles from the seller's profile location, ask
why.

## Verification script (what to say to the seller)

Before driving anywhere, message the seller:

1. "Hi, is this car still available?" (Standard opener, gauges
   responsiveness.)
2. "Can I get the VIN? I want to pull a Carfax." A real owner gives the
   VIN. A curbstoner often refuses or says "I'll show it in person."
3. "Are you the registered owner?" Honest sellers say yes. Curbstoners
   either lie (verify against the title) or hedge ("selling for a friend,"
   "got it from my uncle").
4. "How long have you owned it?" Curbstoners give fuzzy answers or single-
   digit weeks/months. Real owners give years.
5. "Why are you selling?" Real reasons: moving, upgrading, new baby, kid
   left for college. Curbstoner reasons: "not enough time to drive it,"
   "need the money," "got a company car."

If any answer feels rehearsed, evasive, or contradicts the listing, walk.

## Mileage check at meet-up

Before paying, look at the odometer and the Carfax. Curbstoners sometimes
roll back mileage. If the odometer reads lower than the last service
record on the Carfax, the car has been clocked. This is fraud. Walk and
report.

## State-specific resources

If the user has lingering doubt, most state DMVs publish a list of
licensed dealers. A "private seller" who turns up on the licensed-dealer
list is a curbstoner using a personal profile to dodge consumer-protection
disclosures.

## Quick decision table

| Signal | Action |
|---|---|
| 2+ vehicles on profile | Eliminate |
| Parts for sale alongside car | Eliminate |
| New account + many ratings | Eliminate |
| Marketing-copy body text | Eliminate |
| Refuses to give VIN | Eliminate |
| Title is rebuilt/salvage | Eliminate (unless user is shopping projects) |
| Established account + salty private-seller tone | Strong proceed |
| Real personal narrative in description | Strong proceed |
| New account + normal description + 0 ratings | Verify carefully, proceed |
