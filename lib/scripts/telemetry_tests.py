"""telemetry_extract / telemetry_report 測試 (fake brief fixture)。

用法: 以 Python 3 執行本檔 (路徑由檔案位置自推)。改任一 telemetry script 後必跑, 期望 TOTAL FAILURES: 0。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, "telemetry_extract.py")
REPORT = os.path.join(HERE, "telemetry_report.py")

root = tempfile.mkdtemp(prefix="telemetry_fake_")
brief = os.path.join(root, ".framework", "briefs", "2026-01-01-fake-brief")
OUT = os.path.join(root, ".framework", "memory", "telemetry", "gate_runs.jsonl")

fails = 0


def check(name, cond, detail=""):
    global fails
    print(("OK  " if cond else "FAIL") + f" {name} {detail if not cond else ''}")
    fails += 0 if cond else 1


def w(rel, obj):
    p = os.path.join(brief, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def run(*args):
    return subprocess.run([PY, EXTRACT, brief, *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


# fixture: root plan + planning verdict + code sub-brief a (齊)
os.makedirs(brief, exist_ok=True)
open(os.path.join(brief, "plan.md"), "w", encoding="utf-8").write("# plan\n")
w("reviews/planning-reviewer.verdict.json",
  {"verdict": "pass", "actor": {"role": "planning-reviewer", "round": 1, "stage": "planning"},
   "checks": [{"name": "sections", "result": "pass", "evidence": "ok"}]})
os.makedirs(os.path.join(brief, "sub-briefs", "a", "stages", "engineering"), exist_ok=True)
w("sub-briefs/a/stages/engineering/reviews/code-reviewer.verdict.json",
  {"verdict": "fail", "actor": {"role": "code-reviewer", "round": 1, "stage": "engineering"},
   "checks": [{"name": "tests", "result": "fail", "evidence": "MAJOR: TestFoo panics"},
              {"name": "lint", "result": "pass", "evidence": "ok"}]})
w("sub-briefs/a/stages/engineering/reviews/code-reviewer.round2.verdict.json",
  {"verdict": "pass", "actor": {"role": "code-reviewer", "round": 2, "stage": "engineering"},
   "checks": [{"name": "tests", "result": "pass", "evidence": "ok"}]})
w("sub-briefs/a/stages/engineering/reviews/architecture-reviewer.impl-design.verdict.json",
  {"verdict": "pass", "actor": {"role": "architecture-reviewer", "round": 1, "stage": "engineering"},
   "checks": [{"name": "coupling", "result": "pass", "evidence": "ok"}]})
w("sub-briefs/a/reviews/user_review.json",
  {"gate": "user_code_review", "result": "pass",
   "findings": [{"desc": "logger 語系", "severity": "MINOR", "disposition": "fixed_inline"}]})

# T1: 完整 brief → exit 0, rows 正確
r = run()
check("T1 exit 0", r.returncode == 0, r.stderr[:300])
rows = [json.loads(x) for x in open(OUT, encoding="utf-8") if x.strip()]
check("T1 rows=5", len(rows) == 5, str(len(rows)))
gates = sorted(r_["gate"] for r_ in rows)
check("T1 gates", gates == ["architecture-reviewer.impl", "code-reviewer", "code-reviewer",
                            "planning-reviewer", "user_code_review"], str(gates))
cr1 = [x for x in rows if x["gate"] == "code-reviewer" and x["round"] == 1][0]
check("T1 findings 抽取", cr1["findings_count"] == 1 and cr1["findings"][0]["severity"] == "MAJOR")
cr2 = [x for x in rows if x["gate"] == "code-reviewer" and x["round"] == 2][0]
check("T1 round 由檔名", cr2["round"] == 2 and cr2["findings_count"] == 0)
ur = [x for x in rows if x["gate"] == "user_code_review"][0]
check("T1 user disposition", ur["findings"][0]["disposition"] == "fixed_inline" and ur["sub_brief"] == "a")

# T2: 重跑冪等
r2 = run()
rows2 = [json.loads(x) for x in open(OUT, encoding="utf-8") if x.strip()]
check("T2 idempotent", r2.returncode == 0 and len(rows2) == 5, str(len(rows2)))

# T3: 加缺檔 sub-brief b → exit 2 且點名 b
os.makedirs(os.path.join(brief, "sub-briefs", "b", "stages", "engineering"), exist_ok=True)
r3 = run()
check("T3 exit 2", r3.returncode == 2, str(r3.returncode))
check("T3 點名 b", "sub-briefs/b" in r3.stderr and "code-reviewer" in r3.stderr, r3.stderr[:300])

# T4: --force 降警告續抽
r4 = run("--force")
check("T4 force exit 0", r4.returncode == 0, r4.stderr[:300])

# T5: --check-only 不寫檔
os.remove(OUT)
r5 = run("--check-only", "--force")
check("T5 check-only 不寫", r5.returncode == 0 and not os.path.exists(OUT))

# T6: report
run("--force")
r6 = subprocess.run([PY, REPORT, "--jsonl", OUT], capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
check("T6 report exit 0", r6.returncode == 0, r6.stderr[:300])
check("T6 report 內容", "user_code_review" in r6.stdout and "code-reviewer" in r6.stdout
      and "MAJOR:1" in r6.stdout, r6.stdout[:400])

print(f"TOTAL FAILURES: {fails}")
shutil.rmtree(root, ignore_errors=True)
sys.exit(1 if fails else 0)
