"""session_check.py 測試。用 Python 3 執行, 期望 TOTAL FAILURES: 0。"""
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session_check.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

root = tempfile.mkdtemp(prefix="session_fake_")
fails = 0


def check(name, cond, detail=""):
    global fails
    print(("OK  " if cond else "FAIL") + f" {name} {detail if not cond else ''}")
    fails += 0 if cond else 1


def run_file(content, fname="2026-01-01-x.md"):
    p = os.path.join(root, fname)
    open(p, "w", encoding="utf-8").write(content)
    return subprocess.run([PY, CHECK, p], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=ENV)


GOOD = """---
id: 2026-01-01-x
created_at: 2026-01-01T12:00:00
brief_started_at: 2026-01-01T10:00:00
brief_completed_at: 2026-01-01T12:00:00
duration: 2h
recipe: dev-team
roster: [planner, engineer]
state: done
sub_briefs: [a]
clarification_rounds_used: 3
archived_to: ./_archive/2026-01/2026-01-01-x/
---

# Session: 2026-01-01-x

## 摘要

做了 x。

## 關鍵時間軸

- 10:00 開始

## 產出

- plan.md
"""

r = run_file(GOOD)
check("T1 合規檔過", r.returncode == 0 and "SESSION OK" in r.stdout, r.stdout + r.stderr)

r = run_file(GOOD.replace("state: done", "state: completed"))
check("T2 state 非法擋", r.returncode == 2 and "completed" in r.stderr)

r = run_file(GOOD.replace("duration: 2h\n", ""))
check("T3 缺必填鍵擋", r.returncode == 2 and "duration" in r.stderr)

r = run_file(GOOD.replace("## 關鍵時間軸", "## 時間軸"))
check("T4 缺必要 section 擋", r.returncode == 2 and "關鍵時間軸" in r.stderr)

r = run_file(GOOD.replace("id: 2026-01-01-x", "id: 2026-01-01-y"))
check("T5 id 與檔名不符擋", r.returncode == 2 and "不符" in r.stderr)

r = run_file("# Session: 2026-01-01-x\n\n免 frontmatter 舊格式\n")
check("T6 無 frontmatter 擋", r.returncode == 2 and "frontmatter" in r.stderr)

cancelled = GOOD.replace("state: done", "state: cancelled") \
                .replace("## 關鍵時間軸\n\n- 10:00 開始\n\n## 產出\n\n- plan.md\n", "")
r = run_file(cancelled)
check("T7 cancelled 免 section", r.returncode == 0, r.stdout + r.stderr)

# brief_dir 模式: <root>/.framework/briefs/{id} → 找 <root>/.framework/memory/sessions/{id}.md
fw = os.path.join(root, "proj", ".framework")
bdir = os.path.join(fw, "briefs", "2026-01-01-x")
os.makedirs(bdir)
os.makedirs(os.path.join(fw, "memory", "sessions"))
r = subprocess.run([PY, CHECK, bdir], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", env=ENV)
check("T8 brief_dir 模式缺檔擋", r.returncode == 2 and "不存在" in r.stderr)

open(os.path.join(fw, "memory", "sessions", "2026-01-01-x.md"), "w", encoding="utf-8").write(GOOD)
r = subprocess.run([PY, CHECK, bdir], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", env=ENV)
check("T9 brief_dir 模式定位過", r.returncode == 0 and "SESSION OK" in r.stdout, r.stdout + r.stderr)

adir = os.path.join(fw, "briefs", "_archive", "2026-01", "2026-01-01-x")
os.makedirs(adir)
r = subprocess.run([PY, CHECK, adir], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", env=ENV)
check("T10 archive 路徑模式過", r.returncode == 0 and "SESSION OK" in r.stdout, r.stdout + r.stderr)

print(f"TOTAL FAILURES: {fails}")
shutil.rmtree(root, ignore_errors=True)
sys.exit(1 if fails else 0)
