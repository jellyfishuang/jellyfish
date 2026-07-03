---
name: brief-reopen
description: 重啟已歸檔 / 已取消的 brief
allowed-tools: Read, Write, Edit, Bash, Glob, Task
---

# /brief-reopen

重啟既有 brief（已 done / cancelled 的）為新一輪 active brief。

## 用法

```
/brief-reopen <brief_id>
/brief-reopen <brief_id> --as-new   # 視為全新 brief（不繼承 plan）
```

## 適用情境

- 完成的 brief 後續發現需要補做（reviewer 漏抓的 bug、需求變更）
- 取消的 brief 重新評估後決定接續
- 歷史 brief 作為新 brief 的起點（拷貝 plan）

## 行為（預設）

```
1. 確認 brief 存在：
   - 先看 .framework/briefs/{brief_id}/（in-flight 但 cancelled / failed）
   - 再看 .framework/briefs/_archive/{year-month}/{brief_id}/（已歸檔）
2. 若都找不到 → 顯示錯誤 + 列近期 brief
3. 確認當前無 active brief（若有，同 /brief-new 處置）
4. 顯示原 brief 摘要（state / 完成時間 / sub-briefs / 是否有 final artifact）
5. 詢問 reopen 類型：
   (a) 接續執行（從中斷點 / cancelled 點繼續）
   (b) 重做（plan 保留，所有 sub-brief artifact 重新產出）
   (c) Plan 為起點開新 brief（複製 plan 到新 brief_id，原 brief 不動）
   (d) 取消 reopen
6. 依答案處理
```

### (a) 接續執行

```
1. 把歸檔目錄移回 .framework/briefs/{brief_id}/（從 _archive/ 還原）
2. 寫 _active.yaml（新 pid / heartbeat）
3. 對 in-flight 節點（state ∈ {executing, paused, failed}）跑類似 /framework-recover 的對話
4. 對 done 節點：保持 done
5. 進入主迴圈
```

### (b) 重做

```
1. 從 _archive/ 還原
2. 把所有 sub-brief 的 state 重置為 pending
3. pipeline_stages.* 重置 rounds 為 0、verdict null
4. plan / brief.md 保留
5. 寫 _active.yaml
6. 進入 Execute 主迴圈（從零開始跑 stage）
```

### (c) Plan 為起點開新 brief

```
1. 計算新 brief_id：{today}-reopen-{原 brief slug}
2. 建 .framework/briefs/{新 id}/
3. 複製原 plan.md → 新 brief 的 plan.md
4. 寫 brief.md（含「reopened from {原 brief_id}」）
5. 略過 Explore Step 1-3（已有 plan），直接進 Step 5 plan 審核
6. 重新批准（因為 brief 標題與背景可能變）
7. 後續同正常流程
```

## --as-new 模式

直接走 (c) 的路徑，跳過詢問。

## 異常

| 狀況 | 處理 |
|---|---|
| Brief 不存在 | 顯示錯誤 + 列近期 |
| 已有 active | 同 /brief-new 處置 |
| 歸檔目錄損毀 | 嘗試從 .framework/memory/sessions/{brief_id}.md 重建 metadata；若也壞 → 退出 |
| 原 worktree 已被刪 | 警告：「(a) (b) 模式需要 worktree 重建。建議改用 (c) 模式」 |

## 注意事項

- **(a) 模式需要原 worktree 還在**：若 worktree 已 git worktree remove，無法接續
- **(b) 模式會丟失原 artifact**：但保留 final.md 為「上一輪結果」備查
- **(c) 模式最乾淨**：原 brief 不動，新 brief 獨立

## Phase 標註

此指令屬 **Phase B**（不在 MVP 必備清單）。Phase A 跑通後再實作。

當前狀態：
- Phase A：本檔已寫，但 main 對 reopen 邏輯的 detail 可能未完整支援
- Phase B：完整測試 reopen 三模式

## 相關指令

- `/brief-status all`（找 reopen 候選）
- `/framework-recover`（in-flight 接續）
- `/brief-new`

## 相關文件

- `core/batch-lock.md`：active 鎖檢查
