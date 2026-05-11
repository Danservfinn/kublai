# Buildroom Opportunity Radar

Generated: 2026-05-11T03:21:25Z

## Summary

Candidates: 5
Kanban drafts: 3

## Top candidates

### Buildroom Opportunity Radar v0

- Type: `system-improvement`
- Score: `49.9`
- Disposition: `buildroom-candidate`
- Why now: Kurultai has a strong Auto Build loop, but candidate selection is still less inspectable than execution.
- Expected leverage: Turns Brain artifacts into recurring ranked build intent and reduces ad hoc operator steering.
- Sources: 8
- Acceptance criteria:
  - emit JSON and markdown reports
  - score candidates explainably
  - emit dry-run Kanban drafts
  - link recommendations to source refs
  - pass tests and leakage scan
- Counterarguments:
  - Could create noisy recommendations if reports are not capped
  - Scoring must not replace verified user value

### Brain Compiler Coverage Ledger

- Type: `brain-compiler`
- Score: `47.9`
- Disposition: `buildroom-candidate`
- Why now: The Brain has more durable artifacts; now it needs coverage accounting to prevent passive storage.
- Expected leverage: Enforces the invariant that memory only matters when it changes future behavior or gets a no-op receipt.
- Sources: 8
- Acceptance criteria:
  - scan queue/generated/reviews/proposals/receipts
  - identify missing dispositions
  - emit coverage report
- Counterarguments:
  - Could create noisy recommendations if reports are not capped
  - Scoring must not replace verified user value

### Agent Harness Maturity Scoreboard

- Type: `evaluation-candidate`
- Score: `46.7`
- Disposition: `buildroom-candidate`
- Why now: The agent-engineering research argues that agent engineering is harness engineering.
- Expected leverage: Makes agent trust and hardening gaps visible before autonomy expands.
- Sources: 8
- Acceptance criteria:
  - produce explainable maturity scores
  - surface improvement recommendations
  - integrate with Control Room
- Counterarguments:
  - Could create noisy recommendations if reports are not capped
  - Scoring must not replace verified user value

### Buildroom-to-Content OS Bridge

- Type: `content-candidate`
- Score: `35.0`
- Disposition: `watch`
- Why now: Buildrooms are starting to produce reusable doctrine and receipts.
- Expected leverage: Turns proven internal work into public learning when safe.
- Sources: 8
- Acceptance criteria:
  - extract claims/evidence
  - scan public/private boundary
  - draft publish/no-op recommendation
- Counterarguments:
  - Could create noisy recommendations if reports are not capped
  - Scoring must not replace verified user value

### Paper-only Bounty Proof Loop

- Type: `external-opportunity`
- Score: `32.6`
- Disposition: `needs-human-approval`
- Why now: There is upside, but reputation and payment surfaces require stronger proof gates first.
- Expected leverage: Creates a safe path to evaluate economic opportunities without uncontrolled commitments.
- Sources: 8
- Acceptance criteria:
  - evaluate five opportunities on paper
  - classify proceed/no-op/needs approval
  - perform no external actions
- Counterarguments:
  - Could create noisy recommendations if reports are not capped
  - Scoring must not replace verified user value
