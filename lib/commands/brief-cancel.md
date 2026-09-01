---
name: brief-cancel
description: 取消指定 lane 的 active brief（含 worktree / lock 處置）
allowed-tools: Read, Write, Edit, Bash, Glob
---

# /brief-cancel

取消一條 lane 的 active brief。

## 用法

```
/brief-cancel [brief_id]        # 無參數走解析規則（本 session 的 brief → 唯一 lock → 列清單問）
/brief-cancel --keep-worktree   # 保留 worktree（預設保留，此 flag 是顯式宣告）
/brief-cancel --remove-worktree # 取消時順便清 worktree（謹慎用）
```

## 行為

```
1. 解析 brief_id（本 session 正在跑的 brief → registry 唯一 lock → 多個則列清單要求指定），
   Read .framework/briefs/_active/{brief_id}.yaml
2. 若無任何 active lane → 顯示「無 active brief」退出
   （取消非本 session 持有、且 heartbeat 還新的 lane → 額外警告「該 lane 可能有 session 在跑」）
3. 顯示確認：
   「即將取消 brief: {brief_id}
    當前狀態：
      Phase: {phase}
      Sub-briefs: {進度摘要}
      已花時間：{x}h
    取消後：
      - 寫 .framework/briefs/{brief_id}/CANCELLED 標記
      - 跑簡短學習迴圈（僅寫 sessions）
      - 預設保留 worktree（後續可手動清）
      - 刪本 lane 的 lock（_active/{brief_id}.yaml；他 lane 不受影響）

    確定取消？(y/N)」
4. y →
   a. 寫 .framework/briefs/{brief_id}/CANCELLED：
      ```
      cancelled_at: {ISO}
      cancelled_by: user
      reason: {可選，使用者填}
      ```
   b. 詢問取消原因（一行字、可空）
   c. 跑簡短學習迴圈（learning-loop §10）：
      - 寫 .framework/memory/sessions/{brief_id}.md（state=cancelled）
      - 不跑品質評分 / suggest_*
   d. 若 --remove-worktree：
      for each worktree in _tree.yaml.nodes.*.worktree:
        git worktree remove {path}
   e. 若預設（keep）：
      留 worktree + 寫 WORKTREE_ABANDONED.md 標記（如 14d 規則）
   f. 刪 _active/{brief_id}.yaml
   g. 顯示「✓ Brief 已取消」
5. N → 退出
```

## CANCELLED 標記檔

```yaml
# .framework/briefs/{brief_id}/CANCELLED
cancelled_at: 2026-05-06T15:30:00
cancelled_by: user
reason: "需求變動，不再做"
phase_at_cancel: executing
sub_briefs_at_cancel:
  a: done
  b: executing
worktrees_kept: [.framework/worktrees/brief--2026-05-06-x.b]
```

## --remove-worktree 模式

額外：
```
for each worktree:
  git worktree remove --force {worktree_path}
  顯示：「Removed worktree {path}」
```

警告：使用者尚未 commit 的 code 會丟失。互動模式下會二次確認。

## 取消後的處置

- brief 目錄仍在 `.framework/briefs/{brief_id}/`（不歸檔）
- 後續若要恢復：
  - `/brief-reopen {brief_id}` 重啟（Phase B 才實作）
  - 或手動建新 brief 引用既有 plan / artifacts
- 後續若要徹底清：
  - `rm -rf .framework/briefs/{brief_id}/`
  - `rm -rf .framework/worktrees/brief--{sub_id}/`（若 keep 了）
  - `git branch -D brief/{sub_id}`（若有）

## 異常

| 狀況 | 處理 |
|---|---|
| Worktree remove 失敗（有 uncommitted changes） | 警告 + 預設 keep；提示使用者手動 commit / stash 後再清 |
| lock 檔損毀 | 提示使用者用 /framework-unlock {brief_id} |

## 與其他指令對比

| 指令 | 用途 | 保留進度？ |
|---|---|---|
| `/brief-cancel [id]` | 明示取消指定 lane | 是（brief 目錄保留 + sessions 摘要） |
| `/framework-recover [id]` | 從中斷接續指定 lane | 是 |
| `/framework-unlock <id>` | 強制解指定 lane 的 lock | 是（brief 目錄保留但無 lock） |
| `rm .framework/briefs/{id}` | 徹底清 | 否 |

`/brief-cancel` 是「**正常 cancel**」，比 unlock 乾淨：寫 CANCELLED 標記、跑簡短學習迴圈、有取消理由紀錄。

## 相關指令

- `/brief-status`
- `/brief-reopen <id>`
- `/framework-recover`
- `/framework-unlock`

## 相關文件

- `core/learning-loop.md` §10：取消版迴圈
- `core/batch-lock.md`：lock 處置
