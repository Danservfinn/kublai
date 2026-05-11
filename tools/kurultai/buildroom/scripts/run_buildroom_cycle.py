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

def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text())

def proposal_summary() -> dict[str, Any]:
    radar = load_json(BUILDROOM / "opportunity-radar.json") or {}
    radar_drafts = load_json(BUILDROOM / "opportunity-radar-kanban-drafts.json") or {}
    control_drafts = load_json(BUILDROOM / "control-room-kanban-drafts.json") or {}
    attention = load_json(BUILDROOM / "control-room-attention-items.json") or {}
    retention = load_json(BUILDROOM / "control-room-retention-items.json") or {}
    candidates = radar.get("candidates", []) if isinstance(radar, dict) else []
    def compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
        scores = candidate.get("scores", {}) if isinstance(candidate.get("scores"), dict) else {}
        return {
            "title": candidate.get("title"),
            "disposition": candidate.get("disposition") or candidate.get("recommended_disposition"),
            "summary": candidate.get("summary"),
            "score": scores.get("total"),
            "score_breakdown": {k: v for k, v in scores.items() if k != "total"},
        }
    return {
        "outcome": {
            "attention_items": len(attention.get("items", [])) if isinstance(attention, dict) else 0,
            "control_room_kanban_drafts": len(control_drafts.get("drafts", [])) if isinstance(control_drafts, dict) else 0,
            "opportunity_radar_candidates": len(candidates),
            "opportunity_radar_kanban_drafts": len(radar_drafts.get("drafts", [])) if isinstance(radar_drafts, dict) else 0,
            "retention_items": len(retention.get("items", [])) if isinstance(retention, dict) else 0,
        },
        "recommended_next_action": radar.get("recommended_next_action") if isinstance(radar, dict) else None,
        "proposals": [compact_candidate(c) for c in candidates if isinstance(c, dict)],
        "control_room_drafts": control_drafts.get("drafts", []) if isinstance(control_drafts, dict) else [],
    }

def print_proposal_report(summary: dict[str, Any], ok: bool, receipt: Path) -> None:
    outcome = summary.get("outcome", {})
    print(f"Buildroom cycle {'passed' if ok else 'failed'}; receipt: {receipt}")
    print("")
    print("Outcome:")
    for key, value in outcome.items():
        print(f"- {key.replace('_', ' ')}: {value}")
    print("")
    print("Proposals:")
    proposals = summary.get("proposals", [])
    if not proposals:
        print("- none")
    for index, proposal in enumerate(proposals, 1):
        print(f"{index}. {proposal.get('title')} — {proposal.get('disposition')} — score {proposal.get('score')}")
        if proposal.get("summary"):
            print(f"   {proposal['summary']}")
    if summary.get("recommended_next_action"):
        print("")
        print(f"Recommended next action: {summary['recommended_next_action']}")

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
    steps.append(run(health)); ok=all(s["ok"] for s in steps); out=Path(args.receipt_output); proposals=proposal_summary()
    receipt={"schema_version":"0.1.0","generated_at":now(),"source":"run-buildroom-cycle-v0","mode":"apply-kanban" if args.apply_kanban else "dry-run","ok":ok,"step_count":len(steps),"steps":steps,"proposal_summary":proposals,"outputs":{"control_room":"tools/kurultai/buildroom/control-room.md","opportunity_radar":"tools/kurultai/buildroom/opportunity-radar.md","kanban_apply_result":"tools/kurultai/buildroom/.generated/kanban-apply-result.json","retention_items":"tools/kurultai/buildroom/control-room-retention-items.json"}}
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    if args.json: print(json.dumps({"ok":ok,"step_count":len(steps),"receipt":str(out),"failed_steps":[s for s in steps if not s["ok"]],"proposal_summary":proposals}, indent=2, sort_keys=True))
    else: print_proposal_report(proposals, ok, out)
    return 0 if ok else 1
if __name__ == "__main__": raise SystemExit(main())
