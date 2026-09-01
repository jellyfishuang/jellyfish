#!/usr/bin/env python3
"""Brief 收尾機械段: 串檢查鏈 → 歸檔搬移 → 清 lane lock。取代收尾清單 step 7-8 的手動操作。

用法 (Python 3):
  python3 brief_close.py <brief_id> [--root <dir>] [--force] [--dry-run]

流程 (依序, 任一擋下即停):
  0. close-mutex: 取 briefs/_active/_closing.lock (O_EXCL)——多 lane 同時收尾會交錯寫共用
     memory/telemetry/*.jsonl, 故收尾全程序列化; 他 lane 持有且未 stale (<10min) → exit 1 稍候重跑;
     stale 鎖直接搶佔 (crash 殘留)
  1. tree_check.py           — _tree.yaml schema
  2. verdict_check.py        — 已落檔 verdict 全量 schema
  3. session_check.py        — sessions/{id}.md 存在 + learning-loop §4 模板格式 (2026-07-07)
  4. telemetry_extract.py    — gate 遙測抽取 + 落檔完整性 (自帶觸發門檻提示)
  5. _mandate.json 若 status=active → 擋 (須先標 consumed/revoked)
  6. mv briefs/{id} → briefs/_archive/{YYYY-MM}/{id}
     Windows 佔用防護 (2026-07-09 WinError 32 實撞——外部程序 cwd 停在 brief 目錄內即鎖死 rename):
     rename 重試 ×3 → fallback copytree + 逐檔完整性驗證; 副本驗證通過即視為歸檔成功,
     源目錄清除為 best-effort (殘骸不阻斷收尾, 印手動清除指引); 自身 cwd 在 brief 目錄內時先 chdir root
  7. 刪本 lane 的鎖 briefs/_active/{brief_id}.yaml (multi-lane registry, 2026-09-01);
     legacy 單檔 _active.yaml 存在且 brief_id 相符時也刪 (遷移期兼容), 不符 → 保留 + 警告
     (在歸檔副本驗證成功後即清鎖——源目錄殘骸不再擋 lock 清理; 歸檔完全失敗才保留鎖 + exit 1)
--force: 檢查 1-4 降為警告續跑 (使用者明示 skip 時才用, 記 trail); **不豁免第 5 項 mandate 閘**——
         status=active 一律 exit 2 (歸檔永不可預授權, 收回只需使用者一句確認)
--dry-run: 只跑檢查 1-4, 不搬不刪
exit: 0 成功 / 1 用法或內部錯或歸檔失敗 / 2 檢查未過。

前置 (本 script 不代辦, main 先完成): holistic_review 寫入 / local_test / sessions 摘要 / 品質評分 / _suggestions 處理。"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

if hasattr(sys.stdout, "reconfigure"):
    # 子檢查輸出含 UTF-8/替換字元, cp950 console 直接 print 會 UnicodeEncodeError (2026-07-07 實撞)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_check(script, arg):
    r = subprocess.run([sys.executable, os.path.join(HERE, script), arg],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


def files_snapshot(base):
    snap = {}
    for dirpath, _d, fnames in os.walk(base):
        for f in fnames:
            p = os.path.join(dirpath, f)
            snap[os.path.relpath(p, base)] = os.path.getsize(p)
    return snap


def archive_move(bdir, dest):
    """歸檔搬移, Windows 佔用防護 (2026-07-09 WinError 32 實撞)。
    回傳 (ok, husk_left): ok=歸檔副本已完整落地; husk_left=源目錄殘骸未清 (被外部程序佔用)。"""
    for attempt in range(3):
        try:
            os.rename(bdir, dest)
            return True, False
        except OSError:
            if attempt < 2:
                time.sleep(0.3)
    # rename 全敗 (跨卷 / 目錄被佔用) → copy + 驗證; 副本可信才算歸檔成功
    try:
        shutil.copytree(bdir, dest)
    except OSError as e:
        shutil.rmtree(dest, ignore_errors=True)  # 半份副本必撤, 避免「歸檔目標已存在」假象
        print(f"歸檔 copy 失敗: {e}", file=sys.stderr)
        return False, False
    if files_snapshot(bdir) != files_snapshot(dest):
        shutil.rmtree(dest, ignore_errors=True)
        print("歸檔副本完整性驗證不過 (檔案清單/大小不符), 已撤半份副本", file=sys.stderr)
        return False, False
    try:
        shutil.rmtree(bdir)
        return True, False
    except OSError:
        return True, True  # 副本完整, 只是源目錄清不掉 (外部程序佔用) — 不阻斷收尾


def _acquire_closing_lock(briefs):
    """close-mutex: 序列化多 lane 收尾 (telemetry_extract 對共用 jsonl 的寫入無鎖)。
    回傳 lock 路徑; 他 lane 持有且未 stale (<10min) → None。stale 鎖直接搶佔 (crash 殘留)。"""
    reg = os.path.join(briefs, "_active")
    os.makedirs(reg, exist_ok=True)
    p = os.path.join(reg, "_closing.lock")
    for _ in range(2):
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"pid: {os.getpid()}\nat: {datetime.datetime.now().isoformat()}\n".encode())
            os.close(fd)
            return p
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(p)
            except OSError:
                continue  # 剛被釋放, 重試取鎖
            if age > 600:
                print(f"WARN 搶佔 stale _closing.lock (age {int(age)}s)", file=sys.stderr)
                try:
                    os.remove(p)
                except OSError:
                    pass
                continue
            return None
    return None


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

    mutex = _acquire_closing_lock(briefs)
    if mutex is None:
        print("另一 lane 收尾中 (_active/_closing.lock 未釋放且未 stale)——稍候重跑", file=sys.stderr)
        return 1
    try:
        return _close(a, root, briefs, bdir)
    finally:
        try:
            os.remove(mutex)
        except OSError:
            pass


def _close(a, root, briefs, bdir):
    if not os.path.isdir(bdir):
        print(f"brief 目錄不存在: {bdir}", file=sys.stderr)
        return 1
    cwd = os.path.normcase(os.getcwd())
    if cwd == os.path.normcase(bdir) or cwd.startswith(os.path.normcase(bdir) + os.sep):
        os.chdir(root)  # 自身 cwd 在 brief 目錄內會鎖死歸檔 rename (WinError 32)

    failures = []
    for name, script in (("tree_check", "tree_check.py"),
                         ("verdict_check", "verdict_check.py"),
                         ("session_check", "session_check.py"),
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

    mandate_active = False
    mpath = os.path.join(bdir, "_mandate.json")
    if os.path.isfile(mpath):
        try:
            status = json.load(open(mpath, encoding="utf-8")).get("status")
        except ValueError:
            status = "壞 JSON"
        if status == "active":
            print("[mandate] status=active——離場授權未收回, 須先與使用者確認標 consumed/revoked", file=sys.stderr)
            mandate_active = True
        else:
            print(f"[mandate] status={status} (trail, 不擋)")

    if mandate_active:
        # 安全閘: 不受 --force 降級 (§5.6.3 歸檔永不可預授權; 收回 mandate 只需與使用者一句確認)
        print("收尾檢查未過: ['mandate_active']——--force 不豁免此項, 須先標 consumed/revoked", file=sys.stderr)
        return 2
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
    ok, husk = archive_move(bdir, dest)
    if not ok:
        print(f"歸檔失敗——確認無程序佔用 {bdir} (shell cwd 勿停在該目錄內) 後重跑; lane 鎖保留未動",
              file=sys.stderr)
        return 1
    print(f"歸檔: {dest}")

    lock = os.path.join(briefs, "_active", f"{a.brief_id}.yaml")
    legacy = os.path.join(briefs, "_active.yaml")
    if os.path.isfile(lock):
        os.remove(lock)
        print(f"_active/{a.brief_id}.yaml 已刪 (lane 鎖清除)")
    elif os.path.isfile(legacy):
        content = open(legacy, encoding="utf-8").read()
        if f"brief_id: {a.brief_id}" in content:
            os.remove(legacy)
            print("_active.yaml (legacy 單檔) 已刪 (brief_id 相符)")
        else:
            print(f"WARN legacy _active.yaml 的 brief_id 非 {a.brief_id}——保留不刪 (可能屬另一 brief)",
                  file=sys.stderr)
    else:
        print("lane 鎖不存在 (無鎖可清)")
    if husk:
        print(f"WARN 源目錄殘骸未清 (被其他程序佔用; 歸檔副本已完整): 佔用釋放後手動 `rmdir {bdir}`",
              file=sys.stderr)
    print(f"CLOSE OK  {a.brief_id} → _archive/{ym}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
