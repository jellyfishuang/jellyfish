---
name: framework-recover
description: 從中斷的 brief 接續（殭屍 _active.yaml / 4 輪上限 failed sub-brief）
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
---

# /framework-recover

從中斷的 brief 接續。對應 `core/batch-lock.md` 第 4 節 + `core/escalation-rules.md` 第 4.3 節。

## 用法

```
/framework-recover
/framework-recover --pid                     # 強制取代既有 pid（多 session 偵測時）
/framework-recover --sub-brief <sub_id>      # 僅針對特定 sub-brief
```

## 行為

```
1. 偵測 _active.yaml：
   - 不存在 → 顯示「無 active brief，無需 recover。要查歷史用 /brief-status」
   - 存在但 pid == 當前 main pid → 顯示「當前 main session 即為主，無需 recover」
   - 存在且 pid != 當前 → 進入 recover 流程
2. Read 對應 _tree.yaml + _manifest.md + _suggestions.json
2.5 若 _active.yaml 有 autonomous_mandate 或 briefs/{id}/_mandate.json 存在：
    a. 跑 `python .framework/scripts/mandate_check.py .framework/briefs/{id}`（驗結構）
    b. status=active → 顯示 mandate 摘要（auto_advance / pre_authorized / do_not_start / 已推進到哪）
       → 問使用者「繼續此授權自主續跑 / 收回改互動模式（標 consumed）」
    c. status=consumed|revoked → 僅列為歷史 trail，不影響 recover 決策
    d. 驗證 exit 2（結構壞）→ 顯示違規明細，視同無 mandate（互動模式），提醒使用者重簽
    e. 舊制散文 mandate（_active.yaml 內 prose block）→ 唸給使用者、建議轉簽 _mandate.json；不自動轉譯
3. 分析 in-flight 節點（state ∈ {executing, reviewing, paused, failed}）
4. 對每節點顯示給使用者並收答
5. 依答更新 _tree.yaml
6. 更新 _active.yaml.pid = 當前、last_heartbeat = now
7. 進 Execute / Review / Learning 主迴圈接續
```

## 顯示範例

```
==========================================
Recover: 2026-05-06-slot-revenue-q2
==========================================

當前狀態：
  Phase: executing
  上次活動：1h 23m 前（主 session 應已中斷）
  Sub-briefs:
    .a  state=done
    .b  state=executing  stage=writing  reviewer round 1（中斷時 reviewer 跑到一半）
    .c  state=pending  depends_on=[a]

──────────────────────────────────────────
Sub-brief .b 處置？
  (a) 重新跑當前 stage（從 spawn writer round 1 開始）
  (b) 標記 stage 完成（人工已介入修正後接續到下一 stage）
  (c) 標記 sub-brief 失敗（不再跑此 sub-brief）
  (d) 取消整個 brief

> a

──────────────────────────────────────────
Sub-brief .c 處置？
  目前 state=pending，depends_on=[a] 已 done
  可直接啟動。是否啟動？(y/n)

> y

──────────────────────────────────────────
✓ 已更新 _tree.yaml
✓ 已更新 _active.yaml（pid 取代為當前）

繼續 Execute...
```

## 處置選項詳細

### (a) 重新跑當前 stage
- pipeline_stages[i].rounds.producer 重置為 0
- pipeline_stages[i].rounds.reviewer **不重置**（cumulative 累計）
- 重新 spawn 該 stage 對應 role

### (b) 標記 stage 完成
- pipeline_stages[i].state = done
- pipeline_stages[i].verdict = pass（手動標）
- 進下一 stage（依 .framework/pipeline.yaml）
- 警告使用者：「跳過 stage 可能影響後續 review；確定？」

### (c) 標記 sub-brief 失敗
- sub-brief.state = failed
- 寫 escalations/{sub_id}-recover-cancelled.md
- 其他 sub-brief 視 depends_on 處理

### (d) 取消整個 brief
- 同 `/brief-cancel`

## --pid 模式

若偵測到「pid != 當前但 last_heartbeat < 5 分鐘」→ 提示：
「另一個 session（pid {other}）可能仍在跑此 brief。
強制取代為當前 pid 會導致該 session 失敗。
確定？(y/N)」

y → 取代 pid，原 session 下次寫入會失敗（因 pid 不匹配）。

## --sub-brief <sub_id> 模式

只針對特定 sub-brief recover，跳過其他節點的詢問。給已知特定 sub-brief 失敗、其他都好的情境。

## 安全網

```
recover 過程中任何寫檔失敗 → 回滾、不更新 pid
recover 完成後立即更新 last_heartbeat（避免又被偵測為殭屍）
```

## 不做的事

- 不自動猜測該怎麼接續（必使用者答）
- 不刪 brief 目錄
- 不刪 worktree（即使 sub-brief 標 cancelled / failed，worktree 留下供使用者參考）

## 相關指令

- `/framework-status`
- `/framework-unlock`（強制清 lock，不接續）
- `/brief-cancel`
- `/brief-status`

## 相關文件

- `core/batch-lock.md`：殭屍偵測
- `core/escalation-rules.md`：升級恢復
- `core/e2r-tree.md`：state machine
