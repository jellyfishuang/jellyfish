"""patch_dump.py 測試 (fixture git repo): 完整快照 / 不動真實 index / apply 還原 / 空變更 / binary。

用法: 以 Python 3 執行本檔 (需 git 在 PATH)。改 patch_dump.py 後必跑, 期望 TOTAL FAILURES: 0。"""
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = os.path.join(HERE, "patch_dump.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")  # 子行程 stdout 固定 utf-8, 供字串斷言
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")  # cp950 console 印 detail 不炸

root = tempfile.mkdtemp(prefix="patch_dump_fake_")
src = os.path.join(root, "src")
clone = os.path.join(root, "clone")
patch = os.path.join(root, "out.patch")
fails = 0


def check(name, cond, detail=""):
    global fails
    print(("OK  " if cond else "FAIL") + f" {name} {detail if not cond else ''}")
    fails += 0 if cond else 1


def git(repo, *args, binary=False):
    r = subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t",
                        "-c", "core.autocrlf=false", *args], capture_output=True)
    return r.returncode, (r.stdout if binary else r.stdout.decode("utf-8", errors="replace"))


def w(repo, rel, content, binary=False):
    p = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(p) or p, exist_ok=True) if os.path.dirname(rel) else None
    mode = "wb" if binary else "w"
    with open(p, mode, **({} if binary else {"encoding": "utf-8", "newline": "\n"})) as f:
        f.write(content)


# fixture: base commit → 修改 tracked / 刪 tracked / untracked 新檔(含巢狀) / ignored / binary
os.makedirs(src)
git(src, "init", "-q")
w(src, "keep.go", "package a\n")
w(src, "mod.go", "old\n")
w(src, "del.go", "bye\n")
w(src, "bin.dat", b"\x00\x01\x02", binary=True)
w(src, ".gitignore", "ignored.txt\n")
git(src, "add", "-A")
git(src, "commit", "-qm", "base")
git(src, "clone", "-q", src, clone)  # 乾淨 HEAD 副本 (apply 驗證用)
w(src, "mod.go", "new\n")
os.remove(os.path.join(src, "del.go"))
w(src, "sub/new.go", "package sub\n")
w(src, "ignored.txt", "not me\n")
w(src, "bin.dat", b"\x00\xff\xfe", binary=True)
status_before = git(src, "status", "--porcelain")[1]

# T1: dump exit 0, patch 內容正確
r = subprocess.run([PY, DUMP, src, patch], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", env=ENV)
check("T1 exit 0", r.returncode == 0, r.stderr[:300])
body = open(patch, "rb").read().decode("utf-8", errors="replace")
check("T1 含 tracked 修改", "mod.go" in body and "+new" in body)
check("T1 含刪除", "del.go" in body)
check("T1 含 untracked 巢狀新檔", "sub/new.go" in body)
check("T1 含 binary", "GIT binary patch" in body and "bin.dat" in body)
check("T1 不含 ignored", "ignored.txt" not in body)

# T2: 真實 index / 狀態零改變
status_after = git(src, "status", "--porcelain")[1]
staged = git(src, "diff", "--cached", "--name-only")[1].strip()
check("T2 status 不變", status_before == status_after)
check("T2 無 staged", staged == "")

# T3: 乾淨 HEAD 副本 apply → 檔案內容一致
rc, _ = git(clone, "apply", patch)
check("T3 apply exit 0", rc == 0)
same = (open(os.path.join(clone, "mod.go"), encoding="utf-8").read() == "new\n"
        and not os.path.exists(os.path.join(clone, "del.go"))
        and open(os.path.join(clone, "sub/new.go"), encoding="utf-8").read() == "package sub\n"
        and open(os.path.join(clone, "bin.dat"), "rb").read() == b"\x00\xff\xfe")
check("T3 內容還原一致", same)

# T4: 無變更 → 空 patch, exit 0（clone 剛 apply 過有變更 → 用新 clone）
empty_patch = os.path.join(root, "empty.patch")
clone2 = os.path.join(root, "clone2")
git(root, "clone", "-q", src, clone2)
r4 = subprocess.run([PY, DUMP, clone2, empty_patch], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", env=ENV)
check("T4 無變更 exit 0 + 空檔", r4.returncode == 0 and os.path.getsize(empty_patch) == 0
      and "無變更" in r4.stdout, r4.stdout[-200:])

# T5: 非 git repo → exit 1
r5 = subprocess.run([PY, DUMP, root, patch], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", env=ENV)
check("T5 非 repo exit 1", r5.returncode == 1)

print(f"TOTAL FAILURES: {fails}")
shutil.rmtree(root, ignore_errors=True)
sys.exit(1 if fails else 0)
