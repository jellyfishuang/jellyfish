#!/usr/bin/env python3
"""Verdict JSON schema 機械驗證 (typed-interfaces.md §2-3)。main 收 verdict 落檔後跑, 取代 LLM 目測。

用法 (Python 3):
  python3 verdict_check.py <verdict.json>   # 驗單檔 (main §6.3 收 verdict 時)
  python3 verdict_check.py <brief_dir>      # 掃 **/reviews/*.verdict.json 全驗 (歸檔前抽查)

規則:
  verdict ∈ 7 枚舉; actor.{role,type,spec_id,round,stage} 必填 + adversarial bool
  actor.type × verdict 組合表 (producer: pass/partial/ambiguity/needs_decomposition/needs_dependency;
                               reviewer: pass/fail/ambiguity/tool_error)
  summary 必填 (>200 字僅 WARN); producer 的 artifact 必填
  條件必填 (§3.3): pass(reviewer)→checks 全 pass|skipped; fail→checks ≥1 fail;
    ambiguity→questions ≥1 且 ≥1 blocking; needs_decomposition→decomposition_proposal{rationale, sub_briefs≥1};
    needs_dependency→missing_dependency{package, reason}; tool_error→tool_error_details{tool, error};
    partial→partial_completed + partial_missing 皆 ≥1
exit: 0 全過 / 1 檔案或 JSON 錯 / 2 schema 違規 (列明細)。"""
import json
import os
import sys

VERDICTS = {"pass", "fail", "ambiguity", "needs_decomposition", "needs_dependency", "tool_error", "partial"}
BY_TYPE = {"producer": {"pass", "partial", "ambiguity", "needs_decomposition", "needs_dependency"},
           "reviewer": {"pass", "fail", "ambiguity", "tool_error"}}


def validate(data, label):
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
    if at == "producer" and not str(data.get("artifact") or "").strip():
        errs.append("producer 的 artifact 必填")

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
            files += [os.path.join(dirpath, f) for f in fnames if f.endswith(".verdict.json")]
        if not files:
            print(f"brief_dir 下無 *.verdict.json: {target}")
            return 0
    elif os.path.isfile(target):
        files = [target]
    else:
        print(f"目標不存在: {target}", file=sys.stderr)
        return 1

    all_errs, all_warns = [], []
    for f in files:
        label = os.path.relpath(f, target) if os.path.isdir(target) else os.path.basename(f)
        try:
            data = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"{label}: 非合法 JSON: {e}", file=sys.stderr)
            return 1
        errs, warns = validate(data, label)
        all_errs += errs
        all_warns += warns
    for w in all_warns:
        print(f"WARN {w}", file=sys.stderr)
    if all_errs:
        print("verdict schema 違規:", file=sys.stderr)
        for e in all_errs:
            print(f"  - {e}", file=sys.stderr)
        return 2
    print(f"VERDICT OK  files={len(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
