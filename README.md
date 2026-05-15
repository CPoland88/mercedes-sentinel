# used-car-finder

A Claude skill that helps you shop for a reliable used car on Facebook
Marketplace. It filters out curbstoners, scams, and money-pit models;
reads Carfax reports; identifies trim from photos; estimates fair value;
and builds defect-anchored negotiation cases.

## What this is

A skill, not a scraper. It teaches Claude how to evaluate a Marketplace
listing the way a skeptical friend who knows cars would. You paste
listings, photos, and Carfax PDFs into a conversation, and Claude walks
you through the buy/walk decision.

## Why this exists

Roughly 1 in 3 of the most appealing-looking listings on Facebook
Marketplace have a significant red flag visible only in the body text
or the seller's profile. Spotting these takes practice. This skill
packages that practice.

The judgment framework comes from a real used-car search in 2026: a
single buyer evaluating ~2,200 listings in a single metro, eventually
shortlisting ~12 verified picks. The patterns generalize.

## Installation

### As a Claude Code skill

Clone this repo into your `~/.claude/skills/` directory:

```sh
cd ~/.claude/skills
git clone https://github.com/pjdoland/used-car-finder.git
```

The skill activates automatically when you ask Claude for help with
used-car shopping in a Claude Code session.

### Used by itself

You can also paste the contents of `SKILL.md` into any Claude
conversation (Claude.ai, Claude Code, or the API). The reference files
in `references/` are pulled on demand.

## How to use it

The skill walks you through four stages:

1. **Intake.** Claude asks your metro, budget, body-style preferences,
   family situation, mechanical comfort, and belt-tolerance.
2. **Search and filter.** You paste listings (URLs or screenshots);
   Claude classifies them as Tier 1 / Tier 2 / Watch / Kill.
3. **Verify and evaluate.** On a specific car, Claude walks the
   curbstoner check, reads the Carfax, identifies trim from photos,
   and produces a PPI checklist.
4. **Close.** Claude builds a defect-anchored negotiation case and
   sets up insurance coverage.

Try: *"Help me find a reliable used car under $7,000 in [your metro]."*

## Layout

```
SKILL.md                         main skill file (loaded by Claude)
references/
  reliable-makes.md              tier list of makes/models
  curbstoner-playbook.md         seller-profile rubric
  scam-patterns.md               body-text red flags
  carfax-reading.md              how to read a Carfax PDF
  trim-id-guide.md               identifying trim from photos
  ppi-checklist.md               pre-purchase inspection
  timing-chain-vs-belt.md        engine reference
  negotiation-framework.md       defect-anchored offers
  insurance-by-acv.md            coverage by vehicle value
examples/
  example-1-good-listing.md      green-flag listing walkthrough
  example-2-curbstoner.md        curbstoner detection walkthrough
  example-3-scam.md              wire-fraud scam walkthrough
tests/
  self-test.md                   regression tests for the skill
```

## Scope and limitations

- **Facebook Marketplace only.** Craigslist, AutoTrader, CarGurus, and
  dealer sites have different scam patterns and seller dynamics.
- **US market, US insurance.** Some references (state inspection,
  insurance carriers, title-branding rules) assume US conventions.
- **Private-party purchases.** Dealer purchases follow different rules.
- **Under ~$15K.** The judgment framework is calibrated for older,
  higher-mileage cars where reliability matters more than features.
  For newer or more expensive cars, traditional consumer-research
  approaches (Consumer Reports, Edmunds) are also useful.

## Self-test

`tests/self-test.md` contains 5 synthetic listings with expected
verdicts. Run them past the skill periodically to catch regressions if
you modify the references.

## Contributing

PRs welcome. The kind of contributions that help:

- New scam patterns you've encountered on Marketplace
- Model-specific known issues for cars not yet in `reliable-makes.md`
- Trim-identification tells for brands not yet documented
- Regional notes for state-specific insurance or title rules
- Additional self-test cases

## License

MIT. See LICENSE.

## Disclaimer

This skill provides general guidance for evaluating used-car listings.
It is not a substitute for a professional pre-purchase inspection, a
licensed mechanic's opinion, or legal advice. The author is not
responsible for any purchase decisions made using this skill.
