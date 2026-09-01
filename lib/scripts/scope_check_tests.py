"""scope_check.py 測試 (fake multi-repo root + lock registry)。用 Python 3 執行, 期望 TOTAL FAILURES: 0。

fake root 佈局: {root}/SGC_A .. SGC_C 為真 git repo (untracked 檔 = dirty);
.framework/briefs/_active/{bid}.yaml 為 lane lock; legacy 單檔與 fallback 解析各有 case。"""
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
SCOPE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scope_check.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

fails = 0


def check(name, cond, detail=""):
    global fails
    print(("OK  " if cond else "FAIL") + f" {name} {detail if not cond else ''}")
    fails += 0 if cond else 1


def run(root, *args):
    r = subprocess.run([PY, SCOPE, "--root", root, *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def make_root(repos=("SGC_A", "SGC_B", "SGC_C"), dirty=()):
    root = tempfile.mkdtemp(prefix="scope_fake_")
    os.makedirs(os.path.join(root, ".framework", "briefs", "_active"))
    for name in repos:
        d = os.path.join(root, name)
        os.makedirs(d)
        subprocess.run(["git", "-C", d, "init", "-q"], capture_output=True)
        if name in dirty:
            open(os.path.join(d, "junk.go"), "w").write("x\n")
    return root


def lock(root, bid, repos=None, extra=""):
    body = f"brief_id: {bid}\nphase: executing\n"
    if repos is not None:
        body += f"affected_repos: [{', '.join(repos)}]\n"
    body += extra
    open(os.path.join(root, ".framework", "briefs", "_active", f"{bid}.yaml"),
         "w", encoding="utf-8").write(body)


# ── T1 無 lock 無 dirty: 僅報現況, exit 0 ──
r1 = make_root()
rc, out = run(r1)
check("T1 空場僅報現況", rc == 0 and "無 (僅報現況)" in out, out[:200])

# ── T2 --overlap 與各 lane disjoint: 過 ──
r2 = make_root()
lock(r2, "lane1", ["SGC_A"])
rc, out = run(r2, "--overlap", "SGC_B")
check("T2 overlap disjoint 過", rc == 0 and "OVERLAP: 無" in out, out[:200])

# ── T3 --overlap 撞他 lane: exit 2 + 歸屬 ──
rc, out = run(r2, "--overlap", "SGC_A")
check("T3 overlap 撞 lane exit 2", rc == 2 and "lane1" in out and "OVERLAP:" in out, out[:300])

# ── T4 --overlap 撞無主 dirty: exit 2 ──
r4 = make_root(dirty=("SGC_C",))
rc, out = run(r4, "--overlap", "SGC_C")
check("T4 overlap 撞無主 dirty", rc == 2 and "無主" in out, out[:300])

# ── T5 --overlap --self 排除自己的 lock: 過 ──
rc, out = run(r2, "--overlap", "SGC_A", "--self", "lane1")
check("T5 overlap --self 排除自鎖", rc == 0 and "OVERLAP: 無" in out, out[:300])

# ── T6 他 lane 的 dirty = INFO 不違規 ──
r6 = make_root(dirty=("SGC_B",))
lock(r6, "lane1", ["SGC_A"])
lock(r6, "lane2", ["SGC_B"])
rc, out = run(r6, "--repos", "SGC_A")
check("T6 他 lane dirty=INFO", rc == 0 and "INFO(lane:lane2)" in out and "clean scope" in out, out[:400])

# ── T7 無主 dirty + allowed = VIOLATION exit 2 ──
r7 = make_root(dirty=("SGC_C",))
lock(r7, "lane1", ["SGC_A"])
rc, out = run(r7, "--repos", "SGC_A")
check("T7 無主 dirty=VIOLATION", rc == 2 and "VIOLATION" in out and "SGC_C" in out, out[:400])

# ── T8 legacy 單檔 _active.yaml 兼容 (repos 由 brief 目錄 fallback) ──
r8 = make_root()
bdir = os.path.join(r8, ".framework", "briefs", "2026-01-01-legacy")
os.makedirs(bdir)
open(os.path.join(bdir, "plan.md"), "w", encoding="utf-8").write("**affected_repos**: [SGC_A]\n")
open(os.path.join(r8, ".framework", "briefs", "_active.yaml"), "w", encoding="utf-8").write(
    "brief_id: 2026-01-01-legacy\nphase: executing\n")
rc, out = run(r8, "--overlap", "SGC_A")
check("T8 legacy 單檔兼容", rc == 2 and "2026-01-01-legacy" in out, out[:300])

# ── T9 lock 缺 affected_repos 欄 → fallback 解析 brief 目錄 ──
r9 = make_root()
bdir9 = os.path.join(r9, ".framework", "briefs", "lane9")
os.makedirs(bdir9)
open(os.path.join(bdir9, "plan.md"), "w", encoding="utf-8").write("affected_repos: [SGC_B]\n")
lock(r9, "lane9", repos=None)
rc, out = run(r9, "--overlap", "SGC_B")
check("T9 缺欄 fallback 目錄解析", rc == 2 and "lane9" in out, out[:300])

# ── T10 單 lane 無參數: allowed = 該 lock; in-scope dirty = OK ──
r10 = make_root(dirty=("SGC_A",))
lock(r10, "lane1", ["SGC_A"])
rc, out = run(r10)
check("T10 單 lane 無參數", rc == 0 and "OK(in-scope)" in out and "_active/lane1.yaml" in out, out[:400])

# ── T11 多 lane 無參數: 僅報現況+歸屬, 不判違規 ──
r11 = make_root(dirty=("SGC_B",))
lock(r11, "lane1", ["SGC_A"])
lock(r11, "lane2", ["SGC_B"])
rc, out = run(r11)
check("T11 多 lane 無參數僅報現況", rc == 0 and "未指定 --self" in out, out[:400])

# ── T12 --self 單獨用: allowed = 本 lane; 無主 dirty 仍 VIOLATION ──
r12 = make_root(dirty=("SGC_C",))
lock(r12, "lane1", ["SGC_A"])
rc, out = run(r12, "--self", "lane1")
check("T12 --self 定 allowed", rc == 2 and "VIOLATION" in out, out[:400])

# ── T13 --overlap 空值: usage error exit 1 ──
rc, out = run(r2, "--overlap", " ")
check("T13 overlap 空值 exit 1", rc == 1 and "fail-open" in out, out[:200])

# ── T14 --self 不存在的 lock: overlap 模式警告續跑 ──
rc, out = run(r2, "--overlap", "SGC_B", "--self", "ghost")
check("T14 overlap --self 無鎖警告續跑", rc == 0 and "warn" in out.lower(), out[:300])

# ── T15 registry 內 _closing.lock 不被當 lane ──
r15 = make_root()
open(os.path.join(r15, ".framework", "briefs", "_active", "_closing.lock"),
     "w", encoding="utf-8").write("pid: 1\n")
rc, out = run(r15, "--overlap", "SGC_A")
check("T15 _closing.lock 非 lane", rc == 0 and "active lanes: 0" in out, out[:300])

for d in (r1, r2, r4, r6, r7, r8, r9, r10, r11, r12, r15):
    shutil.rmtree(d, ignore_errors=True)

print(f"\nTOTAL FAILURES: {fails}")
sys.exit(1 if fails else 0)
