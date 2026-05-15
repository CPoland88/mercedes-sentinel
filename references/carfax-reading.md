# Reading a Carfax report

A Carfax is the single most useful document in a used-car purchase, but
only if you know what to look for. The headline summary ("No accidents
reported, 32 service records") understates and overstates at the same
time: it misses small defects and overweights cosmetic events.

This guide walks through what to actually extract.

## What to extract, in order

1. **Owner count and ownership pattern**
2. **Title history (state-by-state)**
3. **Accident records**
4. **Service-record density and consistency**
5. **Specific service events (timing belt, transmission fluid, brakes,
   battery, recalls, major repairs)**
6. **Mileage progression**
7. **Inspection / registration history**
8. **Open recalls**

## Owner count: reconcile Carfax with seller's claim

The Carfax owner count and the seller's claim often differ. Both can be
honest.

- Carfax counts every title transfer, including dealer-to-dealer flips
  in the first month after manufacture.
- A seller may say "I'm the second owner" meaning they bought it from
  the original retail owner, even if Carfax shows 4 owners (dealer ->
  original owner -> trade-in -> dealer -> seller).

**Rule:** ignore the raw owner count. Look at the gap between owner
transitions. A 14-year-old car with 4 owners but where one owner held it
for 12 years is effectively a one-owner car. A 5-year-old car with 4
owners is a hot potato; ask why.

## Title history

- **All in one state**: green flag. Local car, easier to verify history.
- **Multiple states**: not bad, but verify each transition was a real
  move and not a title-washing trick (state-hopping to clean a branded
  title is a known curbstoner technique).
- **Branded title at any point** (salvage, rebuilt, flood, lemon-law
  buyback, junk): walk unless the user is shopping projects. Note that
  some states downgrade the brand on subsequent titles; if the Carfax
  shows "title issue" anywhere in history, it's still salvage.

## Accident records

Carfax accident records come from:

- Police reports (only if the police were called)
- Insurance claims (only if the owner filed)
- Body shops (only some)
- DMV records (only severe)

This means **"No accidents reported" is not the same as "no accidents."**
A minor fender-bender paid out of pocket leaves no trace.

What to do:

- If Carfax shows accidents, read the severity. "Minor damage to left
  front" with continued service afterward is usually fine. "Severe
  damage" or "airbag deployment" is closer to a walk.
- If Carfax shows no accidents but the car has obvious mismatched paint,
  uneven panel gaps, or fresh body work, ask the seller and inspect
  carefully.
- Body work alone (without a reported accident) on the Carfax is a yellow
  flag. Ask about it.

## Service-record density and consistency

This is the most overlooked part of the Carfax and one of the most
informative.

**Good pattern:**

- 20+ service records over the car's life
- Mostly from the same dealership or independent shop (proves consistent
  care)
- Regular oil changes at roughly 5K to 10K intervals
- Major services hit at expected mileage (transmission fluid, coolant,
  spark plugs, timing belt where applicable)
- A few non-routine repairs that were addressed promptly

**Bad pattern:**

- Sparse records (4 or 5 over 10 years means the car was DIY'd at best,
  neglected at worst)
- Service at many different shops (could be normal, but cluster of
  cheapest shops is a flag)
- Long gaps with high mileage accumulation (car was used hard with no
  maintenance)
- Major service events not present at expected mileage (no transmission
  fluid in 130K miles is a flag)
- Multiple visits for the same issue in a short window (recurring problem
  that may not be fixed)

The number of service records is roughly proportional to how well the
car was cared for. A car with 30+ records and an active recent
maintenance history is among the safest used-car bets.

## Specific service events to look for

Pull these out and note when they were last done. Use the mileage at
time-of-service, not the date.

| Service | Typical interval | Why it matters |
|---|---|---|
| Engine oil + filter | 5K to 10K | Most-recent date should be recent |
| Transmission fluid (auto) | 30K to 60K | Skipped = transmission failure |
| Transmission fluid (CVT) | 30K | CVT failure if neglected |
| Coolant flush | 60K to 100K | Overdue = head gasket risk |
| Spark plugs | 30K (copper) / 100K (iridium) | Iridium usually overdue |
| Timing belt + water pump | 90K to 105K | See `timing-chain-vs-belt.md` for cost by engine |
| Brake fluid flush | 30K | Often skipped, low priority |
| Brake pads (front) | 30K to 50K | Note last replacement and current |
| Brake pads (rear) | 60K to 100K | Often original on 100K cars |
| Tires | 50K or 6 years | 6+ years old, replace regardless of tread |
| 12V battery | 5 to 7 years | Note last replacement |
| Power steering fluid | 100K | Often skipped, low priority |
| Differential / transfer case (AWD) | 60K | AWD vehicles only |

For each service: subtract the last-done mileage from the current
mileage. If the result is at or past the typical interval, budget for
that service in the negotiation case.

## Hybrid and EV-specific Carfax notes

- **High-voltage battery replacement**: if the Carfax shows the hybrid /
  EV battery was replaced, the meter starts over. A 12-year-old Prius
  with a 2-year-old battery is much safer than a 6-year-old Prius with
  the original.
- **High-voltage battery NOT replaced on a 10+ year hybrid**: original
  battery, in or near its failure window. Budget for replacement. See
  `negotiation-framework.md` defect-cost table for current refurb and
  lithium-conversion ranges by model.
- **IMA / hybrid system fault codes** logged in service history: ask
  what was done. Sometimes the battery was reconditioned, sometimes
  ignored.

## Mileage progression

Look at the mileage column over time. It should increase monotonically
at a roughly consistent rate.

- **Rate of accumulation**: average annual miles. 7K to 15K is normal.
  Under 5K is a grandpa car (good). Over 20K is a road-warrior commuter
  car (more wear).
- **Mileage that goes backwards**: odometer rollback. Walk and report
  to the state AG.
- **Long flat periods**: car was parked. Could be normal (snowbird
  storage); could be theft / impound / collision.

Compare the most recent Carfax mileage to the odometer in the listing
photos. If the photo shows less mileage than the most recent Carfax
record, the car has been driven backwards or the listing is stale.

## Inspection / registration history

Annual state inspections (in states that have them) show whether the car
has been continuously road-legal. A gap in inspections means the car was
either off the road for a year or registered in a non-inspection state.

A **failed inspection followed by immediate re-inspection and pass** is
fine; the seller fixed the issue. A failed inspection with no follow-up
means the car was either parked or sold for parts.

## Open recalls

Carfax lists open (unfulfilled) recalls. Most are minor; some are major.

- **Airbag recalls (Takata):** verify completion. Affects ~tens of
  millions of cars. Easy fix at any dealer for free; just hasn't been
  done if the car never went back.
- **Engine recalls (Hyundai/Kia Theta II):** confirm completion before
  buying. If open, the engine is at risk of failure and the dealer will
  refuse to replace it without specific oil-burn evidence.
- **Other safety recalls:** lower priority but factor in a free dealer
  visit.

Open recalls are not deal-breakers (the dealer will perform them for
free), but they should be completed before the title transfers if at all
possible.

## Carfax vs the AutoCheck and the actual title

Carfax is not the only history report. AutoCheck (Experian) sometimes
catches events Carfax misses, and vice versa. If a Carfax looks
suspiciously clean given the car's age, an AutoCheck is $25 and worth
the second opinion.

The actual paper title is the definitive document. Verify it at meet-up
matches the seller's name, the VIN, and is unbranded.

## Putting it together: producing a summary

When the user gives you a Carfax, return:

```
Carfax summary:
- Owners: N (pattern: one long-term + recent flip / hot-potato / etc.)
- Title: clean across all states / branded in [state] in [year]
- Accidents: none / N reported (severity)
- Service records: N over Y years (density: dense / normal / sparse)
- Most recent service: [date] at [mileage] for [what]
- Last transmission fluid: [date / mileage] (current: due / not due)
- Last coolant: [date / mileage] (current: due / not due)
- Last spark plugs: [date / mileage] (current: due / not due)
- Last timing belt: N/A (chain) / [date / mileage] / never done (due)
- Brakes: front pads [date / mileage] / rear pads [date / mileage]
- 12V battery: [date / mileage]
- Hybrid battery: original / replaced [date / mileage] / N/A
- Open recalls: [list]
- Mileage progression: consistent / suspicious / rollback

Risk summary: [1-2 sentences]
Negotiation levers: [list of dated, specific defects or upcoming services]
Near-term spend (first 12 months): $X to $Y
```

That summary plus the seller-profile check plus a PPI is enough to make a
buy/walk decision.
