# Framework Hooks（機械閘）

Source of truth。部署 = 複製 `*.py` 到 `<專案>/.framework/hooks/`，再依 `hooks-config.template.json` 把 hooks 區塊寫進 `<專案>/.claude/settings.json`（同步一份到 `_framework_managed_hooks` 供漂移比對）。本版 Claude Code 實測 settings.json 寫入後 hooks 即時生效；若未生效，重啟 session 或 `/hooks` 重載。

## 閘清單

| script | 事件 | 行為 |
|---|---|---|
| `bash_gate.py` | PreToolUse (Bash) | `docker rm/rmi/prune`（子指令位置判定）、`compose down -v` → deny；`compose down`（無 -v）、`git commit/push` → ask。比對前剝除引號/heredoc 內容，換行視同指令分隔，大小寫不敏感 |
| `path_gate.py` | PreToolUse (Write/Edit) | 寫 `.framework/memory/`、`.framework/codex/`、`.claude/skills/` → ask（`memory/sessions/` 例外放行）。比對前 normpath（解 `..`、雙斜線）+ 相對路徑 join cwd |
| `fullwidth_gate.py` | PostToolUse (Write/Edit) | `.go` 檔剝除 string/rune literal（rune 用精確單字元文法）後仍含全形標點 → exit 2 回饋 file:line 清單，agent 當場修正 |

## 設計原則

- deny 只給「確定錯」的指令；不確定一律 ask（寧可多彈提示，不讓 agent 卡死空轉）。
- false deny（擋到正常工作）視為最高嚴重度，寧可放寬也不誤擋。
- 所有 script 內部錯誤 fail-open（exit 0）並記 `gate.log`（與 script 同目錄，無輪替上限，過大可直接刪）。
- hooks 對 subagent 的工具呼叫同樣生效，deny 的 stderr 會回饋給 agent。

## 已知限制

- `bash_gate`：`docker 'rm' x` 這類引號包子指令會放行（刻意規避不在 honest-mistake 防護模型內，不為此加複雜度）；`grep compose down.txt` 這類同段湊齊關鍵字仍會誤觸 ask（僅多一次提示）。line continuation（`\` 換行）視同接續同段。flag+value 判定與撇號/heredoc 剝除為近似法——boolean flag 後接子指令再接 rm 開頭參數（`docker -D stop rm-test`）、glued quote（`-e'pat'`）、無 `-` heredoc body 內恰有 tab+delimiter 獨立行，這三類罕見組合可能誤觸；deny 誤觸時 agent 會收到 stderr 說明，改寫指令即可繞開。
- `fullwidth_gate`：backtick 剝除是**全檔任意兩點配對**（非僅註解內 inline code）——兩個各含單一 backtick 的字串/註解之間的違規會漏檢。
- `path_gate` / `fullwidth_gate`：Bash `echo > file` 重導向寫檔繞得過（framework role 均用 Write/Edit，暫不追）。
- 回歸測試：同目錄 `run_tests.py`（62 case，含三輪對抗式驗證的全部回饋案例；fixture 於執行時自建於 temp）。改任一 gate script 後必跑：`python run_tests.py`，期望 FAILURES: 0。
