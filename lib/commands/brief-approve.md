---
name: brief-approve
description: 批准當前 brief 的 plan，從 Explore 階段進入 Execute
allowed_tools: Read, Write, Edit, Glob, Grep, Task
---

# /brief-approve

批准當前 active brief 的 plan，啟動 Execute 階段（5e 決議的 L0 gate）。

## 用法

```
/brief-approve              # 批准當前 active brief
/brief-approve --comment "..."  # 帶批准備註（記錄在 _manifest.md）
```

## 前置條件

- 有 active brief（`.framework/briefs/_active.yaml` 存在）
- 該 brief 處於 `awaiting_approval` state（Explore Step 6）

## 行為

```
1. 讀 _active.yaml 取 brief_id
2. 讀 _tree.yaml.nodes.{brief_id}.state
3. 若 state != awaiting_approval → 顯示錯誤：
   「當前 brief 處於 {state} 狀態，無法批准。
    若要重看 plan，請看 .framework/briefs/{brief_id}/plan.md」
4. 若 state == awaiting_approval：
   a. 寫 _tree.yaml.nodes.{brief_id}.state = executing
   b. 若 plan 有 sub_briefs：
      for sub in plan.sub_briefs:
        i.   建立目錄 .framework/briefs/{brief_id}/sub-briefs/{sub_id}/
        ii.  寫 sub-brief.md（含 title / scope / depends_on / estimated_complexity / parent reference）
        iii. 寫 plan.md（從 L0 plan 推導：scope 章節 + 從 plan.allowed_paths 取對應 glob + 從 L0 驗收條件取相關項）
        iv.  寫 _manifest.md（人類可讀進度，初始狀態）
        v.   建立 _tree.yaml.nodes.{sub_id}：
             - state: pending
             - parent: {brief_id}
             - children: []
             - depends_on: <從 plan.sub_briefs[i].depends_on>
             - roster: <繼承 root.roster，可被 plan 覆寫>
             - plan: ./sub-briefs/{sub_id}/plan.md
             - artifact: null
             - pipeline_stages: <從 .framework/pipeline.yaml.pipelines.{name}.stages 展開，每項 state=pending>
             - decomposition_origin: explore_step_4
             - worktree: null（後續 step c 設定）
        vi.  寫進 _tree.yaml.nodes.{brief_id}.children
   c. 若無 sub_briefs（單一 sub-brief 範圍）：
      - 視整 brief 為單 sub-brief，建立同 b.i-vi 結構，sub_id = "{brief_id}.a"
   d. 若啟用 worktree（dev recipe 等）：
      for sub_id in 新建的 sub-brief id list:
        - git worktree add .framework/worktrees/brief--{sub_id} -b brief/{sub_id}
        - 寫 _tree.yaml.nodes.{sub_id}.worktree = .framework/worktrees/brief--{sub_id}
   e. 更新 _active.yaml.phase = executing
   f. 更新 _manifest.md（含使用者 comment + 批准時間）
   g. 顯示：「Plan 已批准，進入 Execute 階段。Sub-briefs: {list}」
5. Main 進入 Execute 主迴圈（control-plane.md 第 5 節）
```

## Plan 修改路徑（不批准）

若使用者看 plan 不滿意：

```
不要打 /brief-approve。
直接回覆修改意見：
  「請改 X」
  「sub-brief A 的 scope 太大，拆」
  「驗收條件 #3 不夠具體，要求 ...」

Main 會：
1. 把意見回給 planner role（plan 第 2 輪修改）
2. planner 改完 → planning-reviewer 審
3. 重新顯示新 plan
4. 等 /brief-approve
```

若連續 2 輪 reviewer fail（review-loop §2.2）→ 自動回 Explore Step 3 補訪談。

## 異常

| 狀況 | 處理 |
|---|---|
| 無 active brief | 顯示「無 active brief。/brief-new 開新的」 |
| brief state != awaiting_approval | 顯示當前 state，提示對應動作 |
| 沒讀到 plan.md | 顯示錯誤：「plan.md 不存在，可能 Explore 還在跑」 |
| Worktree 建立失敗（git 錯誤） | 回滾、顯示具體 git 錯誤、不更新 state |

## 跨 sub-brief 並行注意

批准後 main 開始並行排程：
- 無 depends_on 的 sub-brief 同訊息 spawn
- 進度可用 `/brief-status` 看
- L0 holistic review 在所有 sub-brief 完成後 main 自做（不 spawn 額外 role）

## 相關指令

- `/brief-new`
- `/brief-status`
- `/brief-cancel`

## 相關文件

- `.framework/lib/core/control-plane.md`：Step E Execute 主流程
- `.framework/lib/core/e2r-tree.md`：state machine
- `.framework/lib/core/review-loop.md`：plan reviewer 失敗回 Explore 規則
