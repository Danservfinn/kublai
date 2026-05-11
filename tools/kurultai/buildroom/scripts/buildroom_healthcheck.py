#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
BUILDROOM = ROOT / "tools" / "kurultai" / "buildroom"


def run(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return {"command": command, "exit_code": proc.returncode, "output": proc.stdout[-4000:]}


def generated_files_present() -> dict[str, Any]:
    expected = [
        BUILDROOM / "control-room-attention-items.json",
        BUILDROOM / "control-room-kanban-drafts.json",
        BUILDROOM / "control-room.json",
        BUILDROOM / "control-room.html",
        BUILDROOM / "control-room.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in expected if not path.exists()]
    return {"name": "generated-files-present", "exit_code": 0 if not missing else 1, "missing": missing, "output": ""}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run public-safe buildroom canaries and regressions.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--skip-pytest", action="store_true", help="Skip focused pytest run for quick cron checks.")
    args = parser.parse_args()

    checks = []
    rooms = [BUILDROOM / "rooms" / "demo-room", BUILDROOM / "rooms" / "2026-05-10-gkisokay-auto-think-auto-build"]
    for room in rooms:
        checks.append({"name": f"validate:{room.name}", **run([sys.executable, "tools/kurultai/buildroom/scripts/validate_room.py", str(room)])})
    checks.append({"name": "control-room-generate", **run([sys.executable, "tools/kurultai/buildroom/scripts/control_room.py"])})
    checks.append({"name": "control-room-cron", **run([sys.executable, "tools/kurultai/buildroom/scripts/control_room_cron.py"])})
    checks.append({"name": "kanban-bridge-dry-run", **run([sys.executable, "tools/kurultai/buildroom/scripts/apply_kanban_drafts.py"])})
    checks.append(generated_files_present())
    checks.append({"name": "compileall-buildroom", **run([sys.executable, "-m", "compileall", "-q", "tools/kurultai/buildroom/scripts"])})
    if not args.skip_pytest:
        checks.append({"name": "pytest-buildroom", **run([sys.executable, "-m", "pytest", "tests/kurultai/test_buildroom_foundation.py", "--no-cov", "-q"])})
    passed = all(check["exit_code"] == 0 for check in checks)
    payload = {"passed": passed, "checks": checks}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"buildroom healthcheck: {'PASS' if passed else 'FAIL'}")
        for check in checks:
            print(f"- {check['name']}: exit {check['exit_code']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
