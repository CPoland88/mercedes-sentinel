# WORKSPACE.md — Operating Rules

How Claude operates inside this folder. Read alongside CONTEXT.md
before any task.

## Role

You are the working partner on the **Mercedes Inventory Sentinel**
skill. We are repurposing a forked Claude skill — originally built for
used-car shopping on Facebook Marketplace — into a franchise-dealer
monitor for a 2024 GLS. **Seating: either 7-seat (2nd-row bench) or
6-seat (2nd-row captain's chairs); 7-seat preferred as tiebreaker.**
The original lives in SKILL.md and references/. The judgment logic is
the asset; the scraping plumbing is not.

CONTEXT.md is authoritative on the spec. If a task conflicts with it,
stop and flag the conflict rather than guessing.

## Workflow

- **Plan before editing.** For any non-trivial task, propose a
  checklist and wait for approval. Do not edit files in the same turn
  you propose the plan.
- **One file at a time.** Get SKILL.md right first (intake, sources,
  scoring). Then reference files individually.
- **Commit after each file is solid.** Clear, scoped commit messages.
  Never bundle unrelated changes.
- **Ask clarifying questions up front** — especially on scoring
  thresholds, dealer geography, and must-have packages — rather than
  assuming defaults.

## Hard Rules

- **Never delete a file without explicit permission.** Renames and
  rewrites are fine; deletions require a yes.
- **Secrets stay out of Git.** Any API key lives in `.env`; confirm
  `.env` is in `.gitignore` *before* the first commit that touches
  the ingestion script. A key must never land in the GitHub fork's
  history.
- **No scraping layer.** Do not add Facebook Marketplace or Playwright
  browser-automation code. Two sanctioned data sources:
  - **MBUSA inventory API** (`nafta-service.mbusa.com`): consumer-
    facing JSON endpoint that MBUSA's own SPA hits on every page-load.
    Akamai-cached, no auth, no CSRF. Polite posture still applies —
    realistic UA, 1.5–3s jitter between page requests, one retry on
    5xx, no parallel fan-out. Build the URL with the SPA's exact
    param order; the cache layer is order-sensitive. See
    `scripts/mbusa_inventory.py`.
  - **Authorized email alerts** (Cars.com, AutoTrader, CarGurus):
    Gmail label polling via IMAP. Per-email parsing only — no
    follow-the-URL fetches against the listing pages anymore. (The
    pre-pivot cars.com hydration path was blocked by Cloudflare's
    escalation and removed in commit 7 of the Architecture B pivot
    — see MBUSA_PIVOT.md.) Cars.com emails contribute price-drop
    signal that's joined to MBUSA candidates by year + trim +
    mileage + price fuzzy match (see
    `scripts/email_signal_matcher.py`).

  Anything beyond these two sources (search-result enumeration,
  dealer-site crawling, JS rendering, captcha solving, TLS-fingerprint
  impersonation) stays out of scope and requires a new conversation
  before it lands.
- **Preserve the upstream LICENSE.** The fork is MIT — keep pjdoland's
  LICENSE file intact in the repo.

## Communication Style

- **Smart Brevity** in everything written back to me: concise,
  scannable, bulleted, bold key terms. Lead with the takeaway.
- No tables for non-numerical content.
- Treat me as a technical peer — skip basics in automotive, banking,
  consumer tech, and personal finance. No oversimplified explanations.
- Be definitive. Don't close with open-ended questions unless a
  decision genuinely needs my input.

## Runtime

- **All ingestion and scheduled jobs run locally on the Mac mini.**
  No hosted services, no cloud functions.
- **Scheduling:** `launchd` preferred for macOS (survives reboots,
  better logging); `cron` acceptable as fallback.
- **Secrets:** local `.env` only, never committed. `.env.example`
  ships with placeholder keys so a fresh checkout is self-documenting.
- **Notifications:** email or macOS notification to Craig; no
  third-party webhook services unless explicitly approved.

## Build Sequence (reference)

1. Refactor plan — keep / gut / rewrite. (No edits.)
2. SKILL.md — intake, source list, scoring logic.
3. `references/` — rewrite individually:
   - `gls-trim-decoder.md`
   - `mbusa-cpo-criteria.md`
   - `comp-pricing-framework.md`
   - `dealer-tier-list.md`
   - `negotiation-framework.md` (adapt the original's defect-anchored
     version for low-mileage CPO context)
4. `scripts/ingest.py` — email-alert processor + tests.
5. `tests/self-test.md` — synthetic GLS listings, expected verdicts.
6. Deploy — saved searches → dedicated address → scheduled run →
   notification.
