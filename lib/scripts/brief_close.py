#!/usr/bin/env python3
"""Brief 收尾機械段: 串檢查鏈 → 歸檔搬移 → 清 _active.yaml。取代收尾清單 step 7-8 的手動操作。

用法 (Python 3):
  python3 brief_close.py <brief_id> [--root <dir>] [--force] [--dry-run]

流程 (依序, 任一擋下即停):
  1. tree_check.py           — _tree.yaml schema
  2. verdict_check.py        — 已落檔 verdict 全量 schema
  3. telemetry_extract.py    — gate 遙測抽取 + 落檔完整性 (自帶觸發門檻提示)
  4. _mandate.json 若 status=active → 擋 (須先標 consumed/revoked)
  5. mv briefs/{id} → briefs/_archive/{YYYY-MM}/{id}
  6. _active.yaml 存在且 brief_id 相符 → 刪; 不符 → 保留 + 警告 (不誤殺別的 brief 的鎖)
--force: 檢查 1-4 降為警告續跑 (使用者明示 skip 時才用, 記 trail)
--dry-run: 只跑檢查 1-4, 不搬不刪
exit: 0 成功 / 1 用法或內部錯 / 2 檢查未過。

前置 (本 script 不代辦, main 先完成): holistic_review 寫入 / local_test / sessions 摘要 / 品質評分 / _suggestions 處理。"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run_check(script, arg):
    r = subprocess.run([sys.executable, os.path.join(HERE, script), arg],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief_id")
    ap.add_argument("--root", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    root = os.path.abspath(a.root) if a.root else os.getcwd()
    briefs = os.path.join(root, ".framework", "briefs")
    bdir = os.path.join(briefs, a.brief_id)
    if not os.path.isdir(bdir):
        print(f"brief 目錄不存在: {bdir}", file=sys.stderr)
        return 1

    failures = []
    for name, script in (("tree_check", "tree_check.py"),
                         ("verdict_check", "verdict_check.py"),
                         ("telemetry_extract", "telemetry_extract.py")):
        rc, out = run_check(script, bdir)
        print(f"[{name}] exit={rc}")
        if out:
            print("  " + out.replace("\n", "\n  "))
        if rc == 2:
            failures.append(name)
        elif rc != 0:
            print(f"{name} 內部錯誤, 中止", file=sys.stderr)
            return 1

    mpath = os.path.join(bdir, "_mandate.json")
    if os.path.isfile(mpath):
        try:
            status = json.load(open(mpath, encoding="utf-8")).get("status")
        except ValueError:
            status = "壞 JSON"
        if status == "active":
            print("[mandate] status=active——離場授權未收回, 須先與使用者確認標 consumed/revoked", file=sys.stderr)
            failures.append("mandate_active")
        else:
            print(f"[mandate] status={status} (trail, 不擋)")

    if failures:
        if not a.force:
            print(f"收尾檢查未過: {failures}——修正後重跑; 使用者明示 skip 才可 --force", file=sys.stderr)
            return 2
        print(f"--force: 降為警告續跑 (未過: {failures})", file=sys.stderr)

    if a.dry_run:
        print("DRY-RUN OK: 檢查完成, 未搬移未清鎖")
        return 0

    ym = datetime.date.today().strftime("%Y-%m")
    dest = os.path.join(briefs, "_archive", ym, a.brief_id)
    if os.path.exists(dest):
        print(f"歸檔目標已存在: {dest}", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(bdir, dest)
    print(f"歸檔: {dest}")

    active = os.path.join(briefs, "_active.yaml")
    if os.path.isfile(active):
        content = open(active, encoding="utf-8").read()
        if f"brief_id: {a.brief_id}" in content:
            os.remove(active)
            print("_active.yaml 已刪 (brief_id 相符)")
        else:
            print(f"WARN _active.yaml 的 brief_id 非 {a.brief_id}——保留不刪 (可能屬另一 brief)", file=sys.stderr)
    else:
        print("_active.yaml 不存在 (無鎖可清)")
    print(f"CLOSE OK  {a.brief_id} → _archive/{ym}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
