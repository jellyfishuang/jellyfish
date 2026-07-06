#!/usr/bin/env python3
"""User-away mandate 結構驗證器: 離場授權寫入 / recover 接手時跑, 確保 _mandate.json 機械可解析且不越安全欄。

用法 (Python 3):
  python3 mandate_check.py <brief_dir>    # 讀 <brief_dir>/_mandate.json + _tree.yaml

驗證:
  必填: brief_id / granted_at / status / auto_advance
  status ∈ {active, consumed, revoked}; granted_at ISO 可解析; brief_id == 目錄名
  auto_advance.sub_briefs 各節點存在於 _tree.yaml; stages ⊆ 允許枚舉
    (user_code_review / plan_approval 永不可入 stages——人審關卡只能走 pre_authorized 逐項預授權)
  auto_advance.max_review_rounds ∈ 1..4 (review-loop cap 只可降不可升)
  pre_authorized[]: target 格式 {sub}.{stage} 且 sub 存在; as 只能 "pass"; condition 必填
    (使用者回來後的補救路徑, 如「憑報告 review, 有問題走 amendment」)
  do_not_start[]: sub_brief 存在 + reason 必填; 與 auto_advance.sub_briefs 無交集
不驗但文件明定的安全欄 (control-plane §5.6): HOLD 條件不可豁免;
  git commit/push / memory|codex|skills 寫入 / 歸檔 / 品質評分 / cancel 永不可預授權。
exit: 0 通過 / 1 檔案缺或 JSON 壞 / 2 違規 (列明細)。"""
import datetime
import json
import os
import sys

STATUS = {"active", "consumed", "revoked"}
STAGES = {"engineering", "code-review", "architecture-review", "unit_test", "integration-test", "local_test"}
USER_GATES = {"user_code_review", "plan_approval"}


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    bdir = os.path.abspath(sys.argv[1])
    mpath = os.path.join(bdir, "_mandate.json")
    tpath = os.path.join(bdir, "_tree.yaml")
    if not os.path.isfile(mpath):
        print(f"_mandate.json 不存在: {mpath}", file=sys.stderr)
        return 1
    try:
        m = json.load(open(mpath, encoding="utf-8"))
    except ValueError as e:
        print(f"_mandate.json 非合法 JSON: {e}", file=sys.stderr)
        return 1
    tree = open(tpath, encoding="utf-8").read() if os.path.isfile(tpath) else ""
    brief_id = os.path.basename(os.path.normpath(bdir))

    errs = []

    def sub_exists(sub):
        return f"{brief_id}.{sub}:" in tree

    for k in ("brief_id", "granted_at", "status", "auto_advance"):
        if k not in m:
            errs.append(f"缺必填欄位: {k}")
    if m.get("brief_id") and m["brief_id"] != brief_id:
        errs.append(f"brief_id 不符目錄: {m['brief_id']} != {brief_id}")
    if m.get("status") not in STATUS:
        errs.append(f"status 非法: {m.get('status')} (允許 {sorted(STATUS)})")
    try:
        datetime.datetime.fromisoformat(str(m.get("granted_at", "")))
    except ValueError:
        errs.append(f"granted_at 非 ISO 時間: {m.get('granted_at')}")

    aa = m.get("auto_advance") or {}
    subs = aa.get("sub_briefs") or []
    for s in subs:
        if tree and not sub_exists(s):
            errs.append(f"auto_advance.sub_briefs 節點不存在: {s}")
    for st in aa.get("stages") or []:
        if st in USER_GATES:
            errs.append(f"stages 不可含人審關卡 {st}——人審只能走 pre_authorized 逐項預授權")
        elif st not in STAGES:
            errs.append(f"stages 非法值: {st} (允許 {sorted(STAGES)})")
    mrr = aa.get("max_review_rounds", 4)
    if not (isinstance(mrr, int) and 1 <= mrr <= 4):
        errs.append(f"max_review_rounds 須為 1..4 整數 (review-loop cap 只可降): {mrr}")

    for pa in m.get("pre_authorized") or []:
        tgt = str(pa.get("target", ""))
        if "." not in tgt:
            errs.append(f"pre_authorized.target 格式須為 {{sub}}.{{stage}}: {tgt}")
        else:
            sub = tgt.split(".", 1)[0]
            if tree and not sub_exists(sub):
                errs.append(f"pre_authorized.target 節點不存在: {tgt}")
        if pa.get("as") != "pass":
            errs.append(f"pre_authorized.as 只能 'pass': {tgt} as={pa.get('as')}")
        if not str(pa.get("condition", "")).strip():
            errs.append(f"pre_authorized.condition 必填 (使用者回來後的補救路徑): {tgt}")

    dns = []
    for d in m.get("do_not_start") or []:
        sub = d.get("sub_brief", "")
        dns.append(sub)
        if tree and not sub_exists(sub):
            errs.append(f"do_not_start 節點不存在: {sub}")
        if not str(d.get("reason", "")).strip():
            errs.append(f"do_not_start.reason 必填: {sub}")
    overlap = set(subs) & set(dns)
    if overlap:
        errs.append(f"auto_advance 與 do_not_start 交集: {sorted(overlap)}")

    if errs:
        print("mandate 驗證未過:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 2
    print(f"MANDATE OK  brief={brief_id} status={m['status']} "
          f"auto={subs} pre_auth={len(m.get('pre_authorized') or [])} do_not_start={dns}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
