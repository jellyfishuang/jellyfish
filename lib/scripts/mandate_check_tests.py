"""mandate_check.py 測試 (fixture brief)。用 Python 3 執行, 期望 TOTAL FAILURES: 0。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mandate_check.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

root = tempfile.mkdtemp(prefix="mandate_fake_")
brief = os.path.join(root, "2026-01-01-fake-brief")
os.makedirs(brief)
open(os.path.join(brief, "_tree.yaml"), "w", encoding="utf-8").write(
    "nodes:\n  2026-01-01-fake-brief:\n    state: executing\n"
    "  2026-01-01-fake-brief.a:\n    state: done\n"
    "  2026-01-01-fake-brief.b:\n    state: executing\n"
    "  2026-01-01-fake-brief.c:\n    state: pending\n")

VALID = {
    "brief_id": "2026-01-01-fake-brief",
    "granted_at": "2026-01-01T18:10:00+08:00",
    "status": "active",
    "auto_advance": {"sub_briefs": ["b"], "stages": ["engineering", "code-review"], "max_review_rounds": 4},
    "pre_authorized": [{"target": "a.user_code_review", "as": "pass", "condition": "憑報告 review，有問題走 amendment"}],
    "do_not_start": [{"sub_brief": "c", "reason": "depends_on b 含使用者 review"}],
    "on_stop": {"report": "user_review_report.md", "covers": ["a", "b"]},
}

fails = 0


def check(name, cond, detail=""):
    global fails
    print(("OK  " if cond else "FAIL") + f" {name} {detail if not cond else ''}")
    fails += 0 if cond else 1


def run(mandate):
    json.dump(mandate, open(os.path.join(brief, "_mandate.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return subprocess.run([PY, CHECK, brief], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=ENV)


def variant(**kw):
    m = json.loads(json.dumps(VALID))
    for k, v in kw.items():
        keys = k.split("__")
        d = m
        for kk in keys[:-1]:
            d = d[kk]
        d[keys[-1]] = v
    return m


r = run(VALID)
check("T1 合法 mandate exit 0", r.returncode == 0 and "MANDATE OK" in r.stdout, r.stderr[:300])

r = run(variant(status="paused"))
check("T2 status 非法 exit 2", r.returncode == 2 and "status" in r.stderr)

m = variant(); m["auto_advance"]["stages"].append("user_code_review")
r = run(m)
check("T3 stages 含人審關卡擋下", r.returncode == 2 and "pre_authorized" in r.stderr)

m = variant(); m["auto_advance"]["sub_briefs"] = ["x"]
r = run(m)
check("T4 節點不存在", r.returncode == 2 and "不存在: x" in r.stderr)

m = variant(); m["pre_authorized"][0]["as"] = "fail"
r = run(m)
check("T5 pre_authorized as 只能 pass", r.returncode == 2)

m = variant(); m["pre_authorized"][0]["condition"] = ""
r = run(m)
check("T6 condition 必填", r.returncode == 2 and "condition" in r.stderr)

m = variant(); m["auto_advance"]["max_review_rounds"] = 9
r = run(m)
check("T7 rounds cap", r.returncode == 2 and "1..4" in r.stderr)

m = variant(); m["do_not_start"][0]["sub_brief"] = "b"
r = run(m)
check("T8 auto 與 do_not_start 交集", r.returncode == 2 and "交集" in r.stderr)

open(os.path.join(brief, "_mandate.json"), "w", encoding="utf-8").write("{broken")
r = subprocess.run([PY, CHECK, brief], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", env=ENV)
check("T9 壞 JSON exit 1", r.returncode == 1)

print(f"TOTAL FAILURES: {fails}")
shutil.rmtree(root, ignore_errors=True)
sys.exit(1 if fails else 0)
