"""brief_close.py 測試 (fake root 全鏈)。用 Python 3 執行, 期望 TOTAL FAILURES: 0。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
CLOSE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brief_close.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

root = tempfile.mkdtemp(prefix="close_fake_")
BID = "2026-01-01-fake-brief"
briefs = os.path.join(root, ".framework", "briefs")
bdir = os.path.join(briefs, BID)
fails = 0


def check(name, cond, detail=""):
    global fails
    print(("OK  " if cond else "FAIL") + f" {name} {detail if not cond else ''}")
    fails += 0 if cond else 1


def w(rel, content):
    p = os.path.join(bdir, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(content)


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
    open(os.path.join(briefs, "_active.yaml"), "w", encoding="utf-8").write(
        f"brief_id: {BID}\nphase: learning\n")


def run(*args):
    return subprocess.run([PY, CLOSE, BID, "--root", root, *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)


# T1: dry-run 全過不搬
build_fixture()
r = run("--dry-run")
check("T1 dry-run exit 0", r.returncode == 0 and "DRY-RUN OK" in r.stdout, (r.stdout + r.stderr)[-400:])
check("T1 未搬移", os.path.isdir(bdir) and os.path.isfile(os.path.join(briefs, "_active.yaml")))

# T2: 真跑 → 歸檔 + 清鎖
r = run()
check("T2 close exit 0", r.returncode == 0 and "CLOSE OK" in r.stdout, (r.stdout + r.stderr)[-400:])
import datetime
ym = datetime.date.today().strftime("%Y-%m")
check("T2 已歸檔", not os.path.isdir(bdir) and os.path.isdir(os.path.join(briefs, "_archive", ym, BID)))
check("T2 鎖已清", not os.path.isfile(os.path.join(briefs, "_active.yaml")))

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

# T5: _active.yaml 屬別的 brief → 歸檔但不刪鎖
build_fixture()
open(os.path.join(briefs, "_active.yaml"), "w", encoding="utf-8").write("brief_id: other-brief\n")
r = run()
check("T5 他人鎖不誤刪", r.returncode == 0 and os.path.isfile(os.path.join(briefs, "_active.yaml"))
      and "保留不刪" in (r.stdout + r.stderr))

# T6: --force 降級續跑
build_fixture()
w("_tree.yaml", "root: %s\nnodes:\n  %s:\n    state: passed\n" % (BID, BID))
r = run("--force")
check("T6 force 續跑歸檔", r.returncode == 0 and "CLOSE OK" in r.stdout, (r.stdout + r.stderr)[-300:])

print(f"TOTAL FAILURES: {fails}")
shutil.rmtree(root, ignore_errors=True)
sys.exit(1 if fails else 0)
