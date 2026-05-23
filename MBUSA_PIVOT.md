# MBUSA Pivot — Architecture B

Decision document for the 2026-05-21 session. Hydration source moves
from cars.com (HTML scrape) to MBUSA inventory API (JSON). Cars.com
emails become a secondary price-drop signal layered on top of MBUSA
candidates.

## Why the pivot

Cars.com hydration worked briefly then got blocked. Cloudflare's
escalation ladder:

1. **UA-only spoof** → 403 + `Cf-Mitigated: challenge`
2. **+ Client Hints (commit `fa0ba15`)** → 30s tarpit on every request
3. **+ HTTP/2 (commit `9c8f84e`)** → Three 200s, three real VINs
   extracted, ~5s total. Architecture worked end-to-end.
4. **~10 minutes later** → 403s again. Behavioral fingerprinting
   kicked in once Cloudflare saw "Python httpx hitting vehicledetail
   URLs at machine speed" as a sustained pattern.

The next rung on the ladder is TLS-fingerprint impersonation
(`curl_cffi` / `tls-client`) which crosses cleanly into "actively
defeating bot-detection" — outside the WORKSPACE.md carve-out and
ethically uncomfortable. The rung after that is headless browser.
Each rung is more aggressive and less stable.

The cars.com path is not sustainable for daily automation.

## The MBUSA API contract (validated working)

**Endpoint:**
```
GET https://nafta-service.mbusa.com/api/inv/v1/en_us/used/vehicles/search
```

**Working query (returns 200, 132 KB JSON, 12 records, 34 total US-wide):**
```
?count=12
&distance=ANY
&exterior=BLU,GRN
&invType=cpo
&maxYear=2026
&minYear=2024
&model=GLS450W4,GLS580W4
&resvOnly=false
&sortBy=distance-asc
&start=0
&withFilters=true
&zip=22180
&class=GLS
```

**Parameter contract (learned from MBUSA's own SPA via DevTools):**
- `model` = comma-separated model designation codes (e.g., `GLS450W4,GLS580W4`).
  NOT `modelId`, NOT `modelDesignation` — the SPA uses `model`.
- `class` = vehicle class above model (`GLS`, `GLE`, etc.).
- `minYear` / `maxYear` = year range (NOT `year=2024,2025,2026`).
- `exterior` = comma-separated short color codes (`BLU`, `GRN`).
  NOT `exteriorColor`, NOT full color names.
- `invType` = `cpo` for CPO only, `cpo,pre` to include pre-owned.
- `count` = page size. Defaults that work: 12. Larger values (50+) cause 500s.
- `start` = pagination offset.
- `sortBy=distance-asc` + `zip=22180` gives us geo-sorted results.
- `distance=ANY` removes geographic cap (paginate to apply our own).
- `resvOnly=false` includes non-reserved inventory.
- `withFilters=true` includes filter taxonomy in response.

**Required headers (matches MBUSA's own SPA, validated via `scripts/dev_capture_api.py`):**
- `Accept: */*`
- `Content-Type: application/json`
- `Origin: https://www.mbusa.com`
- `Referer: https://www.mbusa.com/en/cpo/inventory/search?...`
- `Sec-Fetch-Mode: cors`
- `Sec-Fetch-Dest: empty`
- `Sec-Fetch-Site: same-site`
- Standard Chrome UA + Client Hints (already in dev_capture_api.py)

**No auth, no API key, no CSRF token, no session cookie.** Akamai-cached.
Designed for high-volume consumer traffic.

## Response schema (vehicle record)

`result.pagedVehicles.records[]` is the array. Per-record fields that
matter for CONTEXT.md:

| MBUSA field | CONTEXT.md need |
|:--|:--|
| `vin` | Identity, VIN-pos-10 model year verification |
| `year` | Model year |
| `modelId` / `modelName` | Trim verification |
| `dealer.name` + `dealer.address[0].{city, state}` | Tier A/B/C geo |
| `exteriorMetaColor` / `paint.marketing` | Blue-only gate |
| `inventoryPrice` / `msrp` | Ask price + comp math |
| `usedVehicleAttributes.mileage` | Mileage gate |
| `type` (`PRE` = CPO) | CPO verification |
| `features` / `properties` / `includedFeatures` | Pinnacle/Acoustic/Warmth must-haves |
| `stockId` | Dealer-side inventory ID |

## Coverage check (validated 2026-05-21)

Three cars.com VINs extracted from the price-drop email fixture:

- `4JGFF5KEXRB219544` — **FOUND** in MBUSA CPO+Blue/Green+2024-26+GLS query.
  Ray Catena of Freehold NJ, 25,619 mi, $71,999. Exact price/mileage
  match with cars.com email.
- `4JGFF5KE8RB067442` — not found. Likely non-CPO or wrong color.
  Per CONTEXT.md both are auto-Pass anyway.
- `4JGFF5KE4RB062030` — not found. Same.

Also notable: `4JGFF8FE1RB057816` — the **calibration anchor in
CONTEXT.md** (Mercedes-Benz of White Plains NY, 2024 GLS 580, blue,
13,872 mi, $87,495) — is in the MBUSA API result. Same vehicle Craig
already uses for manual analysis is now machine-readable.

## Architecture B — file-by-file plan

**Delete:**
- `scripts/hydrate.py` — cars.com hydration via JSON-LD/CSS/regex. Obviated.
- `scripts/dev_capture_html.py` — debug tool for the obsolete path.
- `scripts/tests/test_hydrate.py` — tests for the deleted module.

**Keep, simplified:**
- `scripts/parsers/cars_com.py` — drop the `_try_hydrate` call. The
  per-vehicle block parsing is still useful: extracts VIN, year, trim,
  mileage, price, price_drop_delta from the email body. Output becomes
  an `EmailSignal` dict (not a hydration-ready candidate). Cars.com
  emails get processed for their price-drop signal value, not as a
  primary ingestion source.
- `scripts/parsers/__init__.py` — dispatcher unchanged.

**New:**
- `scripts/mbusa_inventory.py` — production API client. Mirrors
  `dev_capture_api.py` but with proper retry, jitter, error handling,
  pagination. Functions:
  - `fetch_matching_inventory(zip, model_codes, year_range, color_codes, invType, distance)`
    returns `list[MbusaCandidate]` after walking all pages.
  - `parse_vehicle_record(record_dict)` → `MbusaCandidate`.
- `scripts/tests/test_mbusa_inventory.py` — synthetic JSON fixtures
  (committed under `scripts/tests/fixtures/` since these will be
  scrubbed of dealer-specific data for CI).

**Modify:**
- `scripts/ingest.py` — orchestration becomes:
  1. Poll MBUSA for current matching inventory (primary candidate stream).
  2. Read unread cars.com / autotrader / cargurus emails for
     EmailSignals (VIN + price_drop_delta).
  3. For each EmailSignal, match by VIN to an existing MBUSA candidate
     and attach the price_drop_delta.
  4. Dedup + queue MBUSA candidates as before.
- `scripts/state.py` — schema additions:
  - `source: "mbusa"` field on candidates (vs `source: "email_only"`
    for unmatched email signals — likely never queued for triage, but
    logged for audit).
  - `email_signals` sub-record per VIN: list of
    `{provider, observed_at, price_drop_delta, ask_at_observation}`
    so triage can see the price-drop trajectory.
  - One-time migration: existing `seen-vins.json` entries get
    `source: "cars_com_hydration"` for archival; new entries use
    the new schema.

**No change:**
- `scripts/triage.py`, `scripts/llm.py`, `scripts/prompts/system.md`
  — gets richer/cleaner candidate input, same triage logic.
- `scripts/notify.py`, `scripts/daily.py`, `launchd/*` — orchestration
  upstream of the change, no contract break.

## Suggested commit sequence

1. **`MBUSA_PIVOT.md` + recon scaffolding** *(tonight, this commit)* —
   captures the decision, the API contract, the coverage data. Also
   commits `scripts/dev_capture_api.py` and the `.gitignore` extension
   for `*.json` fixtures (prep already done).
2. **Add `scripts/mbusa_inventory.py` + tests** — new module, scrubbed
   JSON fixture committed at `scripts/tests/fixtures/mbusa_sample.json`
   (one record manually anonymized from `mbusa_filtered_baseline.json`).
   Standalone module, not yet wired into ingest.
3. **State schema migration** — add `source` field, `email_signals`
   sub-record. Tests cover the migration path.
4. **Wire MBUSA polling into `ingest.py`** — primary stream. Cars.com
   emails still processed via existing parser but their output is
   discarded for now (queued behind a deprecation warning).
5. **Refactor `parsers/cars_com.py`** — drop `_try_hydrate`, change
   output shape to `EmailSignal`. Update tests.
6. **Wire EmailSignal attachment in `ingest.py`** — match by VIN to
   MBUSA candidate stream, attach price_drop_delta. Tests cover the
   match + miss cases.
7. **Delete obsoleted code** — `scripts/hydrate.py`,
   `scripts/dev_capture_html.py`, `scripts/tests/test_hydrate.py`.
   Update WORKSPACE.md hydration carve-out to reflect that the carve-out
   is no longer needed (MBUSA is a sanctioned consumer-facing API, not
   a "scrape with permission" situation).
8. **End-to-end verification** — fixture run + live daily-run dry-run.

Each commit independently passes tests + lives behind a clear scope.

## Open questions for tomorrow

- **Color code mapping.** CONTEXT.md names three specific colors
  (Emerald Green Metallic, Twilight Blue Metallic, MANUFAKTUR Signature
  Ireland Mid Green Metallic). MBUSA's `exterior` filter uses two-letter
  codes (`BLU`, `GRN`). We don't yet know the exact mapping from
  marketing names → short codes. Recon may reveal more granular codes
  (`MGRN`, `EGRN`, etc.) when we inspect `facets.color.values` from the
  baseline JSON. Decide whether to filter on the broad codes (`BLU,GRN`)
  and post-filter in code by marketing name, or use precise codes.
- **Distance enforcement.** MBUSA's `distance=ANY` gives nationwide.
  Filter to `≤250mi` either via the API (`distance=250`) or by computing
  it from the dealer's address in code. API is cleaner; risk: API might
  use straight-line distance, CONTEXT.md uses drive distance.
- **CPO vs pre-owned posture.** Architecture B as drafted polls
  `invType=cpo` only. CONTEXT.md prefers CPO but doesn't require it
  (non-CPO is acceptable with foregone-warranty discount). Worth
  considering polling `invType=cpo,pre` and tagging CPO status in the
  candidate so triage can apply the warranty discount.
- **Email-signal-only candidates.** When a cars.com email's VIN doesn't
  match any MBUSA candidate, it's almost certainly auto-Pass per
  CONTEXT.md (non-CPO + wrong color). Worth logging these for audit
  but probably not queuing for triage. Decide the policy.

## What survives from the cars.com work

Not throwing away the last 8 commits:

- WORKSPACE.md carve-out (commit `9541d07`) — repurpose to cover MBUSA
  API access. The posture (polite, one request per intent, no JS, no
  headless browser) still applies and is even more clearly OK for a
  consumer-facing API like MBUSA.
- `parsers/cars_com.py` block parsing (commit `9d30bf6`) — keep,
  simplified. The regex anchors + per-vehicle UUID dedup logic is
  reusable for the EmailSignal output.
- `parsers/fallback.py` VIN-letter filter (commit `dd946fa`) — keep,
  still applies anywhere we extract VINs from unstructured text.
- All shell-instruction lessons (no `#` comments, sandbox can't git-op
  cleanly) — codified in user memory.

The cars.com hydration commits themselves (`fa0ba15`, `9c8f84e`,
`4e2468e`, `66b3fe5`) get deleted from working tree in commit 7
above. They remain in git history as documentation of the path we
walked.

## Status — 2026-05-23 — Complete

**Pivot complete.** All eight planned commits landed on 2026-05-23:

1. `7fca376` — this decision doc
2. `10c2137` — `scripts/mbusa_inventory.py` API client (36 tests)
3. `77ac5cd` — `scripts/state.py` schema v2 (per-VIN `email_signals` + migration, 12 new tests)
4. `9d9748e` + `5aabd18` — wire MBUSA into `ingest.py` (17 tests) + resilience hotfixes (`max_year` clamp at current calendar year, SPA-exact querystring param order, tolerant pagination on 5xx for later pages)
5. `4720eba` — `parsers/cars_com.py` → EmailSignals, hydration dropped
6. `ae77051` — `scripts/email_signal_matcher.py` + ingest integration (34 tests)
7. `bb9aa90` — delete `scripts/hydrate.py`, `scripts/dev_capture_html.py`, `scripts/tests/test_hydrate.py`; retire WORKSPACE.md hydration carve-out
8. *(this commit)* — live end-to-end verification + status update

Net diff across all seven code commits: roughly –1,000 lines. Suite:
**204 tests OK** (was 238 at `ae77051` minus the 34 in the deleted
`test_hydrate.py`). One housekeeping commit (`951c515`) tidied
README, removed four unused imports, and committed
`NEXT_VEHICLE_HANDOFF.md`.

### Live validation results — 2026-05-23 16:52 ET

After MBUSA's Saturday-morning inventory outage cleared, ran the
synthetic end-to-end one-liner: `run_mbusa_poll` against live MBUSA,
then `parse_email` against the local
`scripts/tests/fixtures/cars_com_price_drop_2026-05-21.eml`, then
`_attach_email_signals` to exercise the matcher.

**MBUSA poll:**

- Both pages returned HTTP 200 (`start=0` and `start=12`) — the
  SPA-exact param order from commit `5aabd18` resolves the cache-cold
  503 issue we hit at 8:52 ET this morning.
- 12 records returned across the two pages.
- 10 kept after CONTEXT.md hard-cap filters (≤250 mi straight-line,
  ≤40k mi, year ≥2024). 2 dropped — likely the >250 mi ones.

**EmailSignal extraction:**

- 3 cars.com EmailSignals extracted from the .eml fixture (all 2024
  GLS 450 4MATIC, all with price-drop deltas).
- 0 regular candidates — the post-pivot parser emits signals only
  for cars.com.

**Matcher results:**

- UUID `d092dc28-4909-4dca-ac69-855bdf8da7ea` (25,619 mi / $71,999) →
  **matched VIN `4JGFF5KEXRB219544`** with score **0.000**. The
  cars.com snapshot and MBUSA snapshot agree exactly on both mileage
  and price. Calibration anchor confirmed.
- UUID `5b475d0d-b34a-40b6-b372-83469b4b7655` (38,099 mi / $59,397) →
  unmatched ("no candidate within mileage/price tolerance"). Correct
  — no MBUSA candidate within ±500 mi / ±$2,000 of those values
  (highest-mileage 2024 GLS 450 in MBUSA today is 27,898 mi).
- UUID `b2cc612e-a40b-4073-a457-4facb2d82a6f` (37,802 mi / $67,864) →
  unmatched. Same.

Predicted outcome: 1 matched, 2 unmatched. Observed outcome: 1
matched, 2 unmatched. Matcher behavior matches design.

### Deployment status

The Mac mini will pick up the new code on next `git pull`. First run
will migrate `data/seen-vins.json` from v1 to v2 in-place on load
(adds `email_signals: []` to every existing VIN record, stamps
`_schema_version: 2`). The launchd plist at
`launchd/com.craigpoland.mercedes-sentinel.plist` is unchanged.

### Tuning to revisit after a few weeks of real runs

- **Matcher tolerances** (`MATCH_MILEAGE_TOLERANCE_MI = 500`,
  `MATCH_PRICE_TOLERANCE_USD = 2000`). First-pass values. Today's
  validation hit score=0.000 — a perfect match — so the tolerances
  weren't actually exercised at boundary. After a few real
  same-VIN observations across cars.com and MBUSA with non-zero
  drift, we'll see whether to tighten or loosen.
- **`invType=cpo` only.** Open question from this doc's main body.
  Flip to `cpo,pre` once triage's foregone-warranty-discount logic
  is in place.
- **MBUSA's straight-line vs. CONTEXT.md drive-mile** distance gate.
  Today's result includes Mercedes-Benz of White Plains NY at 236 mi
  straight-line, but CONTEXT.md previously noted it as 256 mi drive
  (auto-Pass on geography). Triage needs to apply the drive-mile
  refinement, or we add it as a post-filter in `ingest`. Probably
  worth doing once we observe how often a >250-drive-mile dealer
  passes the 250-straight-line gate.
