#!/usr/bin/env python3
"""fullwidth_gate.py 掃描範圍收斂的驗證套件。
每案：寫一個 .go 檔到 tmp -> 組 PostToolUse payload -> 餵進 hook -> 斷言 exit code 與訊息。
"""
import io
import json
import os
import subprocess
import sys
import tempfile

PY = r"C:\Python312\python.exe"
HOOK = r"D:\CodeSpace\SGC\.framework\hooks\fullwidth_gate.py"
OLD = r"D:\CodeSpace\SGC\.framework\hooks\fullwidth_gate.py.bak-20260730"
TMP = tempfile.mkdtemp(prefix="fwgate")

FW_COMMA = "\uff0c"   # ，
FW_PERIOD = "\u3002"  # 。

# 既有檔：第 4 行帶全形標點（pre-existing 違規），其餘乾淨
PRE_EXISTING = (
    "package main\n"
    "\n"
    "// clean half-width comment, nothing wrong here.\n"
    f"// pre-existing dirty comment{FW_COMMA}not touched by this edit{FW_PERIOD}\n"
    "\n"
    "func A() {}\n"
)


def run(hook, payload):
    r = subprocess.run([PY, hook], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True)
    return r.returncode, r.stderr.decode("utf-8", errors="replace")


def write_go(name, content):
    p = os.path.join(TMP, name)
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return p


def payload(tool, path, **ti):
    ti["file_path"] = path
    return {"tool_name": tool, "cwd": TMP, "tool_input": ti}


results = []


def check(label, got, want, detail=""):
    ok = got == want
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: exit={got} (期望 {want}) {detail}")


# --- T1 關鍵回歸：Edit 的新行乾淨，但檔內有存量違規 -> 不該擋 ---
new_clean = "// newly added clean comment, all half-width."
p1 = write_go("t1.go", PRE_EXISTING.replace(
    "// clean half-width comment, nothing wrong here.", new_clean))
code, err = run(HOOK, payload("Edit", p1, old_string="x", new_string=new_clean))
check("T1 新行乾淨+存量違規 -> 放行", code, 0)

# 對照：舊版 hook 對同一案例應該擋下（證明改動生效在正確位置）
code_old, _ = run(OLD, payload("Edit", p1, old_string="x", new_string=new_clean))
check("T1b 舊版 hook 同案例 -> 擋下（對照）", code_old, 2)

# --- T2 Edit 的新行自己帶全形 -> 必擋，且只報該行 ---
new_dirty = f"// newly added dirty comment{FW_COMMA}should be caught{FW_PERIOD}"
p2 = write_go("t2.go", PRE_EXISTING.replace(
    "// clean half-width comment, nothing wrong here.", new_dirty))
code, err = run(HOOK, payload("Edit", p2, old_string="x", new_string=new_dirty))
check("T2 新行帶全形 -> 擋下", code, 2)
only_line3 = (":3" in err) and (":4" not in err)
results.append(only_line3)
print(f"[{'PASS' if only_line3 else 'FAIL'}] T2b 只報第 3 行（新行），不報第 4 行（存量）")
has_note = "既有全形標點" in err
results.append(has_note)
print(f"[{'PASS' if has_note else 'FAIL'}] T2c 訊息含「存量不必回頭修」提示")

# --- T3 Write 帶全形 -> 必擋（整檔皆本次產出）---
p3 = write_go("t3.go", PRE_EXISTING)
code, err = run(HOOK, payload("Write", p3, content=PRE_EXISTING))
check("T3 Write 內容含全形 -> 擋下", code, 2)

# --- T4 Write 全乾淨 -> 放行 ---
clean_file = "package main\n\n// all clean here.\nfunc B() {}\n"
p4 = write_go("t4.go", clean_file)
code, _ = run(HOOK, payload("Write", p4, content=clean_file))
check("T4 Write 全乾淨 -> 放行", code, 0)

# --- T5 MultiEdit：一乾淨一帶全形 -> 擋，只報帶全形那行 ---
src5 = ("package main\n"
        "\n"
        "// edit one clean.\n"
        f"// edit two dirty{FW_COMMA}caught{FW_PERIOD}\n"
        f"// pre-existing dirty{FW_PERIOD}\n"
        "func C() {}\n")
p5 = write_go("t5.go", src5)
code, err = run(HOOK, payload("MultiEdit", p5, edits=[
    {"old_string": "a", "new_string": "// edit one clean."},
    {"old_string": "b", "new_string": f"// edit two dirty{FW_COMMA}caught{FW_PERIOD}"},
]))
check("T5 MultiEdit 其一帶全形 -> 擋下", code, 2)
m5 = (":4" in err) and (":5" not in err)
results.append(m5)
print(f"[{'PASS' if m5 else 'FAIL'}] T5b 只報第 4 行（本次），不報第 5 行（存量）")

# --- T6 new_string 在檔內找不到（stale）-> 放行 + WARN ---
p6 = write_go("t6.go", PRE_EXISTING)
code, _ = run(HOOK, payload("Edit", p6, old_string="x",
                            new_string="// this text is not in the file at all."))
check("T6 new_string 找不到 -> fail-open 放行", code, 0)

# --- T7 非 .go -> 放行 ---
p7 = os.path.join(TMP, "t7.md")
io.open(p7, "w", encoding="utf-8").write(f"# 標題{FW_COMMA}全形{FW_PERIOD}")
code, _ = run(HOOK, payload("Write", p7, content="x"))
check("T7 非 .go 檔 -> 放行", code, 0)

# --- T8 全形在 string literal 內 -> 放行（literal 剝除仍生效）---
lit = 'package main\n\nfunc D() { s := "全形，在字串內。" ; _ = s }\n'
p8 = write_go("t8.go", lit)
code, _ = run(HOOK, payload("Write", p8, content=lit))
check("T8 全形在 string literal 內 -> 放行", code, 0)

# --- T9 存量違規 + Write 乾淨內容：Write 語意=整檔本次產出，故仍擋（設計如此）---
p9 = write_go("t9.go", PRE_EXISTING)
code, _ = run(HOOK, payload("Write", p9, content=PRE_EXISTING))
check("T9 Write 語意=整檔本次產出 -> 存量也算本次（設計）", code, 2)

print("\n" + "=" * 46)
print(f" 結果: {sum(results)} passed, {len(results) - sum(results)} failed")
print("=" * 46)
sys.exit(0 if all(results) else 1)
