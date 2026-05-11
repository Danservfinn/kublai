#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[4]
BUILDROOM = ROOT / "tools" / "kurultai" / "buildroom"
DEFAULT_BRAIN = Path(os.environ.get("BRAIN_ROOT", "/Users/kublai/brain"))
WEIGHTS = {"user_leverage":1.4,"compounding_value":1.6,"tractability":1.1,"verification_clarity":1.2,"risk_reversibility":1.2,"dependency_readiness":1.0,"future_behavior_improvement":1.7,"urgency_freshness":0.8}
SCAN_DIRS = ["queue","generated","docs/proposals","docs/plans","docs/designs","docs/kurultai","receipts"]
TOPIC_RULES: list[dict[str, Any]] = [
 {"title":"Buildroom Opportunity Radar v0","candidate_type":"system-improvement","aliases":["opportunity radar","auto think","what should we build next","ranked build intent"],"summary":"Build a local-first strategy layer that ranks next buildroom candidates from Brain and buildroom evidence.","why_now":"Kurultai has a strong Auto Build loop, but candidate selection is still less inspectable than execution.","expected_leverage":"Turns Brain artifacts into recurring ranked build intent and reduces ad hoc operator steering.","acceptance_criteria":["emit JSON and markdown reports","score candidates explainably","emit dry-run Kanban drafts","link recommendations to source refs","pass tests and leakage scan"],"base_scores":{"user_leverage":5,"compounding_value":5,"tractability":4,"verification_clarity":4,"risk_reversibility":5,"dependency_readiness":5,"future_behavior_improvement":5,"urgency_freshness":4}},
 {"title":"Agent Harness Maturity Scoreboard","candidate_type":"evaluation-candidate","aliases":["harness maturity","agent engineering","eval","regression","sandbox","observability"],"summary":"Score projects, agents, and buildrooms against harness maturity primitives.","why_now":"The agent-engineering research argues that agent engineering is harness engineering.","expected_leverage":"Makes agent trust and hardening gaps visible before autonomy expands.","acceptance_criteria":["produce explainable maturity scores","surface improvement recommendations","integrate with Control Room"],"base_scores":{"user_leverage":4,"compounding_value":5,"tractability":4,"verification_clarity":4,"risk_reversibility":5,"dependency_readiness":4,"future_behavior_improvement":5,"urgency_freshness":3}},
 {"title":"Brain Compiler Coverage Ledger","candidate_type":"brain-compiler","aliases":["compiler coverage","memory is leverage","no-op receipt","changed future behavior","processed until"],"summary":"Report which meaningful sources changed behavior and which still need synthesis, skill, Kanban, receipt, or no-op disposition.","why_now":"The Brain has more durable artifacts; now it needs coverage accounting to prevent passive storage.","expected_leverage":"Enforces the invariant that memory only matters when it changes future behavior or gets a no-op receipt.","acceptance_criteria":["scan queue/generated/reviews/proposals/receipts","identify missing dispositions","emit coverage report"],"base_scores":{"user_leverage":4,"compounding_value":5,"tractability":4,"verification_clarity":5,"risk_reversibility":5,"dependency_readiness":4,"future_behavior_improvement":5,"urgency_freshness":3}},
 {"title":"Paper-only Bounty Proof Loop","candidate_type":"external-opportunity","aliases":["bounty","proof loop","revenue","external acceptance","payment"],"summary":"Design a paper-only workflow for evaluating external opportunities without external side effects.","why_now":"There is upside, but reputation and payment surfaces require stronger proof gates first.","expected_leverage":"Creates a safe path to evaluate economic opportunities without uncontrolled commitments.","acceptance_criteria":["evaluate five opportunities on paper","classify proceed/no-op/needs approval","perform no external actions"],"base_scores":{"user_leverage":3,"compounding_value":4,"tractability":3,"verification_clarity":3,"risk_reversibility":2,"dependency_readiness":3,"future_behavior_improvement":3,"urgency_freshness":2},"gates":["external-side-effect-approval-required"]},
 {"title":"Buildroom-to-Content OS Bridge","candidate_type":"content-candidate","aliases":["content os","public artifact","x article","launch","article"],"summary":"Convert completed buildrooms into evidence-backed content candidates.","why_now":"Buildrooms are starting to produce reusable doctrine and receipts.","expected_leverage":"Turns proven internal work into public learning when safe.","acceptance_criteria":["extract claims/evidence","scan public/private boundary","draft publish/no-op recommendation"],"base_scores":{"user_leverage":3,"compounding_value":4,"tractability":3,"verification_clarity":3,"risk_reversibility":4,"dependency_readiness":3,"future_behavior_improvement":3,"urgency_freshness":2}},
]
def utc_now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def rel_ref(path: Path, base: Path, prefix: str) -> str:
    try: return f"{prefix}/{path.relative_to(base).as_posix()}"
    except ValueError: return path.name
def discover_brain(brain_root: Path) -> list[dict[str, Any]]:
    artifacts=[]
    if not brain_root.exists(): return artifacts
    for sub in SCAN_DIRS:
        folder=brain_root/sub
        if not folder.exists(): continue
        for path in sorted(folder.rglob("*.md")):
            try: text=path.read_text(encoding="utf-8", errors="ignore")
            except OSError: continue
            title=path.stem
            for line in text.splitlines()[:30]:
                s=line.strip()
                if s.lower().startswith("title:"): title=s.split(":",1)[1].strip().strip('"') or title; break
                if s.startswith("# "): title=s[2:].strip() or title; break
            artifacts.append({"ref":rel_ref(path, brain_root, "brain"),"title":title,"text":text.lower(),"kind":sub})
    return artifacts
def discover_buildroom(buildroom_root: Path) -> dict[str, Any]:
    summary={"rooms":[],"control_room_present":False,"attention_count":0,"kanban_draft_count":0}
    rooms=buildroom_root/"rooms"
    if rooms.exists(): summary["rooms"]=[p.name for p in sorted(rooms.iterdir()) if p.is_dir()]
    summary["control_room_present"]=(buildroom_root/"control-room.json").exists()
    for name,key in [("control-room-attention-items.json","attention_count"),("control-room-kanban-drafts.json","kanban_draft_count")]:
        try:
            payload=json.loads((buildroom_root/name).read_text())
            summary[key]=int(payload.get("attention_count") or payload.get("draft_count") or len(payload.get("items") or payload.get("drafts") or []))
        except Exception: pass
    return summary
def stable_id(title: str, candidate_type: str, refs: list[str]) -> str:
    raw=json.dumps({"title":title.lower(),"type":candidate_type,"refs":sorted(refs)[:8]}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]
def score_total(scores: dict[str,int]) -> float: return round(sum(scores.get(k,0)*w for k,w in WEIGHTS.items()),1)
def source_matches(rule: dict[str, Any], artifacts: list[dict[str, Any]]) -> list[dict[str, str]]:
    aliases=[a.lower() for a in rule["aliases"]]; matches=[]
    for artifact in artifacts:
        hay=artifact["text"]+" "+artifact["title"].lower()+" "+artifact["ref"].lower()
        hits=sum(1 for a in aliases if a in hay)
        if hits: matches.append({"ref":artifact["ref"],"title":artifact["title"],"kind":artifact["kind"],"hit_count":hits})
    return sorted(matches, key=lambda m:(-m["hit_count"], m["ref"]))[:8]
def build_candidates(artifacts: list[dict[str, Any]], buildroom_summary: dict[str, Any]) -> list[dict[str, Any]]:
    candidates=[]
    for rule in TOPIC_RULES:
        matches=source_matches(rule, artifacts); refs=[m["ref"] for m in matches]; scores=dict(rule["base_scores"])
        if not matches:
            scores["verification_clarity"]=max(0,scores["verification_clarity"]-1); scores["dependency_readiness"]=max(0,scores["dependency_readiness"]-1)
        total=score_total(scores)+min(3,len(matches)); gates=list(rule.get("gates", [])); disposition="buildroom-candidate"
        if gates: disposition="needs-human-approval"
        elif total < 20: disposition="no-op"
        elif total < 30: disposition="backlog"
        elif total < 38: disposition="watch"
        candidates.append({"id":stable_id(rule["title"],rule["candidate_type"],refs),"title":rule["title"],"candidate_type":rule["candidate_type"],"source_refs":refs,"summary":rule["summary"],"why_now":rule["why_now"],"expected_leverage":rule["expected_leverage"],"acceptance_criteria":rule["acceptance_criteria"],"risks":gates or ["scope creep","duplicate work","weak outcome feedback"],"dependencies":["Brain artifacts","buildroom Control Room outputs"],"recommended_disposition":disposition,"scores":{**scores,"total":total},"explainability":{"top_positive_factors":["compounds future agent behavior","local-first and reversible",f"{len(matches)} supporting source artifacts"],"top_negative_factors":gates or (["limited direct source evidence in this run"] if not matches else ["requires calibration against outcomes"]),"counterarguments":["Could create noisy recommendations if reports are not capped","Scoring must not replace verified user value"]},"source_evidence":matches,"proposed_artifacts":[]})
    return sorted(candidates, key=lambda c:(-float(c["scores"]["total"]), c["title"]))
def kanban_drafts(candidates: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    drafts=[]
    for c in candidates:
        if float(c["scores"]["total"]) < threshold or c["recommended_disposition"] not in {"buildroom-candidate","watch"}: continue
        body="\n".join([f"Candidate: {c['title']}",f"Type: {c['candidate_type']}",f"Score: {c['scores']['total']}",f"Disposition: {c['recommended_disposition']}",f"Why now: {c['why_now']}",f"Expected leverage: {c['expected_leverage']}","Acceptance criteria:",*[f"- {a}" for a in c["acceptance_criteria"]]])
        drafts.append({"title":f"Buildroom opportunity: {c['title']}","body":body,"labels":["buildroom","opportunity-radar",c["candidate_type"],c["recommended_disposition"]],"priority":"high" if float(c["scores"]["total"])>=42 else "normal","source":"buildroom-opportunity-radar-v0","candidate_id":c["id"]})
    return drafts
def markdown_report(payload: dict[str, Any]) -> str:
    lines=["# Buildroom Opportunity Radar","",f"Generated: {payload['generated_at']}","","## Summary","",f"Candidates: {len(payload['candidates'])}",f"Kanban drafts: {len(payload['kanban_drafts'])}","","## Top candidates",""]
    for c in payload["candidates"][:8]:
        lines += [f"### {c['title']}","",f"- Type: `{c['candidate_type']}`",f"- Score: `{c['scores']['total']}`",f"- Disposition: `{c['recommended_disposition']}`",f"- Why now: {c['why_now']}",f"- Expected leverage: {c['expected_leverage']}",f"- Sources: {len(c['source_refs'])}","- Acceptance criteria:"]
        lines += [f"  - {a}" for a in c["acceptance_criteria"]]
        lines += ["- Counterarguments:"]+[f"  - {a}" for a in c["explainability"]["counterarguments"]]+[""]
    if payload.get("warnings"): lines += ["## Warnings",""]+[f"- {w}" for w in payload["warnings"]]
    return "\n".join(lines).rstrip()+"\n"
def main() -> int:
    parser=argparse.ArgumentParser(description="Rank buildroom opportunities from Brain and buildroom evidence.")
    parser.add_argument("--brain-root", default=str(DEFAULT_BRAIN)); parser.add_argument("--buildroom-root", default=str(BUILDROOM)); parser.add_argument("--json-output", default=str(BUILDROOM/"opportunity-radar.json")); parser.add_argument("--markdown-output", default=str(BUILDROOM/"opportunity-radar.md")); parser.add_argument("--kanban-drafts-output", default=str(BUILDROOM/"opportunity-radar-kanban-drafts.json")); parser.add_argument("--draft-threshold", type=float, default=38.0); parser.add_argument("--json", action="store_true")
    args=parser.parse_args(); artifacts=discover_brain(Path(args.brain_root).expanduser()); summary=discover_buildroom(Path(args.buildroom_root).expanduser()); candidates=build_candidates(artifacts,summary); drafts=kanban_drafts(candidates,args.draft_threshold); warnings=[]
    if not artifacts: warnings.append("No Brain artifacts discovered; output is based on canonical fallback candidates only.")
    if not summary.get("control_room_present"): warnings.append("Control Room JSON not found; buildroom state evidence is partial.")
    payload={"schema_version":"0.1.0","generated_at":utc_now(),"mode":"dry-run","input_summary":{"brain_artifact_count":len(artifacts),"buildroom_count":len(summary.get("rooms",[])),"control_room_present":summary.get("control_room_present",False),"attention_count":summary.get("attention_count",0),"kanban_draft_count":summary.get("kanban_draft_count",0)},"candidates":candidates,"rejected":[],"warnings":warnings,"recommended_next_action":candidates[0]["title"] if candidates else None,"kanban_drafts":drafts}
    for path,data in [(Path(args.json_output),payload),(Path(args.kanban_drafts_output),{"source":"buildroom-opportunity-radar-v0","generated_at":payload["generated_at"],"draft_count":len(drafts),"drafts":drafts})]: path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data, indent=2, sort_keys=True)+"\n")
    md=Path(args.markdown_output); md.parent.mkdir(parents=True, exist_ok=True); md.write_text(markdown_report(payload))
    if args.json: print(json.dumps({"candidate_count":len(candidates),"draft_count":len(drafts),"recommended_next_action":payload["recommended_next_action"],"warnings":warnings}, indent=2, sort_keys=True))
    else: print(f"Wrote {args.json_output}, {args.markdown_output}, and {args.kanban_drafts_output}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
