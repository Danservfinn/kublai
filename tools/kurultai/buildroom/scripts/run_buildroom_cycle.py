#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[4]
BUILDROOM = ROOT / "tools" / "kurultai" / "buildroom"
PYTHON = "/opt/homebrew/opt/python@3.14/bin/python3.14"
def now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def run(cmd: list[str], cwd: Path = ROOT, allow_codes: set[int] | None = None) -> dict[str, Any]:
    allow_codes=allow_codes or {0}; proc=subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return {"command":cmd,"exit_code":proc.returncode,"ok":proc.returncode in allow_codes,"output_tail":"\n".join(proc.stdout.splitlines()[-20:])}
def room_dirs() -> list[Path]:
    rooms=BUILDROOM/"rooms"; return [p for p in sorted(rooms.iterdir()) if p.is_dir()] if rooms.exists() else []
def main() -> int:
    parser=argparse.ArgumentParser(description="Run a local buildroom cycle to completion on command.")
    parser.add_argument("--apply-kanban", action="store_true"); parser.add_argument("--skip-pytest", action="store_true"); parser.add_argument("--json", action="store_true"); parser.add_argument("--receipt-output", default=str(BUILDROOM/".generated"/"buildroom-cycle-receipt.json")); args=parser.parse_args(); steps=[]
    for room in room_dirs(): steps.append(run(["python3", str(BUILDROOM/"scripts/validate_room.py"), str(room)]))
    steps.append(run(["python3", str(BUILDROOM/"scripts/control_room.py")]))
    steps.append(run(["python3", str(BUILDROOM/"scripts/control_room_cron.py")]))
    steps.append(run(["python3", str(BUILDROOM/"scripts/opportunity_radar.py")]))
    kanban_cmd=["python3", str(BUILDROOM/"scripts/apply_kanban_drafts.py"), "--output", str(BUILDROOM/".generated"/"kanban-apply-result.json")]
    if args.apply_kanban: kanban_cmd.append("--apply")
    steps.append(run(kanban_cmd))
    steps.append(run(["python3", str(BUILDROOM/"scripts/retention_review.py")]))
    health=[PYTHON, str(BUILDROOM/"scripts/buildroom_healthcheck.py"), "--json"]
    if args.skip_pytest: health.append("--skip-pytest")
    steps.append(run(health)); ok=all(s["ok"] for s in steps); out=Path(args.receipt_output)
    receipt={"schema_version":"0.1.0","generated_at":now(),"source":"run-buildroom-cycle-v0","mode":"apply-kanban" if args.apply_kanban else "dry-run","ok":ok,"step_count":len(steps),"steps":steps,"outputs":{"control_room":"tools/kurultai/buildroom/control-room.md","opportunity_radar":"tools/kurultai/buildroom/opportunity-radar.md","kanban_apply_result":"tools/kurultai/buildroom/.generated/kanban-apply-result.json","retention_items":"tools/kurultai/buildroom/control-room-retention-items.json"}}
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    if args.json: print(json.dumps({"ok":ok,"step_count":len(steps),"receipt":str(out),"failed_steps":[s for s in steps if not s["ok"]]}, indent=2, sort_keys=True))
    else: print(f"Buildroom cycle {'passed' if ok else 'failed'}; receipt: {out}")
    return 0 if ok else 1
if __name__ == "__main__": raise SystemExit(main())
