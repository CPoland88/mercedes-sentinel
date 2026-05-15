# Driving Facebook Marketplace with Playwright MCP

Load this file when Playwright MCP is available and the user has agreed
to let Claude drive the browser.

## Prerequisites

- User is logged into Facebook **in the browser that Playwright
  controls**. Do not attempt to log in for the user; do not handle
  credentials.
- If `mcp__playwright__browser_navigate` and related tools are not
  callable, fall back to paste mode and tell the user.

## Subcategory paths matter

The subcategory in the URL path is what filters by body style. URL
query parameters like `carType=sedan` do **not** filter.

| Body style | URL path |
|---|---|
| All vehicles | `facebook.com/marketplace/[city]/vehicles` |
| Cars (all body styles) | `facebook.com/marketplace/[city]/cars` |
| Sedans | `facebook.com/marketplace/[city]/sedans` |
| Hatchbacks | `facebook.com/marketplace/[city]/hatchbacks` |
| Wagons | `facebook.com/marketplace/[city]/wagons` |
| SUVs | `facebook.com/marketplace/[city]/suvs` |
| Pickups | `facebook.com/marketplace/[city]/trucks` |
| Minivans | `facebook.com/marketplace/[city]/minivans` |

`/station-wagons` redirects to the root and does NOT work; use
`/wagons`.

Some subcategories return "no products in your area" for stretches of
the day even when inventory exists. If a subcategory is empty,
harvest `/cars` (which pulls all body styles) and filter by title-
text body-style detection.

## Search filter parameters that DO work

These are query parameters that actually filter:

- `minPrice` and `maxPrice` (e.g., `?minPrice=2000&maxPrice=7000`)
- `radius` (in miles; FB will silently clamp to a lower value if
  inventory is sparse, especially on hatchbacks and wagons)
- `sortBy` (e.g., `creation_time_descend` for newest first)
- `daysSinceListed` (1, 7, 30)

## Snapshot, not screenshot

Use `mcp__playwright__browser_snapshot` for parsing listing data. The
accessibility tree contains listing titles, prices, locations, and
links in structured form. Screenshots are useful for showing the user
a specific finding but are expensive to parse.

## Per-listing workflow

For each candidate listing:

1. Navigate to the listing URL.
2. Snapshot the page. Extract: title, price, location, body text,
   posting date, seller name, seller profile link.
3. Apply `references/scam-patterns.md` to the body text.
4. Navigate to the seller profile link.
5. Snapshot. Extract: account join year, Marketplace rating count,
   active listings (vehicles + non-vehicles), Marketplace history.
6. Apply `references/curbstoner-playbook.md` vehicle-count rule.
7. If the listing survives both filters, emit the VERDICT block.

## Rate limits and challenges

- Do not page through hundreds of listings per minute. Marketplace
  will rate-limit or challenge the session.
- If the page returns a CAPTCHA, an "are you a robot" challenge, or
  a login prompt, **stop**. Do not click through. Tell the user to
  clear the challenge in the browser, then continue.
- A reasonable cadence is 10 to 15 listings per minute with brief
  pauses. Long sessions should be split.

## What Playwright cannot do

- Solve captchas.
- Bypass login walls (FB requires login for most Marketplace browsing).
- Read messages or message sellers (this requires user action).
- Access the seller's "Sold listings" tab if FB hides it behind a
  click. The user may need to expand it.

## Falling back

If a Playwright session fails (login challenge, rate limit, network
error), drop back to paste mode for the current car. Do not retry the
same action; tell the user what happened and ask them to paste the
listing manually.
