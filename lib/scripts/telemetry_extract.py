#!/usr/bin/env python3
"""Gate 遙測抽取 + verdict 落檔完整性檢查 (brief 歸檔前跑; 確定性機械流程)。

用法 (Python 3):
  python3 telemetry_extract.py <brief_dir> [--check-only] [--force] [--out <jsonl>]

行為:
  1. 掃 <brief_dir> 下所有 reviews/*.verdict.json 與 reviews/user_review.json
  2. 完整性檢查: 每個 code sub-brief (有 stages/engineering/) 須有 >=1 code-reviewer verdict
     + reviews/user_review.json; brief root 有 plan.md 則須 >=1 planning-reviewer verdict。
     缺 → 列缺檔清單 exit 2 (--force 降為警告續抽; --check-only 只檢不寫)
  3. 抽取為 gate-run rows append 至 .framework/memory/telemetry/gate_runs.jsonl
     (同 brief_id + source=live 舊列先清 → 重跑冪等)

row 欄位: brief_id / sub_brief / gate / round / verdict / findings(list) / findings_count
          / source(live|retro) / extracted_at
gate enum: planning-reviewer | architecture-reviewer.plan | architecture-reviewer.impl
           | code-reviewer | test-writer | integration-tester | user_code_review
           | L0-holistic | (其他 role 名原樣)
exit: 0 成功 / 1 用法或內部錯誤 / 2 完整性檢查未過。"""
import argparse
import datetime
import json
import os
import re
import sys

REQUIRED_PLANNING_GATE = "planning-reviewer"   # root 有 plan.md 時要求
REQUIRED_SUB_GATE = "code-reviewer"            # code sub-brief 要求
SEVERITY_PAT = re.compile(r"\b(BLOCKER|CRITICAL|MAJOR|MINOR)\b", re.IGNORECASE)
SEVERITY_ORDER = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR"]


def resolve_out(brief_dir, cli_out):
    if cli_out:
        return os.path.abspath(cli_out)
    d = os.path.abspath(brief_dir)
    while True:
        if os.path.basename(d) == ".framework":
            return os.path.join(d, "memory", "telemetry", "gate_runs.jsonl")
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.join(os.path.abspath(brief_dir), "gate_runs.jsonl")


def sub_brief_of(relpath):
    m = re.search(r"(?:^|[\\/])sub-briefs[\\/]([^\\/]+)[\\/]", relpath)
    return m.group(1) if m else None


def derive_gate(fname, sub_brief, data):
    base = fname[: -len(".verdict.json")]
    base = re.sub(r"\.round\d+$", "", base)
    if base.lower().startswith("l0"):
        return "L0-holistic"
    if base.startswith("architecture-reviewer"):
        rest = base[len("architecture-reviewer"):]
        if "impl" in rest:
            return "architecture-reviewer.impl"
        if "plan" in rest:
            return "architecture-reviewer.plan"
        stage = str(((data or {}).get("actor") or {}).get("stage") or "")
        if "impl" in stage:
            return "architecture-reviewer.impl"
        if "plan" in stage:
            return "architecture-reviewer.plan"
        return "architecture-reviewer.impl" if sub_brief else "architecture-reviewer.plan"
    return base


def top_severity(text):
    hits = [m.group(1).upper() for m in SEVERITY_PAT.finditer(text or "")]
    for s in SEVERITY_ORDER:
        if s in hits:
            return s
    return None


def verdict_row(brief_id, relpath, fname, data):
    sub = sub_brief_of(relpath)
    gate = derive_gate(fname, sub, data)
    actor = data.get("actor") or {}
    m = re.search(r"\.round(\d+)\.verdict\.json$", fname)
    rnd = int(m.group(1)) if m else actor.get("round") or 1
    findings = []
    for c in data.get("checks") or []:
        if c.get("result") == "fail":
            ev = str(c.get("evidence") or "")[:300]
            findings.append({"desc": c.get("name") or "", "evidence": ev,
                             "severity": top_severity((c.get("name") or "") + " " + ev),
                             "disposition": None})
    return {"brief_id": brief_id, "sub_brief": sub, "gate": gate, "round": rnd,
            "verdict": data.get("verdict"), "findings": findings,
            "findings_count": len(findings), "source": "live",
            "extracted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}


def user_review_row(brief_id, relpath, data):
    findings = []
    for f in data.get("findings") or []:
        findings.append({"desc": str(f.get("desc") or "")[:300], "evidence": None,
                         "severity": f.get("severity"), "disposition": f.get("disposition")})
    return {"brief_id": brief_id, "sub_brief": sub_brief_of(relpath), "gate": "user_code_review",
            "round": data.get("round") or 1, "verdict": data.get("result"),
            "findings": findings, "findings_count": len(findings), "source": "live",
            "extracted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}


def scan(brief_dir):
    rows, missing = [], []
    brief_id = os.path.basename(os.path.normpath(brief_dir))
    sub_has_code, sub_has_required, sub_has_user = set(), set(), set()
    root_has_plan = os.path.isfile(os.path.join(brief_dir, "plan.md"))
    root_has_planning_verdict = False

    for dirpath, _dirnames, filenames in os.walk(brief_dir):
        rel = os.path.relpath(dirpath, brief_dir)
        sub = sub_brief_of(rel + os.sep)
        if os.path.basename(dirpath) == "engineering" and sub:
            sub_has_code.add(sub)
        if os.path.basename(dirpath) != "reviews":
            continue
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            relf = os.path.join(rel, fname)
            if fname.endswith(".verdict.json"):
                try:
                    data = json.load(open(fpath, encoding="utf-8"))
                except (OSError, ValueError) as e:
                    print(f"WARN 略過壞檔 {relf}: {e}", file=sys.stderr)
                    continue
                row = verdict_row(brief_id, relf, fname, data)
                rows.append(row)
                if row["gate"] == REQUIRED_SUB_GATE and row["sub_brief"]:
                    sub_has_required.add(row["sub_brief"])
                if row["gate"] == REQUIRED_PLANNING_GATE and not row["sub_brief"]:
                    root_has_planning_verdict = True
            elif fname == "user_review.json":
                try:
                    data = json.load(open(fpath, encoding="utf-8"))
                except (OSError, ValueError) as e:
                    print(f"WARN 略過壞檔 {relf}: {e}", file=sys.stderr)
                    continue
                row = user_review_row(brief_id, relf, data)
                rows.append(row)
                if row["sub_brief"]:
                    sub_has_user.add(row["sub_brief"])

    for sub in sorted(sub_has_code):
        if sub not in sub_has_required:
            missing.append(f"sub-briefs/{sub}: 缺 {REQUIRED_SUB_GATE} verdict (*.verdict.json)")
        if sub not in sub_has_user:
            missing.append(f"sub-briefs/{sub}: 缺 reviews/user_review.json")
    if root_has_plan and not root_has_planning_verdict:
        missing.append(f"brief root: 有 plan.md 但缺 {REQUIRED_PLANNING_GATE} verdict")
    return rows, missing


def write_rows(out_path, brief_id, rows):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    kept = []
    if os.path.isfile(out_path):
        for line in open(out_path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                old = json.loads(line)
            except ValueError:
                kept.append(line)
                continue
            if not (old.get("brief_id") == brief_id and old.get("source") == "live"):
                kept.append(json.dumps(old, ensure_ascii=False))
    kept.extend(json.dumps(r, ensure_ascii=False) for r in rows)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + ("\n" if kept else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief_dir")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    if not os.path.isdir(a.brief_dir):
        print(f"brief_dir 不存在: {a.brief_dir}", file=sys.stderr)
        return 1
    rows, missing = scan(a.brief_dir)
    if missing:
        print("verdict 落檔完整性檢查未過:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        if not a.force:
            return 2
        print("--force: 降為警告, 續抽既有檔", file=sys.stderr)
    print(f"brief: {os.path.basename(os.path.normpath(a.brief_dir))}")
    print(f"gate-runs 抽得: {len(rows)}  完整性: {'PASS' if not missing else 'FORCED'}")
    if a.check_only:
        print("check-only: 不寫檔")
        return 0
    out = resolve_out(a.brief_dir, a.out)
    write_rows(out, os.path.basename(os.path.normpath(a.brief_dir)), rows)
    print(f"寫入: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
