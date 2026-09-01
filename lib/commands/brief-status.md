---
name: brief-status
description: 跨 lane dashboard（所有 active brief + 等你的關卡 + 產線占用）與單一 brief 詳細
allowed-tools: Read, Glob, Grep
---

# /brief-status

顯示 brief 進度（不修改任何檔）。無參數時是**跨 lane dashboard**——多 lane 並行時使用者注意力才是 scheduler，此視圖回答「我現在該看哪條線」。

## 用法

```
/brief-status              # 跨 lane dashboard（所有 active lane + 等你的關卡 + 產線占用 + inbox 可開案）
/brief-status all          # 列所有歷史 brief（含歸檔）
/brief-status {brief_id}   # 單一 brief 詳細（active 或已歸檔皆可）
```

## 行為（無參數 → dashboard）

```
1. 掃 .framework/briefs/_active/*.yaml（跳過 _ 開頭檔；每份 = 一條 lane）
   偵測到 legacy 單檔 _active.yaml → 一併列出 + 提示搬遷（batch-lock.md §8）
2. 逐 lane 讀 .framework/briefs/{brief_id}/_tree.yaml（取 user-actor stage 與進度）
3. 分類每條 lane：
   等你的關卡 = phase ∈ {awaiting_approval, on_hold} 或 _tree 有 user-actor stage 待處理
               （user_code_review / plan_approval / amendment 進行中 / architecture ack 待回）
               或 lane 殭屍（last_heartbeat > 1hr，標註建議 /framework-recover）
   自主推進中 = 其餘（executing / reviewing / local_test / learning；標註 mandate 是否 active）
4. 產線占用 = 各 lane 的 affected_repos 反查表
5. inbox 可開案 = 掃 briefs/inbox/*.md 的 affected_repos 宣告，列出與所有 active lane 無交集
   且狀態非「討論中」者（排隊中但可立即開的 brief）
6. 尾附近期歸檔（最近 5 個，從 .framework/memory/sessions/ 排序）
```

## 顯示格式（dashboard）

```
══ 等你的關卡 ═══════════════════════════════════
  2026-09-01-wallet-rounding    ⏸ awaiting_approval（plan 已出 40 分鐘）
  2026-08-30-mtg-cancel-flow    ⏸ user_code_review（sub .b）
══ 自主推進中 ═══════════════════════════════════
  2026-08-29-otel-phase3        ▶ executing（mandate active；.a engineering round 2）
══ 產線占用 ═════════════════════════════════════
  SGC_WalletService, SGC_WalletClient   ← wallet-rounding
  SGC_ProviderBetService                ← mtg-cancel-flow
  SGC_ProviderGatewayService            ← otel-phase3
══ inbox 可開案（與現有 lane 無交集）═════════════
  bet-index-slimming（SGC_ProviderBetService ← 占用中，暫不可）
  google-ads-conversion-upload（討論中，不列）
  device-metrics-split（SGC_PlayerInfoService）→ /brief-import 可開

近期歸檔（最近 5 個）：
- 2026-08-28-cancel-errorcode   [done]
- ...
```

- 無任何 active lane → 「目前無 active brief」+ inbox 可開案 + 近期歸檔
- 單 lane 時 dashboard 自動附上該 lane 的 sub-brief 樹（同單一 brief 詳細的縮減版）

## 顯示格式（特定 brief_id，active lane）

```
==========================================
Lane: 2026-09-01-wallet-rounding
==========================================

階段：Execute
Recipe: dev-team
Pipeline: new_feature
affected_repos: [SGC_WalletService, SGC_WalletClient]（scope_status: confirmed）
啟動時間：2026-09-01 10:00 (1h 23m ago)  heartbeat: 3m ago

────────────────────────────────────────
L0: 2026-09-01-wallet-rounding
   State: executing
   Roster: planner, engineer, code-reviewer
   Plan: ./plan.md (批准於 10:30)

   Sub-briefs:
   ├─ .a   state=done    (engineering 完成 11:15)
   │       amendments: a1 done (13:08) | a2 amending
   ├─ .b   state=executing  stage=engineering  round 1
   └─ .c   state=pending  depends_on=[a]
────────────────────────────────────────

最新 verdict（讀 _manifest.md 末段）：
  [11:42] engineer Round 1 → producer pass
  [11:43] code-reviewer Round 1 → reviewer fail (error path 未收斂)

下一步：
  - sub-brief .b stage engineering 進入 round 2
```

## Amendment 顯示規則

讀 `_tree.yaml.nodes.{sub_id}.amendments[]`：

- 若陣列為空或欄位缺失 → **不顯示** amendment 行（保持輸出乾淨）
- 若有任一非終態（`amending`） → 列在「下一步」區塊
- 列條目格式：`a{n} {state}{若終態 + 完成時間}`，多項用 `|` 分隔
- 終態（`done` / `done_with_notes` / `rejected` / `cancelled`）只在 sub-brief 行下方顯示，不重複進「下一步」

範例：
```
amendments: a1 done (13:08) | a2 done_with_notes (13:30) | a3 amending
```

## 顯示格式（特定 brief_id，已歸檔）

```
==========================================
Brief: 2026-05-04-tax-policy-summary
==========================================

State: done
Recipe: research-team
Pipeline: full_research
持續時間：2h 15m

關鍵時間軸（從 _manifest.md）：
[10:00] 建立 brief
[10:08] Explore 完成（5 題訪談）
[10:12] Plan 批准
[10:15] 開始 Execute（2 sub-briefs 並行）
[11:30] sub-brief .a done
[11:50] sub-brief .b done
[12:10] L0 holistic review pass
[12:15] 完成、歸檔

歸檔位置：.framework/briefs/_archive/2026-05/2026-05-04-tax-policy-summary/
Session 摘要：.framework/memory/sessions/2026-05-04-tax-policy-summary.md
```

## 行為（all）

```
列所有歷史 brief（從 .framework/memory/sessions/ + .framework/briefs/_archive/ 掃）：
- 按時間倒序
- 顯示：id / state / recipe / 完成時間
- 上限顯示 30 個（更多請直接看 .framework/memory/sessions/）
```

## 異常

| 狀況 | 處理 |
|---|---|
| 某 lane 的 lock 存在但 _tree.yaml 缺失 | 該 lane 標警告：「狀態檔不一致，建議 /framework-recover {brief_id}」（不影響其他 lane 顯示） |
| lock 檔名與內文 brief_id 不符 | 標警告（是 bug；batch-lock §9 鐵律） |
| brief_id 不存在（特定查詢） | 顯示錯誤：「找不到 {brief_id}」+ 列 active lanes 與近期 brief |
| _manifest.md 解析失敗 | 顯示原始內容，警告解析失敗 |
| 偵測到 legacy 單檔 _active.yaml | 列為一條 lane + 提示搬遷至 registry |

## 不做的事

- **不修改任何檔**（純讀取；含不代辦 legacy 搬遷——只提示）
- **不取消 / 不接續**（要這些用 `/brief-cancel` / `/framework-recover`）
- **不展開 stage 內細節到逐 verdict**（要看細節直接 Read `.framework/briefs/{id}/sub-briefs/{sub_id}/stages/`）

## 相關指令

- `/brief-amend <sub_id> "..."` — 對 done 的 sub-brief 做輕量修訂
- `/brief-cancel [brief_id]` — 取消指定 lane
- `/brief-reopen <id>` — 重啟歸檔
- `/framework-recover [brief_id]` — 從中斷恢復指定 lane
- `/framework-status` — framework 整體狀態（roles / settings）

## 相關文件

- `.framework/lib/core/e2r-tree.md`：_tree.yaml schema（含 amendments 欄位）
- `.framework/lib/core/batch-lock.md`：lock registry schema、multi-lane 並發規則
- `.framework/lib/core/amendment.md`：amendment 流程規範
