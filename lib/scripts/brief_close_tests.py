"""brief_close.py 測試 (fake root 全鏈)。用 Python 3 執行, 期望 TOTAL FAILURES: 0。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

PY = sys.executable
CLOSE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brief_close.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

root = tempfile.mkdtemp(prefix="close_fake_")
BID = "2026-01-01-fake-brief"
briefs = os.path.join(root, ".framework", "briefs")
bdir = os.path.join(briefs, BID)
LOCK = os.path.join(briefs, "_active", BID + ".yaml")  # lane 鎖 (multi-lane registry)
fails = 0


def check(name, cond, detail=""):
    global fails
    print(("OK  " if cond else "FAIL") + f" {name} {detail if not cond else ''}")
    fails += 0 if cond else 1


def w(rel, content):
    p = os.path.join(bdir, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(content)


SESSION_MD = f"""---
id: {BID}
created_at: 2026-01-01T12:00:00
brief_started_at: 2026-01-01T10:00:00
brief_completed_at: 2026-01-01T12:00:00
duration: 2h
recipe: dev-team
roster: [planner, engineer]
draft_cycles: null
fork_count: null
state: done
sub_briefs: [a]
archived_to: ./_archive/2026-01/{BID}/
---

# Session: {BID}

## 摘要

fake。

## 關鍵時間軸

- 10:00 開始

## 產出

- plan.md
"""


def build_fixture():
    shutil.rmtree(os.path.join(root, ".framework"), ignore_errors=True)
    os.makedirs(bdir)
    w("_tree.yaml", "root: %s\ncreated_at: 2026-01-01T10:00:00\nlast_updated: 2026-01-01T11:00:00\n"
      "nodes:\n  %s:\n    state: done\n    holistic_review: pass\n" % (BID, BID))
    w("plan.md", "# plan\n")
    w("reviews/planning-reviewer.verdict.json", json.dumps(
        {"verdict": "pass", "actor": {"role": "planning-reviewer", "type": "reviewer", "spec_id": BID,
                                      "round": 1, "stage": "planning"}, "summary": "ok", "artifact": None,
         "checks": [{"name": "sections", "result": "pass", "evidence": "ok"}]}))
    spath = os.path.join(root, ".framework", "memory", "sessions", BID + ".md")
    os.makedirs(os.path.dirname(spath), exist_ok=True)
    open(spath, "w", encoding="utf-8").write(SESSION_MD)
    os.makedirs(os.path.join(briefs, "_active"), exist_ok=True)
    open(LOCK, "w", encoding="utf-8").write(
        f"brief_id: {BID}\nphase: learning\naffected_repos: [SGC_Fake]\n")


def run(*args):
    return subprocess.run([PY, CLOSE, BID, "--root", root, *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)


# T1: dry-run 全過不搬
build_fixture()
r = run("--dry-run")
check("T1 dry-run exit 0", r.returncode == 0 and "DRY-RUN OK" in r.stdout, (r.stdout + r.stderr)[-400:])
check("T1 未搬移", os.path.isdir(bdir) and os.path.isfile(LOCK))

# T2: 真跑 → 歸檔 + 清鎖
r = run()
check("T2 close exit 0", r.returncode == 0 and "CLOSE OK" in r.stdout, (r.stdout + r.stderr)[-400:])
import datetime
ym = datetime.date.today().strftime("%Y-%m")
check("T2 已歸檔", not os.path.isdir(bdir) and os.path.isdir(os.path.join(briefs, "_archive", ym, BID)))
check("T2 鎖已清", not os.path.isfile(LOCK))

# T3: tree 壞 → exit 2 擋
build_fixture()
w("_tree.yaml", "root: %s\nnodes:\n  %s:\n    state: passed\n" % (BID, BID))
r = run()
check("T3 tree 違規擋", r.returncode == 2 and os.path.isdir(bdir), (r.stdout + r.stderr)[-300:])

# T4: mandate active 擋; consumed 放行
build_fixture()
w("_mandate.json", json.dumps({"brief_id": BID, "granted_at": "2026-01-01T10:00:00", "status": "active",
                               "auto_advance": {"sub_briefs": []}}))
r = run("--dry-run")
check("T4 mandate active 擋", r.returncode == 2 and "mandate" in (r.stdout + r.stderr))
w("_mandate.json", json.dumps({"brief_id": BID, "granted_at": "2026-01-01T10:00:00", "status": "consumed",
                               "auto_advance": {"sub_briefs": []}}))
r = run("--dry-run")
check("T4 consumed 放行", r.returncode == 0, (r.stdout + r.stderr)[-300:])

# T5: 他 lane 的鎖不受影響; legacy 單檔屬別的 brief → 歸檔但不刪
build_fixture()
os.remove(LOCK)  # 本 lane 無 registry 鎖, 只有 legacy 單檔 (他人的)
other_lock = os.path.join(briefs, "_active", "other-lane.yaml")
open(other_lock, "w", encoding="utf-8").write("brief_id: other-lane\n")
open(os.path.join(briefs, "_active.yaml"), "w", encoding="utf-8").write("brief_id: other-brief\n")
r = run()
check("T5 他人鎖不誤刪", r.returncode == 0 and os.path.isfile(os.path.join(briefs, "_active.yaml"))
      and os.path.isfile(other_lock) and "保留不刪" in (r.stdout + r.stderr))
os.remove(other_lock)
os.remove(os.path.join(briefs, "_active.yaml"))

# T5b: legacy 單檔屬本 brief → 遷移期兼容刪除
build_fixture()
os.remove(LOCK)
open(os.path.join(briefs, "_active.yaml"), "w", encoding="utf-8").write(f"brief_id: {BID}\nphase: learning\n")
r = run()
check("T5b legacy 相符即刪", r.returncode == 0 and not os.path.isfile(os.path.join(briefs, "_active.yaml"))
      and "legacy" in (r.stdout + r.stderr), (r.stdout + r.stderr)[-300:])

# T6: --force 降級續跑
build_fixture()
w("_tree.yaml", "root: %s\nnodes:\n  %s:\n    state: passed\n" % (BID, BID))
r = run("--force")
check("T6 force 續跑歸檔", r.returncode == 0 and "CLOSE OK" in r.stdout, (r.stdout + r.stderr)[-300:])

# T7: sessions 缺檔 → session_check 擋 (2026-07-07 gate)
build_fixture()
os.remove(os.path.join(root, ".framework", "memory", "sessions", BID + ".md"))
r = run("--dry-run")
check("T7 缺 sessions 擋", r.returncode == 2 and "session_check" in (r.stdout + r.stderr),
      (r.stdout + r.stderr)[-300:])

# T7b: mandate active 不受 --force 豁免 (安全閘)
build_fixture()
w("_mandate.json", json.dumps({"brief_id": BID, "granted_at": "2026-01-01T10:00:00", "status": "active",
                               "auto_advance": {"sub_briefs": []}}))
r = run("--force")
check("T7b force 不豁免 mandate active", r.returncode == 2 and "不豁免" in (r.stdout + r.stderr)
      and os.path.isdir(bdir), (r.stdout + r.stderr)[-300:])

# T8: 自身 cwd 在 brief 目錄內 → self-guard chdir, 照常歸檔 (2026-07-09 WinError 32 防護)
build_fixture()
r = subprocess.run([PY, CLOSE, BID, "--root", root], cwd=bdir,
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
import datetime as _dt
_ym = _dt.date.today().strftime("%Y-%m")
check("T8 自身 cwd 防護歸檔成功", r.returncode == 0 and "CLOSE OK" in r.stdout
      and os.path.isdir(os.path.join(briefs, "_archive", _ym, BID)),
      (r.stdout + r.stderr)[-400:])
check("T8 鎖已清", not os.path.isfile(LOCK))

# T9: 外部程序 cwd 佔用 brief 目錄 → copy fallback 歸檔完整 + 鎖照清 (殘骸僅 WARN)
build_fixture()
holder = subprocess.Popen([PY, "-c", "import time; time.sleep(60)"], cwd=bdir)
try:
    time.sleep(0.3)
    r = run()
finally:
    holder.terminate()
    holder.wait()
out = r.stdout + r.stderr
archived = os.path.isdir(os.path.join(briefs, "_archive", _ym, BID))
check("T9 佔用下歸檔成功", r.returncode == 0 and "CLOSE OK" in r.stdout and archived, out[-400:])
check("T9 鎖已清 (殘骸不擋 lock)", not os.path.isfile(LOCK))
if os.path.isdir(bdir):  # Windows: rename/rmtree 被佔用擋 → 須有殘骸 WARN; POSIX rename 可成則無殘骸
    check("T9 殘骸有 WARN 指引", "殘骸" in out, out[-400:])
    shutil.rmtree(bdir, ignore_errors=True)

# T10: close-mutex — 他 lane 收尾中 (新鮮 _closing.lock) → exit 1; stale 鎖 → 搶佔續跑
build_fixture()
closing = os.path.join(briefs, "_active", "_closing.lock")
open(closing, "w", encoding="utf-8").write("pid: 99999\n")
r = run("--dry-run")
check("T10 新鮮 _closing.lock 擋", r.returncode == 1 and "收尾中" in (r.stdout + r.stderr),
      (r.stdout + r.stderr)[-300:])
old = time.time() - 700
os.utime(closing, (old, old))  # 仿 crash 殘留 (>10min)
r = run("--dry-run")
check("T10 stale 鎖搶佔續跑", r.returncode == 0 and "搶佔" in (r.stdout + r.stderr),
      (r.stdout + r.stderr)[-300:])
check("T10 mutex 已釋放", not os.path.isfile(closing))

print(f"TOTAL FAILURES: {fails}")
shutil.rmtree(root, ignore_errors=True)
sys.exit(1 if fails else 0)
