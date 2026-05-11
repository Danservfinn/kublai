#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROOMS = ROOT / "rooms"
OUTPUT = ROOT / "control-room-retention-items.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def room_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def retention_item(room: Path) -> dict[str, Any] | None:
    retention = load_json(room / "retention" / "retention-review.json")
    trust = load_json(room / "trust" / "trust-report.json")
    summary = load_json(room / "operator" / "operator-summary.json")
    recommendation = str(retention.get("recommendation") or retention.get("retention_recommendation") or "").lower()
    status = str(retention.get("status") or retention.get("decision_status") or "pending").lower()
    if recommendation in {"", "keep"} and status in {"resolved", "complete", "completed"}:
        return None
    needs_receipt = status not in {"resolved", "complete", "completed"}
    trust_state = str(trust.get("trust_state") or trust.get("state") or "unknown")
    next_action = str(summary.get("next_action") or "review retention recommendation and write receipt")
    severity = "medium" if recommendation in {"improve", "prune"} or trust_state in {"watch", "investigate"} else "low"
    return {
        "id": f"retention:{room.name}",
        "room_id": room.name,
        "recommendation": recommendation or "review",
        "status": status,
        "trust_state": trust_state,
        "severity": severity,
        "needs_receipt": needs_receipt,
        "next_action": next_action,
        "receipt_template": f"brain/receipts/kurultai/{{date}}-{room.name}-retention-review.md",
    }


def build_payload(rooms_root: Path) -> dict[str, Any]:
    items = [item for room in room_dirs(rooms_root) if (item := retention_item(room))]
    try:
        rooms_ref = str(rooms_root.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        rooms_ref = "${BUILDROOM_ROOMS}"
    return {"rooms_root": rooms_ref, "items": items, "summary": {"items": len(items), "needs_receipt": sum(1 for item in items if item["needs_receipt"])}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit buildroom retention follow-up items without deleting anything.")
    parser.add_argument("--rooms", type=Path, default=ROOMS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--fail-on-items", action="store_true")
    args = parser.parse_args()
    payload = build_payload(args.rooms)
    write_json(args.output, payload)
    print(json.dumps(payload["summary"], sort_keys=True))
    return 1 if args.fail_on_items and payload["items"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
