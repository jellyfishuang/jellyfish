"""verdict_check.py 測試。用 Python 3 執行, 期望 TOTAL FAILURES: 0。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verdict_check.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

root = tempfile.mkdtemp(prefix="verdict_fake_")
fails = 0


def check(name, cond, detail=""):
    global fails
    print(("OK  " if cond else "FAIL") + f" {name} {detail if not cond else ''}")
    fails += 0 if cond else 1


def run(data, fname="x.verdict.json"):
    p = os.path.join(root, fname)
    json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return subprocess.run([PY, CHECK, p], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=ENV)


REV_PASS = {"verdict": "pass", "actor": {"role": "code-reviewer", "type": "reviewer", "spec_id": "b.a",
                                         "round": 1, "stage": "engineering", "adversarial": False},
            "summary": "ok", "artifact": None,
            "checks": [{"name": "tests", "result": "pass", "evidence": "ok"}]}

r = run(REV_PASS)
check("T1 reviewer pass 合法", r.returncode == 0, r.stderr[:300])

m = json.loads(json.dumps(REV_PASS)); m["verdict"] = "partial"
r = run(m)
check("T2 reviewer 回 partial 組合擋", r.returncode == 2 and "組合非法" in r.stderr)

m = json.loads(json.dumps(REV_PASS)); m["checks"][0]["result"] = "fail"
r = run(m)
check("T3 pass 帶 fail check 擋", r.returncode == 2)

m = {"verdict": "fail", "actor": REV_PASS["actor"], "summary": "x",
     "checks": [{"name": "t", "result": "fail", "evidence": "boom"}]}
r = run(m)
check("T4 fail 合法", r.returncode == 0, r.stderr[:300])

m = {"verdict": "ambiguity", "actor": REV_PASS["actor"], "summary": "x",
     "questions": [{"id": "q1", "text": "?", "severity": "non-blocking"}]}
r = run(m)
check("T5 ambiguity 無 blocking 擋", r.returncode == 2 and "blocking" in r.stderr)

m = {"verdict": "pass", "actor": {"role": "engineer", "type": "producer", "spec_id": "b.a",
                                  "round": 0, "stage": "engineering"},
     "summary": "done", "artifact": None}
r = run(m)
check("T6 producer 無 artifact 擋", r.returncode == 2 and "artifact" in r.stderr)

m = {"verdict": "partial", "actor": dict(m["actor"]), "summary": "x", "artifact": "./f.md",
     "partial_completed": ["a"], "partial_missing": []}
r = run(m)
check("T7 partial 缺 missing 擋", r.returncode == 2)

# brief_dir 模式
bd = os.path.join(root, "brief", "sub-briefs", "a", "stages", "eng", "reviews")
os.makedirs(bd)
json.dump(REV_PASS, open(os.path.join(bd, "code-reviewer.verdict.json"), "w", encoding="utf-8"))
r = subprocess.run([PY, CHECK, os.path.join(root, "brief")], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", env=ENV)
check("T8 brief_dir 模式", r.returncode == 0 and "files=1" in r.stdout, r.stdout[:200])

print(f"TOTAL FAILURES: {fails}")
shutil.rmtree(root, ignore_errors=True)
sys.exit(1 if fails else 0)
