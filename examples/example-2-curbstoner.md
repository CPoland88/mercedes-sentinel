# Example 2: Curbstoner (auto-eliminate)

This is a synthetic example showing a typical curbstoner listing and how
the skill should detect it.

## Listing card

```
2012 Toyota Camry SE
$7,200
98,000 mi
Posted 2 days ago in Houston, TX
Excellent condition
```

## Listing body text

> Beautiful 2012 Toyota Camry SE in excellent condition!! Clean title in
> hand, runs and drives great, no issues!! One owner garage kept, never
> any accidents.
>
> Brand new tires, fresh oil change, brand new brakes!! Cold AC, hot
> heat, all power options work perfect!! Sunroof, leather, premium
> audio!! Backup camera!!
>
> Must see in person to appreciate!! Serious buyers only!! Cash deal
> only!! Title in hand ready to transfer!!
>
> Call or text [phone number]

## Seller profile

- Profile: Mike Johnson
- Joined Facebook: 8 months ago
- Marketplace ratings: 14 (all from vehicle sales in the last 6 months)
- Active listings: this Camry, a 2014 Nissan Altima, a 2010 Ford Fusion,
  a set of 17" wheels and tires, a 2.4L Camry coil pack
- Recently sold: a 2008 Honda Civic, a 2011 Hyundai Sonata, a 2013 Kia
  Optima, two transmission fluid jugs
- Timeline: no personal posts; profile photo is a generic landscape

## How the skill should evaluate this

```
VERDICT: KILL
Year/Make/Model/Trim: claimed 2012 Camry SE, trim unverified (no
  interior photos shown; SE has alloys + cloth/leatherette + paddle
  shifters)
Ask: $7,200 / Estimated fair private-party: $6,000 to $7,500 if trim
  verifies as SE with leather package; less otherwise
Engine: 2AR-FE 2.5L I4, chain (good)
Known issues for this gen: 2012 was the first year of the new platform;
  early-build issues mostly addressed. No major red flags for this gen
  IF a real one.
Seller signal: RED. Auto-eliminate.
  Reasons:
    1. 4 active vehicle listings + 3 recently sold vehicles in the last
       6 months. Curbstoner / unlicensed dealer.
    2. Car parts (wheels, coil pack, transmission fluid) listed
       alongside vehicles. Parting out cars on the side.
    3. Account joined 8 months ago + 14 Marketplace ratings (most from
       vehicle sales). Real new users do not accumulate vehicle
       ratings at this rate.
    4. Profile photo is generic; no personal timeline.
    5. Body text is pure marketing copy: triple-bang punctuation,
       buzzwords ("garage kept," "one owner," "must see"), zero
       specific dated maintenance, zero personal narrative.
    6. "Title in hand" mentioned twice; classic curbstoner verbal tic.
Body-text flags: "runs and drives great" filler, "must see in person,"
  no VIN offered, "cash only" with urgency
Deferred maintenance risk: UNKNOWN. The "brand new tires / brakes /
  oil" claim is unverifiable and is exactly what a curbstoner says
  to mask deferred maintenance.
Next step: WALK. Do not message. Do not drive to see it. The seller is
  flipping auction cars. Even if the specific car is fine, the
  consumer protections of a private-party sale do not apply, and
  curbstoners often hide salvage / odometer rollback / accident
  history.
```

## Why this is a curbstoner

The single highest-signal indicator is the **seller profile having 7+
vehicles + car parts**. Even if every other signal looked clean, that
alone is auto-eliminate.

Supporting signals:

- New account + many ratings is the classic curbstoner fingerprint.
- Marketing-copy body text with no specific dated services. A real
  owner can tell you when they did each service and how much it cost.
- "Title in hand" repeated. Real owners say "clean title" or just
  nothing.
- Generic profile photo, no personal timeline.

## What the skill should NOT do

- Do not ask the seller for the VIN. Don't engage. The user's time and
  attention are the scarce resource.
- Do not give the seller benefit of the doubt because the model is
  Tier 1. Tier 1 models attract curbstoners precisely because they
  hold their value.
- Do not suggest the user "verify in person." Driving to a curbstoner's
  parking lot wastes a Saturday and exposes the user to high-pressure
  sales tactics.
