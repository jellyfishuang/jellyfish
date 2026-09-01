#!/usr/bin/env python3
"""Verdict JSON schema 機械驗證 (typed-interfaces.md §2-3)。main 收 verdict 落檔後跑, 取代 LLM 目測。

用法 (Python 3):
  python3 verdict_check.py <verdict.json>   # 驗單檔 (main §6.3 收 verdict 時)
  python3 verdict_check.py <brief_dir>      # 掃 **/reviews/ 下所有 verdict 檔全驗 (歸檔前抽查)

規則:
  verdict ∈ 7 枚舉; actor.{role,type,spec_id,round,stage} 必填 + adversarial bool
  actor.type × verdict 組合表 (producer: pass/partial/ambiguity/needs_decomposition/needs_dependency/tool_error;
                               reviewer: pass/fail/ambiguity/tool_error)
    — tool_error 2026-07-09 開放 producer (role 前置閘慣例: engineer/test-writer/integration-tester 前置失敗時 emit)
  summary 必填 (>200 字僅 WARN); producer 的 artifact 於 pass/partial 必填 (其餘 verdict 無產出可 null)
  條件必填 (§3.3): pass(reviewer)→checks 全 pass|skipped; fail→checks ≥1 fail;
    ambiguity→questions ≥1 且 ≥1 blocking; needs_decomposition→decomposition_proposal{rationale, sub_briefs≥1};
    needs_dependency→missing_dependency{package, reason}; tool_error→tool_error_details{tool, error};
    partial→partial_completed + partial_missing 皆 ≥1
exit: 0 全過 / 1 檔案或 JSON 錯 / 2 schema 違規 (列明細)。"""
import json
import datetime
import os
import sys

VERDICTS = {"pass", "fail", "ambiguity", "needs_decomposition", "needs_dependency", "tool_error", "partial"}
BY_TYPE = {"producer": {"pass", "partial", "ambiguity", "needs_decomposition", "needs_dependency", "tool_error"},
           "reviewer": {"pass", "fail", "ambiguity", "tool_error"}}

ADVISORY_VERDICTS = {"clean", "findings"}
FINDING_REQUIRED = ("severity", "dimension", "finding", "why_it_hurts_future",
                    "suggested_direction", "evidence", "spec_checked")
SKETCH_REQUIRED = ("focus", "change", "shape", "reuse_vs_new",
                   "overlaps_existing", "pattern_divergence", "key_tradeoffs", "ack_required")


# 2026-08-18 grandfather: 此日之前落檔的 verdict 早於 is_verdict_file() 修好之前, 整批未曾被掃過
# (舊掃描條件只認 .verdict.json 結尾, {role}.verdict.{segment}.json 全數逃過)。
# 這些歷史檔的 schema 違規降為 WARN 不擋歸檔; 之後落的檔一律嚴格。
# 判準用 mtime 而非檔名語序 —— 兩種語序往後都還會用, 用檔名切等於讓閘繼續半殘。
LEGACY_SCHEMA_CUTOFF = datetime.date(2026, 8, 18)


def is_legacy(path):
    try:
        mt = datetime.date.fromtimestamp(os.path.getmtime(path))
    except OSError:
        return False
    return mt < LEGACY_SCHEMA_CUTOFF


def is_verdict_file(fname):
    """本專案落檔慣例有兩種語序: {role}.verdict.{segment}.json 與 {role}.{segment}.verdict.json。
    原本只認 .verdict.json 結尾, 前者整批逃過機械閘。"""
    return fname.endswith(".json") and ".verdict." in fname


def validate_advisory(data, label):
    """advisory verdict (architecture-reviewer role.md §6): verdict ∈ clean|findings, 非 7 枚舉。
    summary 免 200 字 WARN (§5.x 要求詳述三個未來測試)。"""
    errs = []
    v = data.get("verdict")
    if v not in ADVISORY_VERDICTS:
        errs.append(f"advisory verdict 非法: {v} (須 clean|findings)")
    actor = data.get("actor") or {}
    for k in ("role", "spec_id", "stage"):
        if not str(actor.get(k) or "").strip():
            errs.append(f"actor.{k} 必填")
    if not isinstance(actor.get("round"), int):
        errs.append(f"actor.round 須為整數: {actor.get('round')}")
    if not str(data.get("summary") or "").strip():
        errs.append("summary 必填")
    findings = data.get("findings") or []
    if v == "findings" and not findings:
        errs.append("verdict=findings 須附 findings >=1")
    if v == "clean" and findings:
        errs.append("verdict=clean 不應有 findings")
    for i, f in enumerate(findings):
        for k in FINDING_REQUIRED:
            if not str(f.get(k) or "").strip():
                errs.append(f"findings[{i}].{k} 必填")
        if f.get("severity") not in ("blocker", "advisory"):
            errs.append(f"findings[{i}].severity 非法: {f.get('severity')} (須 blocker|advisory)")
    sketch = data.get("design_sketch") or {}
    if not sketch:
        errs.append("design_sketch 必附 (role.md §6.1)")
    else:
        for k in SKETCH_REQUIRED:
            if k not in sketch:
                errs.append(f"design_sketch.{k} 必填")
        if "ack_required" in sketch:
            ack = sketch["ack_required"]
            # canonical bool; 字串 "true"/"false" 寬收 (歷史落檔存在, 2026-07-09 定型別)
            if not (isinstance(ack, bool) or (isinstance(ack, str) and ack.lower() in ("true", "false"))):
                errs.append(f"design_sketch.ack_required 型別非法: {ack!r} (canonical bool, 字串 'true'/'false' 寬收)")
    return [f"{label}: {e}" for e in errs], []


def validate(data, label):
    if (data.get("actor") or {}).get("advisory") is True:
        return validate_advisory(data, label)
    errs, warns = [], []
    v = data.get("verdict")
    if v not in VERDICTS:
        errs.append(f"verdict 非法: {v}")
    actor = data.get("actor") or {}
    for k in ("role", "type", "spec_id", "stage"):
        if not str(actor.get(k) or "").strip():
            errs.append(f"actor.{k} 必填")
    if not isinstance(actor.get("round"), int):
        errs.append(f"actor.round 須為整數: {actor.get('round')}")
    if "adversarial" in actor and not isinstance(actor["adversarial"], bool):
        errs.append("actor.adversarial 須為 bool")
    at = actor.get("type")
    if at not in BY_TYPE:
        errs.append(f"actor.type 非法: {at}")
    elif v in VERDICTS and v not in BY_TYPE[at]:
        errs.append(f"組合非法: {at} 不可回 {v} (typed-interfaces §2.2, main 應拒收轉 tool_error)")
    if not str(data.get("summary") or "").strip():
        errs.append("summary 必填")
    elif len(str(data["summary"])) > 200:
        warns.append(f"summary 超過 200 字 ({len(str(data['summary']))})")
    if at == "producer" and v in ("pass", "partial") and not str(data.get("artifact") or "").strip():
        errs.append("producer 的 artifact 於 pass/partial 必填")

    checks = data.get("checks") or []
    if v == "pass" and at == "reviewer":
        if not checks:
            errs.append("reviewer pass 須附 checks")
        elif any(c.get("result") not in ("pass", "skipped") for c in checks):
            errs.append("pass 的 checks 每項 result 須為 pass|skipped")
    if v == "fail" and not any(c.get("result") == "fail" for c in checks):
        errs.append("fail 須有至少一項 checks result=fail")
    if v == "ambiguity":
        qs = data.get("questions") or []
        if not qs:
            errs.append("ambiguity 須附 questions")
        elif not any(q.get("severity") == "blocking" for q in qs):
            errs.append("ambiguity 的 questions 須含至少一項 severity=blocking")
    if v == "needs_decomposition":
        dp = data.get("decomposition_proposal") or {}
        if not str(dp.get("rationale") or "").strip() or not dp.get("sub_briefs"):
            errs.append("needs_decomposition 須附 decomposition_proposal{rationale, sub_briefs>=1}")
    if v == "needs_dependency":
        md = data.get("missing_dependency") or {}
        if not str(md.get("package") or "").strip() or not str(md.get("reason") or "").strip():
            errs.append("needs_dependency 須附 missing_dependency{package, reason}")
    if v == "tool_error":
        te = data.get("tool_error_details") or {}
        if not str(te.get("tool") or "").strip() or not str(te.get("error") or "").strip():
            errs.append("tool_error 須附 tool_error_details{tool, error}")
    if v == "partial":
        if not data.get("partial_completed") or not data.get("partial_missing"):
            errs.append("partial 須附 partial_completed + partial_missing 各 >=1")
    return [f"{label}: {e}" for e in errs], [f"{label}: {w}" for w in warns]


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    target = os.path.abspath(sys.argv[1])
    files = []
    if os.path.isdir(target):
        for dirpath, _d, fnames in os.walk(target):
            if os.path.basename(dirpath) != "reviews":
                continue
            files += [os.path.join(dirpath, f) for f in fnames if is_verdict_file(f)]
        if not files:
            print(f"brief_dir 下無 verdict 檔: {target}")
            return 0
    elif os.path.isfile(target):
        files = [target]
    else:
        print(f"目標不存在: {target}", file=sys.stderr)
        return 1

    all_errs, all_warns, legacy_errs, legacy_files = [], [], [], set()
    for f in files:
        label = os.path.relpath(f, target) if os.path.isdir(target) else os.path.basename(f)
        try:
            data = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"{label}: 非合法 JSON: {e}", file=sys.stderr)
            return 1
        errs, warns = validate(data, label)
        all_warns += warns
        if errs and is_legacy(f):
            legacy_errs += errs
            legacy_files.add(label)
        else:
            all_errs += errs
    for w in all_warns:
        print(f"WARN {w}", file=sys.stderr)
    if legacy_errs:
        print(f"LEGACY {len(legacy_files)} 檔 {len(legacy_errs)} 條 schema 違規降為警告"
              f" (mtime < {LEGACY_SCHEMA_CUTOFF}, 早於掃描條件修好之前, 不擋歸檔):", file=sys.stderr)
        for e in legacy_errs:
            print(f"  ~ {e}", file=sys.stderr)
    if all_errs:
        print("verdict schema 違規:", file=sys.stderr)
        for e in all_errs:
            print(f"  - {e}", file=sys.stderr)
        return 2
    print(f"VERDICT OK  files={len(files)}"
          + (f"  (legacy 降級 {len(legacy_files)} 檔)" if legacy_files else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
