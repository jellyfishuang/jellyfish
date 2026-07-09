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

# 2026-07-09: tool_error 開放 producer (role 前置閘) + artifact 縮域 pass/partial + advisory 路徑
PROD = {"role": "engineer", "type": "producer", "spec_id": "b.a", "round": 0, "stage": "engineering"}

m = {"verdict": "tool_error", "actor": dict(PROD), "summary": "worktree 前置失敗", "artifact": None,
     "tool_error_details": {"tool": "git", "error": "worktree already exists", "remediation_hint": "清 worktree"}}
r = run(m)
check("T9 producer tool_error 合法 (artifact null)", r.returncode == 0, r.stderr[:300])

m = {"verdict": "tool_error", "actor": dict(PROD), "summary": "x", "artifact": None}
r = run(m)
check("T10 producer tool_error 缺 details 擋", r.returncode == 2 and "tool_error_details" in r.stderr)

m = {"verdict": "fail", "actor": dict(PROD), "summary": "x", "artifact": None,
     "checks": [{"name": "t", "result": "fail", "evidence": "boom"}]}
r = run(m)
check("T11 producer fail 仍組合擋", r.returncode == 2 and "組合非法" in r.stderr)

m = {"verdict": "ambiguity", "actor": dict(PROD), "summary": "x", "artifact": None,
     "questions": [{"id": "q1", "text": "?", "severity": "blocking"}]}
r = run(m)
check("T12 producer ambiguity artifact null 合法 (縮域迴歸)", r.returncode == 0, r.stderr[:300])

ADV_ACTOR = {"role": "architecture-reviewer", "type": "reviewer", "spec_id": "b.a",
             "round": 1, "stage": "engineering", "adversarial": False, "advisory": True}
SKETCH = {"focus": "implementation_design", "change": "x", "shape": "a->b", "reuse_vs_new": "復用 []",
          "overlaps_existing": "N", "pattern_divergence": "N", "key_tradeoffs": ["t"], "ack_required": "false"}

m = {"verdict": "clean", "actor": dict(ADV_ACTOR), "summary": "三未來測試皆健康", "design_sketch": dict(SKETCH)}
r = run(m)
check("T13 advisory clean 合法", r.returncode == 0, r.stderr[:300])

m = {"verdict": "clean", "actor": dict(ADV_ACTOR), "summary": "x"}
r = run(m)
check("T14 advisory 缺 design_sketch 擋", r.returncode == 2 and "design_sketch" in r.stderr)

m = {"verdict": "findings", "actor": dict(ADV_ACTOR), "summary": "x", "design_sketch": dict(SKETCH),
     "findings": [{"severity": "advisory", "dimension": "耦合", "finding": "f"}]}
r = run(m)
check("T15 advisory findings 缺必填欄擋", r.returncode == 2 and "why_it_hurts_future" in r.stderr)

m = {"verdict": "pass", "actor": dict(ADV_ACTOR), "summary": "x", "design_sketch": dict(SKETCH)}
r = run(m)
check("T16 advisory 回 7 枚舉 verdict 擋", r.returncode == 2 and "advisory verdict 非法" in r.stderr)

print(f"TOTAL FAILURES: {fails}")
shutil.rmtree(root, ignore_errors=True)
sys.exit(1 if fails else 0)
