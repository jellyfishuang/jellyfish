"""tree_check.py 測試。用 Python 3 執行, 期望 TOTAL FAILURES: 0。"""
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tree_check.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

root = tempfile.mkdtemp(prefix="tree_fake_")
fails = 0


def check(name, cond, detail=""):
    global fails
    print(("OK  " if cond else "FAIL") + f" {name} {detail if not cond else ''}")
    fails += 0 if cond else 1


def run(content, fname="_tree.yaml"):
    p = os.path.join(root, fname)
    open(p, "w", encoding="utf-8").write(content)
    return subprocess.run([PY, CHECK, p], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=ENV)


GOOD = """root: 2026-01-01-x
created_at: 2026-01-01T10:00:00
last_updated: 2026-01-01T11:00:00
nodes:
  2026-01-01-x:
    state: executing
    parent: null
    holistic_review: null
    brief_stages:
      local_test:
        state: pass
        result_summary: "ok"
  2026-01-01-x.a:
    state: done
    parent: 2026-01-01-x
    pipeline_stages:
      - name: engineering
        state: done
        rounds: { producer: 1, reviewer: 1, adversarial: 0 }
        verdict: pass
      - name: unit_test
        state: skipped
        rounds: { producer: 0, reviewer: 0, adversarial: 0 }
        verdict: skipped
"""

r = run(GOOD)
check("T1 合法 tree（含 skipped/brief_stages pass）", r.returncode == 0 and "nodes=2" in r.stdout, r.stderr[:300])

r = run(GOOD.replace("state: executing", "state: l0_review_passed"))
check("T2 node state 非法擋", r.returncode == 2 and "l0_review_passed" in r.stderr)

r = run(GOOD.replace("        state: done", "        state: passed"))
check("T3 stage state 非法擋", r.returncode == 2 and "passed" in r.stderr)

r = run(GOOD.replace("root: 2026-01-01-x\n", "root: 2026-01-01-x\nstate: executing\n"))
check("T4 頂層攤平擋", r.returncode == 2 and "攤平" in r.stderr)

r = run(GOOD.replace("last_updated: 2026-01-01T11:00:00\n", ""))
check("T5 缺頂層鍵擋", r.returncode == 2 and "last_updated" in r.stderr)

r = run(GOOD.replace("  2026-01-01-x:\n", "  2026-01-01-y:\n"))
check("T6 root 不在 nodes 擋", r.returncode == 2 and "不在 nodes" in r.stderr)

r = run(GOOD.replace("verdict: pass", "verdict: approved"))
check("T7 stage verdict 非法擋", r.returncode == 2 and "approved" in r.stderr)

print(f"TOTAL FAILURES: {fails}")
shutil.rmtree(root, ignore_errors=True)
sys.exit(1 if fails else 0)
