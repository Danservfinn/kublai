#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFTS = ROOT / "control-room-kanban-drafts.json"
DEFAULT_STATE = ROOT / ".generated" / "kanban-draft-state.json"
DEFAULT_LEDGER = ROOT / ".generated" / "kanban-apply-ledger.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def drafts_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        value = payload.get("drafts") or payload.get("tasks") or []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def stable_key(draft: dict[str, Any]) -> str:
    metadata = draft.get("metadata") if isinstance(draft.get("metadata"), dict) else {}
    for field in ("attention_item_id", "attention_id", "item_id", "idempotency_key"):
        value = metadata.get(field) or draft.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    room = str(metadata.get("room_id") or draft.get("room_id") or "unknown-room")
    reason = str(metadata.get("reason") or draft.get("reason") or draft.get("title") or draft.get("source") or "unknown-reason")
    return hashlib.sha256(f"{room}\n{reason}".encode()).hexdigest()[:24]


def normalize_draft(draft: dict[str, Any]) -> dict[str, Any]:
    key = stable_key(draft)
    title = str(draft.get("title") or f"buildroom attention: {key}").strip()
    body = str(draft.get("body") or draft.get("description") or "").strip()
    metadata = draft.get("metadata") if isinstance(draft.get("metadata"), dict) else {}
    severity = str(metadata.get("severity") or draft.get("severity") or "medium")
    room_id = str(metadata.get("room_id") or draft.get("room_id") or "")
    reason = str(metadata.get("reason") or draft.get("reason") or draft.get("source") or "")
    acceptance = draft.get("acceptance_criteria") or metadata.get("acceptance_criteria") or []
    if not isinstance(acceptance, list):
        acceptance = [str(acceptance)]
    verification = draft.get("verification_commands") or metadata.get("verification_commands") or []
    if not isinstance(verification, list):
        verification = [str(verification)]
    lines = [body] if body else []
    lines.extend([
        "",
        f"Source: buildroom Control Room attention item `{key}`",
        f"Room: `{room_id or 'unknown'}`",
        f"Severity: `{severity}`",
        f"Reason: {reason or 'see generated attention item payload'}`" if reason else "Reason: see generated attention item payload",
        "",
        "Acceptance criteria:",
    ])
    lines.extend(f"- {item}" for item in acceptance or ["attention item is resolved or explicitly receipted as no-op"])
    lines.append("")
    lines.append("Verification commands:")
    lines.extend(f"- {item}" for item in verification or ["python3 tools/kurultai/buildroom/scripts/buildroom_healthcheck.py"])
    return {
        "dedupe_key": key,
        "title": title,
        "body": "\n".join(lines).strip() + "\n",
        "assignee": str(draft.get("assignee") or metadata.get("assignee") or "kublai"),
        "priority": coerce_priority(draft.get("priority") or metadata.get("priority"), severity),
        "workspace_kind": str(draft.get("workspace_kind") or "dir"),
        "workspace_path": str(draft.get("workspace_path") or "${KURULTAI_HOME}"),
        "idempotency_key": f"buildroom-control-room:{key}",
        "metadata": {**metadata, "dedupe_key": key, "room_id": room_id, "severity": severity, "reason": reason},
    }


def priority_for_severity(severity: str) -> int:
    return {"critical": 90, "high": 70, "medium": 50, "low": 30}.get(severity.lower(), 50)



def coerce_priority(value: Any, severity: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    if isinstance(value, str) and value.strip().lower() in {"critical", "high", "medium", "normal", "low"}:
        mapped = value.strip().lower().replace("normal", "medium")
        return priority_for_severity(mapped)
    return priority_for_severity(severity)

def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"applied": {}}
    data = load_json(path)
    return data if isinstance(data, dict) else {"applied": {}}


def existing_task_by_idempotency(con: sqlite3.Connection, key: str) -> str | None:
    row = con.execute("select id from tasks where idempotency_key = ? limit 1", (key,)).fetchone()
    return str(row[0]) if row else None


def insert_task(con: sqlite3.Connection, task: dict[str, Any], created_by: str) -> str:
    existing = existing_task_by_idempotency(con, task["idempotency_key"])
    if existing:
        return existing
    task_id = "t_" + hashlib.sha256(task["idempotency_key"].encode()).hexdigest()[:8]
    now = int(time.time())
    con.execute(
        """
        insert into tasks (
            id, title, body, assignee, status, priority, created_by, created_at,
            workspace_kind, workspace_path, idempotency_key, skills
        ) values (?, ?, ?, ?, 'todo', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            task["title"],
            task["body"],
            task["assignee"],
            task["priority"],
            created_by,
            now,
            task["workspace_kind"],
            task["workspace_path"],
            task["idempotency_key"],
            json.dumps(["kanban-worker", "kurultai-operations"]),
        ),
    )
    con.execute(
        "insert into task_events (task_id, kind, payload, created_at) values (?, 'created', ?, ?)",
        (task_id, json.dumps({"source": "buildroom-control-room", "metadata": task["metadata"]}, sort_keys=True), now),
    )
    return task_id


def build_plan(drafts_path: Path, state_path: Path) -> dict[str, Any]:
    payload = load_json(drafts_path)
    state = load_state(state_path)
    applied = state.get("applied") if isinstance(state.get("applied"), dict) else {}
    normalized = [normalize_draft(item) for item in drafts_from_payload(payload)]
    unique: dict[str, dict[str, Any]] = {}
    for task in normalized:
        unique.setdefault(task["dedupe_key"], task)
    tasks = []
    for task in unique.values():
        prior = applied.get(task["dedupe_key"])
        tasks.append({**task, "already_applied": bool(prior), "existing_task_id": prior.get("task_id") if isinstance(prior, dict) else None})
    return {"source": str(drafts_path), "state": str(state_path), "tasks": tasks, "summary": {"drafts": len(normalized), "unique": len(unique), "new": sum(1 for task in tasks if not task["already_applied"])}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply buildroom Control Room Kanban drafts with idempotent dry-run default.")
    parser.add_argument("--drafts", type=Path, default=DEFAULT_DRAFTS)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--kanban-db", type=Path, default=Path.home() / ".hermes" / "kanban.db")
    parser.add_argument("--apply", action="store_true", help="Create real Hermes Kanban tasks. Default is dry-run only.")
    parser.add_argument("--created-by", default="kublai-control-room")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan = build_plan(args.drafts, args.state)
    if args.apply:
        state = load_state(args.state)
        state.setdefault("applied", {})
        con = sqlite3.connect(args.kanban_db)
        try:
            with con:
                for task in plan["tasks"]:
                    task_id = insert_task(con, task, args.created_by)
                    task["created_task_id"] = task_id
                    task["already_applied"] = bool(task.get("existing_task_id")) or task_id == task.get("existing_task_id")
                    state["applied"][task["dedupe_key"]] = {"task_id": task_id, "idempotency_key": task["idempotency_key"], "applied_at": int(time.time())}
        finally:
            con.close()
        write_json(args.state, state)
        write_json(args.ledger, {"mode": "apply", **plan})
    else:
        write_json(args.ledger, {"mode": "dry-run", **plan})
    if args.output:
        write_json(args.output, plan)
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", **plan["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
