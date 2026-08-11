# Framework Hooks（機械閘）

Source of truth。部署 = 跑 `/framework-hooks-sync`（確定性機械流程 `lib/scripts/hooks_sync.py`：複製 `*.py` → `.framework/hooks|scripts/`、渲染 `hooks-config.template.json`、合併 `.claude/settings.json` 並保留使用者自加 hooks、鏡像 `_framework_managed_hooks`、跑回歸）。本版 Claude Code 實測 settings.json 寫入後 hooks 即時生效；若未生效，重啟 session 或 `/hooks` 重載。

## 閘清單

| script | 事件 | 行為 |
|---|---|---|
| `bash_gate.py` | PreToolUse (Bash) | `docker rm/rmi/prune`（子指令位置判定）、`compose down -v` → deny；`compose down`（無 -v）、`git commit/push` → ask，**mandate 生效中升級 deny**。比對前剝除引號/heredoc 內容，換行視同指令分隔，大小寫不敏感 |
| `path_gate.py` | PreToolUse (Write/Edit) | 寫 `.framework/memory/`、`.framework/codex/`、`.claude/skills/` → ask（`memory/sessions/` 例外放行），**mandate 生效中升級 deny**。比對前 normpath（解 `..`、雙斜線）+ 相對路徑 join cwd |
| `fullwidth_gate.py` | PostToolUse (Write/Edit) | `.go` 檔剝除 string/rune literal（rune 用精確單字元文法）後仍含全形標點 → exit 2 回饋 file:line 清單，agent 當場修正 |
| `gate_mandate.py` | （共用模組，非 hook） | 判定 user-away mandate 是否生效：`briefs/_active.yaml` 的 `brief_id` + `autonomous_mandate` 指針 → `_mandate.json.status == "active"`。動機：永不可預授權的動作（control-plane §5.6.3）不該對不在場的人彈 ask（會 hang 整條線），deny 的 stderr 讓 agent 換路續跑並記入 on_stop.report。任何讀取/解析失敗回 False（回退 ask）；`GATE_BRIEFS_DIR` 環境變數覆寫 briefs 目錄（測試 fixture 注入用）；gate 端 import 失敗亦回退 ask |

## 設計原則

- deny 只給「確定錯」的指令；不確定一律 ask（寧可多彈提示，不讓 agent 卡死空轉）。
- false deny（擋到正常工作）視為最高嚴重度，寧可放寬也不誤擋。
- 所有 script 內部錯誤 fail-open（exit 0）並記 `gate.log`（與 script 同目錄，無輪替上限，過大可直接刪）。
- hooks 對 subagent 的工具呼叫同樣生效，deny 的 stderr 會回饋給 agent。

## 已知限制

- `bash_gate`：`docker 'rm' x` 這類引號包子指令會放行（刻意規避不在 honest-mistake 防護模型內，不為此加複雜度）；`grep compose down.txt` 這類同段湊齊關鍵字仍會誤觸 ask（僅多一次提示）。line continuation（`\` 換行）視同接續同段。flag+value 判定與撇號/heredoc 剝除為近似法——boolean flag 後接子指令再接 rm 開頭參數（`docker -D stop rm-test`）、glued quote（`-e'pat'`）、無 `-` heredoc body 內恰有 tab+delimiter 獨立行，這三類罕見組合可能誤觸；deny 誤觸時 agent 會收到 stderr 說明，改寫指令即可繞開。
- `fullwidth_gate`：backtick 剝除是**全檔任意兩點配對**（非僅註解內 inline code）——兩個各含單一 backtick 的字串/註解之間的違規會漏檢。
- `path_gate` / `fullwidth_gate`：Bash `echo > file` 重導向寫檔繞得過（framework role 均用 Write/Edit，暫不追）。
- `gate_mandate`：stale active mandate（使用者回場忘標 consumed）會讓 deny 多留一陣——影響 = compose down / 守護路徑寫入（含 learning loop 合法寫入）/ agent 代跑的 git commit-push 被擋；使用者在場標 consumed 即解，且 `brief_close.py` 的 mandate 未收回擋保證不跨 brief 殘留。
- 回歸測試：同目錄 `run_tests.py`（84 case，含三輪對抗式驗證的全部回饋案例 + mandate ask 升級 deny；fixture 於執行時自建於 temp，case 以 `GATE_BRIEFS_DIR` 與真實 repo 隔離，另有 fakeroot 哨兵 case 驗 `__file__` 相對預設路徑與 import 失敗回退）。改任一 gate script 後必跑：`python run_tests.py`，期望 FAILURES: 0。
- `hooks_sync.py` 生命週期測試：`lib/scripts/hooks_sync_tests.py`（fake root：fresh / idempotent / user hook 保留 / 壞 JSON 拒寫 / dry-run）。改 hooks_sync.py 後必跑，期望 TOTAL FAILURES: 0。
- gate 遙測測試：`lib/scripts/telemetry_tests.py`（fake brief fixture：抽取 / 冪等 / 缺檔 exit 2 / --force / --check-only / 報表 / 缺 patch WARN）。改 telemetry_extract.py / telemetry_report.py 後必跑，期望 TOTAL FAILURES: 0。
- patch dump 測試：`lib/scripts/patch_dump_tests.py`（fixture git repo：tracked 改/刪 + untracked 巢狀 + binary + ignored 排除 / 真實 index 零改變 / apply 還原一致 / 空變更）。改 patch_dump.py 後必跑，期望 TOTAL FAILURES: 0。
- mandate 驗證測試：`lib/scripts/mandate_check_tests.py`（fixture brief：合法 / status / 人審關卡入 stages 擋 / 節點存在 / as 限 pass / condition 必填 / rounds cap / 交集 / 壞 JSON）。改 mandate_check.py 後必跑，期望 TOTAL FAILURES: 0。
- verdict schema 測試：`lib/scripts/verdict_check_tests.py`（reviewer/producer 組合表 / 條件必填 / brief_dir 模式）。改 verdict_check.py 後必跑。
- tree schema 測試：`lib/scripts/tree_check_tests.py`（node/stage/brief_stages 三層 state enum / 攤平 / 頂層鍵 / verdict 枚舉）。改 tree_check.py 後必跑。
- brief close 測試：`lib/scripts/brief_close_tests.py`（dry-run / 歸檔+清鎖 / 檢查鏈擋 / mandate active 擋 / 他人鎖不誤刪 / --force）。改 brief_close.py 後必跑。
