# Buildroom Opportunity Radar

Opportunity Radar is the Auto Think layer for the buildroom system. It ranks evidence-backed build candidates from Brain and buildroom state, emits inspectable JSON/markdown reports, and drafts follow-up work without applying side effects by default.

Run:

```bash
python3 tools/kurultai/buildroom/scripts/opportunity_radar.py
```

Outputs:

- `tools/kurultai/buildroom/opportunity-radar.json`
- `tools/kurultai/buildroom/opportunity-radar.md`
- `tools/kurultai/buildroom/opportunity-radar-kanban-drafts.json`

Buildroom cycle command:

```bash
python3 tools/kurultai/buildroom/scripts/run_buildroom_cycle.py
```

This validates rooms, regenerates Control Room outputs, runs cron extraction, runs Opportunity Radar, performs a Kanban bridge dry-run, runs retention review, runs healthcheck, and writes `buildroom-cycle-receipt.json`.

Real Kanban creation requires:

```bash
python3 tools/kurultai/buildroom/scripts/run_buildroom_cycle.py --apply-kanban
```

Safety defaults: local-first, dry-run by default, no external side effects, no hard deletes, inspectable generated artifacts, and explicit apply modes.
