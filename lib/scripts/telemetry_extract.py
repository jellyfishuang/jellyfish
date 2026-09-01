#!/usr/bin/env python3
"""Gate 遙測抽取 + verdict 落檔完整性檢查 (brief 歸檔前跑; 確定性機械流程)。

用法 (Python 3):
  python3 telemetry_extract.py <brief_dir> [--check-only] [--force] [--out <jsonl>]

行為:
  1. 掃 <brief_dir> 下所有 reviews/*.verdict.json 與 reviews/user_review.json
  2. 完整性檢查: 每個 code sub-brief (有 stages/engineering/) 須有 >=1 code-reviewer verdict
     + reviews/user_review.json; brief root 有 plan.md 則須 >=1 planning-reviewer verdict。
     缺 → 列缺檔清單 exit 2 (--force 降為警告續抽; --check-only 只檢不寫)
     另檢 code sub-brief 的 artifacts/*.patch 工作成果快照 (patch_dump.py 產) — 缺僅 WARN 不擋 (過渡期)
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
LIVE_READ_TRIGGER = 10    # live brief 數達此值 → 提示跑 gate 遙測首讀 (memory/experiments/)
DRAFT_TRIAL_TRIGGER = 3   # sessions 含 draft_cycles 數值的樣本數達此值 → 提示跑試跑判讀
SEVERITY_PAT = re.compile(r"\b(BLOCKER|CRITICAL|MAJOR|MINOR)\b", re.IGNORECASE)
SEVERITY_ORDER = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR"]


def is_waiver_file(fname):
    """gate 豁免記錄 {gate}.waived.json: 使用者仲裁免跑某 gate 時落檔, 供完整性檢查認得。
    只有使用者仲裁能產生; 內容須指名 arbitration 與依據。"""
    return fname.endswith(".waived.json")


def is_verdict_file(fname):
    """本專案落檔慣例有兩種語序: {role}.verdict.{segment}.json 與 {role}.{segment}.verdict.json。
    原本只認 .verdict.json 結尾, 前者整批逃過機械閘。"""
    return fname.endswith(".json") and ".verdict." in fname


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
    # 兩種語序都要收: {role}.verdict.{segment}.json 與 {role}.{segment}.verdict.json
    base = fname[: -len(".json")] if fname.endswith(".json") else fname
    base = base.replace(".verdict", "")
    base = re.sub(r"\.round[0-9][\w-]*$", "", base)
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
    return base.split(".")[0]   # engineer.S4-fixes → engineer


def top_severity(text):
    hits = [m.group(1).upper() for m in SEVERITY_PAT.finditer(text or "")]
    for s in SEVERITY_ORDER:
        if s in hits:
            return s
    return None


def normalize_checks(checks, relf, warnings):
    """checks 的正規形狀是 list of dict。其他形狀只警告不中斷 (原本直接 AttributeError 炸掉整條歸檔管線)。"""
    if checks is None:
        return []
    if isinstance(checks, dict):
        warnings.append(f"{relf}: checks 是 object 形狀 (正規形狀為 list of dict), 無法抽 findings, 已略過")
        return []
    if not isinstance(checks, list):
        warnings.append(f"{relf}: checks 型別為 {type(checks).__name__} (正規形狀為 list of dict), 已略過")
        return []
    items = [c for c in checks if isinstance(c, dict)]
    if len(items) != len(checks):
        warnings.append(f"{relf}: checks 內有 {len(checks) - len(items)} 個非 dict 項, 該些項已略過")
    return items


def verdict_row(brief_id, relpath, fname, data, warnings):
    sub = sub_brief_of(relpath)
    gate = derive_gate(fname, sub, data)
    actor = data.get("actor") or {}
    m = re.search(r"\.round(\d+)\.verdict\.json$", fname)
    rnd = int(m.group(1)) if m else actor.get("round") or 1
    findings = []
    for c in normalize_checks(data.get("checks"), relpath, warnings):
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
    rows, missing, warnings = [], [], []
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
            if is_verdict_file(fname):
                try:
                    data = json.load(open(fpath, encoding="utf-8"))
                except (OSError, ValueError) as e:
                    print(f"WARN 略過壞檔 {relf}: {e}", file=sys.stderr)
                    continue
                row = verdict_row(brief_id, relf, fname, data, warnings)
                rows.append(row)
                if row["gate"] == REQUIRED_SUB_GATE and row["sub_brief"]:
                    sub_has_required.add(row["sub_brief"])
                if row["gate"] == REQUIRED_PLANNING_GATE and not row["sub_brief"]:
                    root_has_planning_verdict = True
            elif is_waiver_file(fname):
                try:
                    data = json.load(open(fpath, encoding="utf-8"))
                except (OSError, ValueError) as e:
                    print(f"WARN 略過壞檔 {relf}: {e}", file=sys.stderr)
                    continue
                g, wsub = data.get("gate"), sub_brief_of(relf)
                warnings.append(
                    f"{relf}: {g} 由使用者仲裁 {data.get('arbitration') or '?'} 豁免"
                    f" ({str(data.get('reason') or '')[:80]})")
                if g == REQUIRED_SUB_GATE and wsub:
                    sub_has_required.add(wsub)
                if g == REQUIRED_PLANNING_GATE and not wsub:
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
        art = os.path.join(brief_dir, "sub-briefs", sub, "artifacts")
        has_patch = os.path.isdir(art) and any(f.endswith(".patch") for f in os.listdir(art))
        if not has_patch:
            warnings.append(f"sub-briefs/{sub}: 缺 artifacts/*.patch 工作成果快照 (patch_dump.py; 過渡期僅警告)")
    if root_has_plan and not root_has_planning_verdict:
        missing.append(f"brief root: 有 plan.md 但缺 {REQUIRED_PLANNING_GATE} verdict")
    return rows, missing, warnings


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
    rows, missing, warnings = scan(a.brief_dir)
    for w_ in warnings:
        print(f"WARN {w_}", file=sys.stderr)
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
    print_trigger_status(out)
    return 0


def print_trigger_status(out_path):
    """歸檔時機械提示實驗判讀門檻 (不靠人記得)。experiments runbook 見 memory/experiments/。"""
    try:
        live = set()
        if os.path.isfile(out_path):
            for line in open(out_path, encoding="utf-8"):
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("source") == "live":
                    live.add(r.get("brief_id"))
        mem = os.path.dirname(os.path.dirname(out_path))  # memory/
        sess_dir = os.path.join(mem, "sessions")
        drafts = 0
        if os.path.isdir(sess_dir):
            for f in os.listdir(sess_dir):
                if not f.endswith(".md"):
                    continue
                head = open(os.path.join(sess_dir, f), encoding="utf-8").read(2000)
                if re.search(r"^draft_cycles:\s*\d+", head, re.MULTILINE):
                    drafts += 1
        print(f"遙測觸發狀態: live briefs {len(live)}/{LIVE_READ_TRIGGER} (gate 首讀) | "
              f"draft 樣本 {drafts}/{DRAFT_TRIAL_TRIGGER} (紅筆試跑判讀)")
        hits = []
        if len(live) >= LIVE_READ_TRIGGER:
            hits.append("gate 遙測首讀")
        if drafts >= DRAFT_TRIAL_TRIGGER:
            hits.append("draft+redline 試跑判讀")
        if hits:
            print(f">>> 已達判讀門檻: {' + '.join(hits)} — 依 memory/experiments/ 對應 runbook 執行, 並知會使用者")
    except OSError as e:
        print(f"WARN 觸發狀態計算失敗 (不影響抽取): {e}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
