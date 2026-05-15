# Example 3: Outright scam (kill, do not engage)

This is a synthetic example showing a bait-and-switch / wire-fraud scam
and how the skill should detect it.

## Listing card

```
2015 Lexus RX 350
$8,500
67,000 mi
Posted today in Portland, OR
Like new condition
```

## Listing body text

> 2015 Lexus RX 350 AWD, only 67,000 miles, like new condition. Selling
> on behalf of my deceased husband. He kept it garaged and only drove it
> on weekends. Reluctant to sell but I am moving to live with my
> daughter in another state and need to let it go quickly.
>
> Clean title, full service history at the Lexus dealership. Selling
> below market value because I need this gone by the end of the week
> and I do not have time for tire-kickers.
>
> I am currently out of state finalizing the move. The car is in a
> secure storage facility in Portland. If you are interested, payment
> can be made through eBay Motors which will hold the funds in escrow
> and arrange shipping to you. Buyer pays for shipping. You can inspect
> the car for 5 days after delivery and if you are not satisfied your
> money is refunded.
>
> Serious buyers only, please contact me at [gmail address] for more
> details and photos.

## Seller profile

- Profile: Linda Roberts
- Joined Facebook: 3 weeks ago
- Marketplace ratings: 0
- Active listings: this RX 350 only
- Recently sold: none
- Timeline: no posts at all; profile photo is a stock image of a beach

## How the skill should evaluate this

```
VERDICT: KILL (scam, do not engage)
Year/Make/Model/Trim: irrelevant, this listing is not a real sale
Ask: $8,500 / Comparable 2015 RX 350 AWD with 67K miles: $18K to $24K
Engine: irrelevant
Known issues: irrelevant
Seller signal: RED. Auto-eliminate.
  Reasons:
    1. Price is 60%+ below comparable listings. A 2015 RX 350 with 67K
       does not sell for $8,500 anywhere; this is bait.
    2. "Selling on behalf of deceased husband" + "moving out of state"
       + "need to sell quickly": the textbook escape-hatch narrative.
       Combines low-information (can't answer service questions) with
       urgency (forces fast decisions).
    3. "Currently out of state" + "secure storage facility": classic
       advance-fee scam setup. The car does not exist.
    4. "Payment through eBay Motors escrow with shipping": eBay Motors
       does not offer escrow for private-party FB Marketplace sales.
       This is a fake-eBay phishing variant. The "escrow" link sent
       later will be a spoofed page.
    5. "5-day inspection / money-back guarantee": there is no car,
       there is no inspection, and the money is gone the moment it
       hits the wire.
    6. Contact via Gmail rather than FB Marketplace messages: takes the
       transaction off platform so FB cannot intervene.
    7. Brand new account (3 weeks), no timeline, stock-image profile
       photo, zero ratings, single high-value listing.
Body-text flags: every paragraph contains at least one scam pattern.
Next step: WALK. Do not message. Do not send a Gmail. Do not provide
  shipping address. Optionally report the listing to FB Marketplace via
  the "Report" button (helps other buyers).
```

## Anatomy of this scam

This is a **wire-fraud / advance-fee scam**, one of the most common on
FB Marketplace. The pattern:

1. Bait with a Tier 1 desirable car (Lexus, Honda Odyssey, Toyota
   4Runner) at 40 to 60% of market value.
2. Use the "I'm not here, the car is in storage, we'll ship it" line to
   prevent in-person inspection.
3. Route payment through a fake "escrow service" that is actually a
   phishing site spoofing eBay or Carfax or some other recognized
   brand.
4. Once the wire goes through, the listing disappears, the account is
   abandoned, and the money is gone. FB will not refund. Your bank may
   not refund a wire.

Some variants also harvest the buyer's personal information (mailing
address, ID photo) for identity theft, even if no money is sent.

## Why specific phrases are the tells

- **"Deceased husband / spouse / father":** sympathy hook, also explains
  why the seller can't answer technical questions.
- **"Moving out of state":** urgency + plausible reason for not being
  available for inspection.
- **"Below market value, need to sell quickly":** explains the
  unbelievable price.
- **"Storage facility":** explains why the car is not at the seller's
  home.
- **"eBay Motors escrow":** the actual fraud mechanism. eBay Motors no
  longer offers escrow for non-eBay sales.
- **"Inspection guarantee after delivery":** locks in the buyer; once
  the money is wired, the car never arrives.

## What the skill should NOT do

- Do not engage to "verify" the scam. The scammer will respond with
  more elaborate documentation (fake escrow URL, photoshopped title)
  designed to push the buyer toward sending money.
- Do not assume the user can spot the scam if they message the seller.
  Scammers are professionals and the social engineering is sophisticated.
- Do not get distracted by the car's specs. The car does not exist.

## How to detect this pattern in 5 seconds

If the listing has **any two of**:
- Price 30%+ below comparable
- "Selling for deceased / military deployment / out of state move"
- "Pay through escrow / shipping / wire transfer"
- New account with no timeline

…it is a scam. Skip immediately.
