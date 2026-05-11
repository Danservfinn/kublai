# Buildroom Control Room Operating Loop

The Control Room loop turns buildroom contracts into recurring caretaker work.

## Commands

Run from the Kurultai repo root:

- `python3 tools/kurultai/buildroom/scripts/control_room_cron.py`
- `python3 tools/kurultai/buildroom/scripts/apply_kanban_drafts.py`
- `python3 tools/kurultai/buildroom/scripts/retention_review.py`
- `python3 tools/kurultai/buildroom/scripts/buildroom_healthcheck.py`

## Loop phases

1. Regenerate the dashboard: `control-room.md/json/html`.
2. Emit attention items: `control-room-attention-items.json`.
3. Emit Kanban drafts: `control-room-kanban-drafts.json`.
4. Dry-run the Kanban bridge and write an apply ledger under `.generated/`.
5. Emit retention review items: `control-room-retention-items.json`.
6. Run the healthcheck canary before any PR or scheduled rollout.

## Kanban bridge safety

`apply_kanban_drafts.py` is dry-run by default. It only creates real Hermes Kanban tasks when `--apply` is passed.

Dedupe is based on a stable attention-item key and the Hermes task `idempotency_key`, prefixed with `buildroom-control-room:`. This prevents repeated cron runs from spamming duplicate tasks.

## Retention safety

`retention_review.py` never deletes buildroom artifacts. It only emits follow-up items and receipt templates for keep/improve/park/prune decisions.

## Healthcheck contract

`buildroom_healthcheck.py` verifies:

- demo room validates
- real gkisokay room validates
- Control Room generation succeeds
- Control Room Cron succeeds
- Kanban bridge dry-run succeeds
- generated files exist
- buildroom scripts compile
- focused buildroom pytest passes unless `--skip-pytest` is used

## Suggested Hermes cron

Conservative schedule: every 60 minutes.

Command shape: run healthcheck in quick mode, run Control Room Cron, dry-run the Kanban bridge, and emit retention review items.

Default behavior remains proposal-only. Add `--apply` to the Kanban bridge only after the dedupe ledger and task bodies are reviewed.
