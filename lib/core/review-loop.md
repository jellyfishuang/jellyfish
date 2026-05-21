# Review Loop — Fail Verdict 處理規則

> 本文件規範 reviewer 回 `verdict: fail` 時 main 的處理邏輯：1-2 輪同 role 修改、3 輪以上回 Explore、4 輪上限強制升級。
>
> 對應 OMC E²R 的「Review 失敗可觸發重新 Explore」精神，但用實作友善的階梯規則取代純動態決策。

---

## 1. 規則總覽

```
Round 1 (reviewer fail)
  → 同 producer 改，附 reviewer 意見（保留 producer context）
  → reviewer 重審（cumulative round=2）
  ↓
Round 2 (reviewer 仍 fail，cumulative reviewer = 2)
  → 視為 plan 本身可能有問題（同 producer 連續 2 輪不過很罕見）
  → 不再給同 producer 第 3 輪同 plan，直接回 L0 Explore Step 3-4：補訪談 + 改 plan
  → 改完重新批准（/brief-approve）
  → Execute 重新跑該 stage：producer rounds 重置（fresh producer，從 round=1 起）
    但 **reviewer / adversarial / explore rounds 累積不重置**（cumulative）
    → 重跑後 reviewer 第 1 次審 = cumulative round 3
  ↓
Round 3 (post-explore reviewer 第 1 次仍 fail，cumulative reviewer = 3)
  → 給新 producer 一次 retry 機會（fresh producer round=2，cumulative reviewer 即將 round=4）
  ↓
Round 4 (cumulative reviewer = 4，仍 fail)
  → 強制升級使用者
  → 寫 escalation.md（事件詳細紀錄）
  → 暫停此 sub-brief（state=failed）
  → 使用者決定：手動介入 / cancel / 修 plan 重來
```

---

## 2. 詳細階段邏輯

### 2.1 Round 1 fail → Round 2

```
條件：reviewer verdict.verdict=fail, round=1

main 動作：
1. 收 reviewer verdict（含 checks[] 失敗證據）
2. 寫 verdict 至 stages/{stage}/reviews/{reviewer}.verdict.json
3. 更新 _tree.yaml 該 stage rounds.reviewer=1
4. spawn 同 producer，prompt 加：
   - 你的上輪輸出：<artifact 路徑>
   - reviewer 意見：<verdict.checks 失敗項 + summary>
   - 請依意見修改後重新 emit verdict
5. 等 producer 回新 verdict
6. 收新 producer verdict → spawn reviewer round=2
7. 等 reviewer round=2 verdict
```

**Producer context**：保留（同一 subagent name 啟動，但每個 Task call 是新 session；context 透過 prompt 注入歷史）。

### 2.2 Round 2 fail → Round 3 重 Explore

```
條件：reviewer verdict.verdict=fail, round=2

main 動作：
1. 收 reviewer verdict
2. 寫 verdict 與更新 _tree.yaml
3. 判斷：累積 2 輪同 role 修改仍失敗 → 不可能是 producer 個體問題，是 plan 不對
4. 把 sub-brief state 暫設為 paused（while parent 進入 re-Explore）
5. 回到 L0 Explore Step 3-4：
   a. 顯示給使用者：「Stage X 連續 2 輪 review fail。
      失敗原因摘要：<reviewer 累積意見>
      建議：補訪談以修正 plan。是否進入 Explore？」
   b. 使用者同意 → 進 Explore Step 3 補訪談
   c. 使用者拒絕 → 直接強制升級（跳到 4 輪邏輯）
6. Plan 改寫並 reviewer pass 後：
   a. 顯示新 plan 給使用者批准（/brief-approve）
   b. 批准後重新進 Execute
   c. 該 stage 的 producer rounds 重置為 0（fresh producer 從 round=1 起跑）
   d. 該 stage 的 **reviewer rounds 累積不重置**（仍從上次累計繼續往上）
   e. 此次 explore 視為「rounds.explore += 1」
```

**為什麼 2 輪後就回 Explore，而不是 3 輪？**

實測經驗：同 role 連續 3 輪修改仍 fail 的機率極低，通常是 plan 不對而非 producer 不力。提早觸發 Explore 比浪費第 3 輪 producer 更有效率。

### 2.3 Round 3+（Explore 後重新跑）

```
條件：使用者已批准新 plan，重新進 Execute

main 動作：
1. 重 spawn producer（**fresh**，rounds.producer 重置為 1）
2. 重 spawn reviewer（**cumulative round=3**；reviewer rounds 不重置）
3. 若 reviewer round=3 fail → 給新 producer 一次 retry（rounds.producer=2）→ reviewer round=4
4. 若 reviewer round=4 仍 fail → Round 4 強制升級（不再二次重 Explore；見 §2.4）
```

**注意**：`_tree.yaml` 的 `rounds.explore` 累計。`pipeline_stages[i].rounds.producer` **重置**為 0；`rounds.reviewer` / `rounds.adversarial` **不重置**（cumulative）。詳見 §3.1。

### 2.4 Round 4 強制升級

```
條件：第 4 次 reviewer fail 累積（即 Explore 重做後仍 fail）

main 動作：
1. 寫 escalation.md：
   - brief_id, sub_id, stage
   - 4 輪 review 詳細歷史
   - 各輪 producer artifact 摘要
   - 各輪 reviewer 意見
   - main 的判斷（為什麼建議升級）
   - 建議的下一步選項
2. sub-brief state = failed
3. 顯示給使用者：「Sub-brief X 連續 4 輪 review fail，已超過 framework 自動處理上限。
   詳情：<escalation.md 路徑>
   選項：
   (a) 我手動介入修 code/plan 後執行 `/framework-recover` 接續
   (b) `/brief-cancel` 取消整個 brief
   (c) 我看完詳情後再決定（先 hold，brief 保持 failed 狀態）」
4. 暫停此 sub-brief；其他 sub-brief 若無依賴可繼續
```

---

## 3. Round 計數規則

### 3.1 計數對象

| 名稱 | 寫入位置 | 計數什麼 | 上限 | 重置時機 |
|---|---|---|---|---|
| `rounds.producer` | `pipeline_stages[i].rounds`（L1） | 同 producer 在當前 cycle 跑了幾次 | 5（per-producer per-cycle，避免無窮 retry） | Explore 重做時重置（fresh producer） |
| `rounds.reviewer` | `pipeline_stages[i].rounds`（L1） | 同 stage 的 **checklist** reviewer 累計跑了幾次（不含 adversarial） | 4（cumulative，跨 Explore 重做不重置） | **僅 Brief cancel** |
| `rounds.adversarial` | `pipeline_stages[i].rounds`（L1） | 同 stage 的 **adversarial** reviewer 累計跑了幾次（second_review=true 才有） | 2（cumulative） | **僅 Brief cancel** |
| `rounds.explore` | `nodes.{root_id}.rounds`（L0） | L0 Explore 跑了幾次 | 2（首次 + 重做 1 次） | **僅 Brief cancel** |
| `rounds.l0_review` | `nodes.{root_id}.rounds`（L0） | L0 holistic review 跑了幾次 | 同 explore（每次 holistic fail = 一次 explore） | 同 rounds.explore |

**Producer cap = 5**：保護 producer 在 ambiguity / partial / needs_decomposition 等需要 retry 的情境下不會無限循環。達 5 → 升級。**Adversarial fail 觸發的 producer 重做也計入此 cap**。

### 3.2 上限觸發

| 上限 | 觸發動作 |
|---|---|
| `rounds.reviewer == 2`（cumulative，且尚未 explore 過） | 回 Explore（2.2） |
| `rounds.reviewer == 4`（cumulative，post-explore stage 再 fail 一次後達上限） | 強制升級（2.4） |
| `rounds.adversarial >= 2` 且仍 fail | 強制升級（adversarial-deadlock，避免 checklist-pass / adversarial-fail 無窮迴圈） |
| `rounds.explore >= 2` 且 post-replan stage 仍 fail | 強制升級（避免無窮 explore 迴圈） |
| `rounds.producer >= 5`（含 adversarial 觸發的重做） | 強制升級 |

**Adversarial 失敗的迴圈防護**：
場景：checklist round 1 pass → adversarial round 1 fail → producer 重做 round N → checklist round 2 pass → adversarial round 2 fail。
此時 `rounds.adversarial == 2` 達上限 → 強制升級（寫 escalation `adversarial-deadlock`）。
若使用者人介入後 unlock → 必須降到 single pass（`/framework-pipeline-edit` 改該 stage `second_review: false`）才能繼續。

注意：
- `rounds.reviewer` 是 **cumulative** 計數，**不在 Explore 重做時重置**
- `rounds.producer` 在 Explore 重做時重置為 0（fresh producer）
- L0 holistic review fail 時走相同邏輯：fail 一次 → 回 Explore；連 2 次 explore 後仍 fail → 升級

### 3.3 為什麼 explore 上限 2？

第 1 次 explore = 初始；第 2 次 = round 2 fail 後重做。若第 2 次後仍 fail → 不該再 explore（plan 第 2 次寫錯仍 fail，問題已超 framework 能處理範圍，必升級使用者）。

---

## 4. Producer Verdict（非 fail）的處理

review-loop 主要管 reviewer fail。其他 verdict：

| Producer verdict | 處理 |
|---|---|
| `pass` | 進 reviewer 階段（不算 round） |
| `partial` | main 詢問使用者：接受 / 補完 / cancel。接受 → 進 reviewer；補完 → spawn 同 producer 第 2 輪 |
| `ambiguity` | 進 clarification.md 邏輯 |
| `needs_decomposition` | 進 e2r-tree.md 邏輯 |
| `needs_dependency` | 升級使用者裝；暫停 sub-brief |

| Reviewer verdict | 處理 |
|---|---|
| `pass` | 進下一 stage |
| `fail` | 進本文件 review-loop 規則 |
| `ambiguity` | 進 clarification.md（reviewer 也可說「我看不懂這個 artifact 想做什麼」） |
| `tool_error` | 升級使用者修工具；暫停 sub-brief |

---

## 5. 同 Role 的 Producer Context 注入

Round 2 spawn producer 時，main 必注入：

```
[本次任務的標準 prompt（包括 plan / 上游 artifact / skills / codex 等）]

---

## 上輪輸出（你自己做的，本次任務需修改）

<artifact 路徑或內容貼一段>

## Reviewer 意見（依此修改）

<reviewer verdict.summary>

具體失敗檢查項：
<verdict.checks where result=fail>

## 本輪是第 2 輪 / 共 2 輪
若仍無法通過，下一輪將切換新 producer 或 escalate plan。
請仔細依 reviewer 意見修改。
```

Round 3 起（Explore 後重新跑）spawn producer 時：

```
[標準 prompt（plan 已被 Explore 改過）]

---

## 注意：本 stage 之前曾連續 review fail 後 Explore 重做
新 plan 的關鍵改動：<main 摘要>
請依新 plan 重新實作，不要參考舊 artifact。
```

---

## 6. 鐵律

### 6.1 不繞過 fail 放行
即使「reviewer 太嚴格」也不能 main 直接視為 pass。要改 plan 重做或升級。

### 6.2 不允許 reviewer 「半 pass」
Reviewer 的 verdict 必為 `pass` / `fail` / `ambiguity` / `tool_error` 之一（4 個；見 typed-interfaces.md §2.2）。不允許「pass with caveats」自由文字。要附條件 → 用 `partial`（producer 才有）或 `fail`（reviewer）+ checks 細節。

### 6.3 Round 計數與 _tree.yaml 同步
每輪 review 結束 → 立即更新 _tree.yaml.nodes.{sub}.pipeline_stages[i].rounds。不延後寫。

### 6.4 Explore 重做必走完整流程
Round 2 fail 後重 Explore，必走 Step 3 訪談 + Step 4 plan 重寫 + Step 5 reviewer + Step 6 批准。不能 main 偷偷改 plan 跳批准。

### 6.5 同 stage 內並行 producer 的 round 計數
若同 stage 有多 producer（例：併發兩個 engineer 改不同檔），**每個 producer 獨立計算自己的 round**（同一 producer 的 retry 累計到自己）。**Stage 整體 pass 條件**：所有 producer 都 pass + reviewer 對整 stage 出 pass verdict。

### 6.6 Escalation 必寫 escalation.md
Round 4 升級時必寫詳細記錄，不只口頭通知。

兩個位置（見 escalation-rules.md §1 lifecycle 表）：
- 升級當下：`.framework/briefs/{root_id}/_escalations/{timestamp}-{reason}.md`（即時事件檔）
- Brief 結束學習迴圈：mirror 摘要至 `.framework/memory/lessons/escalations/{root_id}-{sub_id}-{stage}.md`（永久紀錄）

---

## 7. Recipe / Pipeline.yaml 對 round 的覆寫

某些 recipe 可能需要不同 round 數（例：研究類可能 1-2 就夠、高風險類可能 1-2-3-4-5）。

`.framework/pipeline.yaml` 可覆寫：

```yaml
review_rounds_override:
  same_role_max: 2          # 默認 2（fail → 回 Explore）
  total_max: 4              # 默認 4（強制升級）
  explore_max: 2            # 默認 2（不再 Explore）
```

或 per-stage 覆寫：

```yaml
stages:
  research:
    role: researcher
    reviewer: source-quality-reviewer
    review_rounds:
      same_role_max: 1     # research 寬鬆，1 輪不過就 Explore
      total_max: 3
```

未提供時用 default。

---

## 8. 範例：完整一輪走完

### 8.1 起始

```
Sub-brief: 2026-05-06-slot-revenue-q2.a
Stage: analysis
Producer: data-analyst (Round 1)
```

### 8.2 第 1 輪：fail

```
Producer 寫 analysis.md → verdict: pass, artifact=...
↓
Reviewer (analysis-reviewer) 審 → verdict: fail, round=1
checks: [{name: cohort_consistency, result: fail, evidence: "用了註冊月份，plan 規定首儲月份"}]
↓
main 寫 verdict → 更新 _tree.yaml.pipeline_stages[i].rounds.reviewer=1
```

### 8.3 第 2 輪：fail

```
spawn data-analyst Round 2，附 reviewer 意見
Producer 改 → verdict: pass
↓
Reviewer 審 → verdict: fail, round=2
checks: [{name: cohort_consistency, result: pass, evidence: "已改成首儲月份"},
         {name: missing_baseline, result: fail, evidence: "缺 baseline 對照組"}]
↓
main 偵測 rounds.reviewer=2 → 觸發回 Explore
顯示使用者：「2 輪 fail，建議回 Explore 補 plan 對 baseline 的要求」
使用者同意 → 進 Explore Step 3 補訪談
```

### 8.4 Explore 重做

```
Step 3 補問：「baseline 對照組要用上一季同期還是去年同期？」
使用者答：「上一季同期」
Step 4 planner 改 plan，加 baseline 章節
Step 5 planning-reviewer pass
Step 6 使用者批准 /brief-approve
↓
_tree.yaml.rounds.explore=2
回 Execute：
  - producer rounds 重置（fresh producer 從 round=1 起）
  - reviewer / adversarial rounds **不重置**（cumulative 仍為 2 / 0）
```

### 8.5 重新跑 stage：pass

```
spawn data-analyst（fresh，rounds.producer=1）
Producer 寫 → verdict: pass
↓
Reviewer 審（cumulative round=3）→ verdict: pass
↓
main：stage 完成（cumulative reviewer = 3，未達 cap 4），進下一 stage
```

---

## 9. 給接手 agent 的提醒

- **`rounds.reviewer == 2` 是回 Explore 的觸發點**，不要試圖讓 producer 跑第 3 輪修同樣的東西
- **Explore 重做時 plan 必有實質改動**：若 planner 重寫的 plan 與舊版相同 → main 偵測（diff），警告使用者「plan 沒實質變更」並要求重新介入
- **使用者可選跳過 Explore 直接 escalate**：若使用者覺得「這問題我直接看比較快」，2.2 流程提供拒絕選項 → 跳到 Round 4 強制升級
- **Escalation.md 是後續 lesson 的素材**：寫得詳細，brief 結束時學習迴圈會引用
- **Round 計數錯誤是常見 bug**：每次寫 verdict 都同步更新 _tree.yaml，don't lazy-write
- **多 producer 並行 stage**：每個 producer 獨立計 round，但 stage 視為「全 pass」才能進下一 stage

---

## 10. 相關文件

- `core/control-plane.md`：main 的整體 Execute 邏輯
- `core/typed-interfaces.md`：verdict schema（fail / partial / ambiguity 等）
- `core/e2r-tree.md`：rounds 寫進 _tree.yaml 哪邊
- `core/clarification.md`：ambiguity verdict 處理
- `core/escalation-rules.md`：Round 4 升級時的 escalation.md 格式
- `core/learning-loop.md`：Brief 結束時 escalation.md 變 lesson
