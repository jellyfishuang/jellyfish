# E²R Tree — 任務樹結構與遍歷規範

> 本文件規範 brief 的層級結構、`_tree.yaml` schema、節點狀態機、main 的遍歷邏輯。
>
> 對應 OMC（arXiv:2604.22446）論文的 **Explore-Execute-Review Tree Search**——任務遞迴分解、結果向上彙整、Review 失敗可觸發重 Explore。本框架受限 2 層（L0 + L1），詳見 design-summary 第 8 節。

---

## 1. 樹結構

### 1.1 層級

| 層 | 名稱 | 描述 |
|---|---|---|
| L0 | Root brief | 使用者開的 brief（`/brief-new`） |
| L1 | Sub-brief | Explore 階段或 Execute 階段切的子任務 |
| L2 | **不允許** | 受限 2 層 |

### 1.2 為什麼受限 2 層

1. **Main token 預算**：main 是樹的唯一遍歷者，深度 ≥3 後跨多層 verdict 彙整會爆 context
2. **使用者體感**：3 層以上的分解使用者跟不上進度
3. **Termination 保證**：論文形式化保證在實作不易 reproduce，硬限制更安全

### 1.3 不夠用怎麼辦

當使用者覺得任務真的需要 3 層時：

- **手動拆**：使用者把超大需求拆成多個 root brief，由人類擔任 L0 之上的 dispatcher
- **後續優化**：未來若資料表明 2 層常不夠，再評估升級為 3 層（但要重設計 token 管理）

---

## 1.4 Schema 規範化警告

本章 §2.2 的 `_tree.yaml` schema 與 §4.4 的 `_manifest.md` schema 是 **canonical**——main session 寫入時**必照此格式**。

**禁止自由發揮**：
- 不要把 `nodes.{id}.*` 攤平成 `root.*`（會破壞 multi-node 場景的解析）
- 不要新增 enum 外的 state 值（例：用 `completed` 而非規範的 `done`）
- 不要刪減必備欄位（即使單 sub-brief / planning_only）

**理由**：`/brief-status`、`/framework-recover`、`/brief-reopen` 都依此 schema 解析；偏離的格式會導致這些指令失敗。

---

## 2. `_tree.yaml` Schema

### 2.1 路徑

每 root brief 一份：`.framework/briefs/{root_id}/_tree.yaml`。

### 2.2 完整 schema

```yaml
root: 2026-05-06-slot-revenue-q2
created_at: 2026-05-06T10:00:00
last_updated: 2026-05-06T11:30:00
nodes:
  2026-05-06-slot-revenue-q2:
    state: executing                  # 見 §3.1 L0 enum
    parent: null
    children:
      - 2026-05-06-slot-revenue-q2.a
      - 2026-05-06-slot-revenue-q2.b
    consumed_child_ids: [a, b]        # 已用過的字母（含已 cancelled），決定下個切分用哪個字母
    roster:
      - data-analyst
      - analysis-reviewer
      - writer
    plan: ./plan.md
    artifact: null                    # L0 通常 null（沒有單一 artifact，而是子的彙整）
    pipeline: .framework/pipeline.yaml         # 使用的 pipeline 路徑（通常複製自 recipe）
    started_at: 2026-05-06T10:00:00
    completed_at: null
    rounds:                           # review 輪數紀錄（review-loop.md）
      explore: 1
      l0_review: 0
    holistic_review: null             # null | pass | fail（L0 holistic review 結果）

  2026-05-06-slot-revenue-q2.a:
    state: done
    parent: 2026-05-06-slot-revenue-q2
    children: []
    depends_on: []                    # 從 plan.sub_briefs 複製進來；其他 sub-brief id 陣列
    roster:                           # 繼承自 parent，可被 plan 覆寫
      - data-analyst
      - analysis-reviewer
    plan: ./sub-briefs/a/plan.md
    artifact: ./sub-briefs/a/final.md
    pipeline_stages:                  # 此 sub-brief 的 stage 進度
      - name: research
        state: done
        rounds: { producer: 1, reviewer: 1, adversarial: 1 }   # adversarial 0 if second_review=false
        verdict: pass
      - name: analysis
        state: done
        rounds: { producer: 2, reviewer: 2, adversarial: 1 }   # checklist 第 2 輪 + adversarial 1 輪通過
        verdict: pass
    started_at: 2026-05-06T10:30:00
    completed_at: 2026-05-06T11:15:00
    decomposition_origin: explore_step_4   # explore_step_4 | execute_needs_decomposition
    worktree: .framework/worktrees/brief--2026-05-06-slot-revenue-q2.a   # null if not used
    amendments: []                    # 見 §2.5；初始為 [] 或省略，amendment 觸發時 append

  2026-05-06-slot-revenue-q2.b:
    state: executing
    parent: 2026-05-06-slot-revenue-q2
    children: []
    roster:
      - writer
      - editor
    plan: ./sub-briefs/b/plan.md
    artifact: null
    pipeline_stages:
      - name: writing
        state: running
        rounds: { producer: 1, reviewer: 0, adversarial: 0 }
        verdict: null
    started_at: 2026-05-06T11:00:00
    completed_at: null
    decomposition_origin: explore_step_4
    worktree: null
```

### 2.3 欄位說明

| 欄位 | 類型 | 說明 |
|---|---|---|
| `root` | string | Root brief id |
| `nodes.{id}.state` | enum | 見 3.1 狀態機 |
| `nodes.{id}.parent` | string \| null | parent id；root 為 null |
| `nodes.{id}.children` | string[] | sub-brief id 陣列；leaf 為 [] |
| `nodes.{id}.depends_on` | string[] | 僅 L1 有；其他 sub-brief id 陣列（從 plan.sub_briefs 複製進來），main 排程依此判斷可動 sub-brief |
| `nodes.{id}.roster` | string[] | 此節點啟用的 role 名稱 |
| `nodes.{id}.plan` | string | plan.md 相對路徑（相對 brief 目錄） |
| `nodes.{id}.artifact` | string \| null | 最終彙整 artifact（L0 通常 null；L1 通常指向 final.md） |
| `nodes.{id}.pipeline` | string | 僅 L0 有；指向 .framework/pipeline.yaml |
| `nodes.{id}.pipeline_stages` | object[] | 僅 L1 有；展開的 stage 進度。每項含 `name`, `state`, `rounds: {producer, reviewer, adversarial}`, `verdict` |
| `nodes.{id}.rounds` | object | 僅 L0 有；各階段 review 輪數累積（含 explore / l0_review） |
| `nodes.{id}.holistic_review` | enum \| null | 僅 L0 有；L0 review 結果 |
| `nodes.{id}.decomposition_origin` | enum | sub-brief 從哪來（Explore Step 4 / Execute needs_decomposition） |
| `nodes.{id}.worktree` | string \| null | 對應 worktree 路徑 |
| `nodes.{id}.amendments` | object[] | 僅 L1 有；amendment 紀錄陣列。見 §2.5。初始可為 `[]` 或省略 |

### 2.4 寫入時機

`_tree.yaml` 由 main session 獨佔寫入。寫入時機：

| 時機 | 寫入內容 |
|---|---|
| Brief 建立（Step B） | 初始 root node, state=exploring |
| Roster 確認（Explore Step 1 結束） | 寫 root.roster |
| Plan 批准（/brief-approve） | root.state=executing；建 children sub-brief 節點 |
| Worktree 建立 | sub-brief.worktree |
| Stage 進入 running | sub-brief.pipeline_stages[i].state=running |
| Verdict 收到 | sub-brief.pipeline_stages[i].verdict / rounds |
| Stage 完成 | state=done |
| Sub-brief 完成 | sub-brief.state=done, completed_at, artifact=./final.md |
| Sub-brief needs_decomposition 同意 | 新增 children（注意：違反 2 層限制的拒絕） |
| L0 holistic review | root.holistic_review |
| Brief 完成 | root.state=done, completed_at |
| `/brief-amend` 開始 | sub-brief.amendments[] append 新項，state=amending |
| Amendment producer 回 verdict（終態） | sub-brief.amendments[i].state=done\|done_with_notes\|rejected\|cancelled, completed_at |

每次寫入後同步更新 `last_updated`。

---

## 2.5 Amendment 條目 schema

每個 sub-brief 節點下的 `amendments[]` 元素：

```yaml
amendments:
  - id: a1                            # 單字母前綴 a + 序號（a1, a2, a3...）
    state: done                       # amending | done | done_with_notes | rejected | cancelled
    summary: "rename fetchUser → getUserById"
    allowed_paths_delta:              # 本次 amendment 擴張的路徑（可空）
      - src/utils/y.ts
      - README.md
    created_at: 2026-05-06T13:00:00
    completed_at: 2026-05-06T13:08:00 # null 直到終態
```

**State enum**：

| State | 描述 |
|---|---|
| `amending` | 訪談中 / 確認中 / producer 跑中 |
| `done` | producer pass、final.md 已 append amendment 章節 |
| `done_with_notes` | producer partial、使用者明示接受 |
| `rejected` | producer 二次 ambiguity / needs_decomposition / needs_dependency / tool_error |
| `cancelled` | 使用者於確認步驟選 cancel |

**id 命名**：
- 單字母 `a` 前綴 + 序號（與 sub-brief 字母 id 區隔）
- 序號從 1 起、append-only（rejected / cancelled 仍佔號）
- 同 sub-brief 累積非 cancelled amendments 不設次數上限；第 3 次起軟提醒不阻擋（見 amendment.md §1.3）

**鐵律**：
- amendment 不算 sub-brief 節點，不進 `nodes` map（只掛在所屬 sub-brief 節點的 `amendments[]`）
- amendment 不影響 L0 holistic review 結果（已 pass 的不重跑）
- amendment 不參與學習迴圈（不寫 sessions / lessons / patterns）

完整流程規範見 `core/amendment.md`。

---

## 3. 節點狀態機

### 3.1 狀態列舉

| 狀態 | 描述 | 可進入的下一狀態 |
|---|---|---|
| `pending` | 已建立尚未啟動（L1 初始） | executing, cancelled |
| `exploring` | Explore 階段（Step 1-5，僅 L0） | awaiting_approval, cancelled |
| `awaiting_approval` | 等使用者 /brief-approve（Step 6，僅 L0） | executing, exploring（若使用者要求修改）, cancelled |
| `executing` | Execute 階段進行中 | reviewing, paused, failed, cancelled, done |
| `reviewing` | L0 holistic review 進行中（僅 L0） | done, exploring（fail 回 Explore）, failed |
| `paused` | L1 暫停（parent 正在 re-Explore） | executing（重新跑 stage）, cancelled |
| `done` | 完成（L1 = stage 全 pass；L0 = holistic review pass） | （終態；L1 done 後 amendment 流程不改 state，僅在節點上 append `amendments[]`） |
| `failed` | 失敗（4 輪上限觸發、使用者拒絕、不可恢復錯誤） | cancelled（使用者放棄）, executing（/framework-recover 接續） |
| `cancelled` | 使用者取消 | （終態） |

**Stage state enum**（`pipeline_stages[i].state`，僅 L1 用）：

| Stage state | 描述 |
|---|---|
| `pending` | 尚未啟動 |
| `running` | producer 或 reviewer 正在跑 |
| `done` | 此 stage 最終 reviewer pass |
| `failed` | 此 stage 累積 4 輪 reviewer fail（依 review-loop） |
| `paused` | 此 stage 因 parent re-Explore 暫停 |

### 3.2 L0 vs L1 狀態差異

| 狀態 | L0 適用 | L1 適用 |
|---|---|---|
| pending | ✗（L0 一建立就進 exploring） | ✓（L1 初始狀態） |
| exploring | ✓ | ✗（L1 無獨立 Explore；plan 從 L0 plan 推導） |
| awaiting_approval | ✓ | ✗（L1 不需獨立批准） |
| executing | ✓ | ✓ |
| reviewing | ✓ | ✗（L1 在 stage 內 review，不需獨立 reviewing 狀態） |
| paused | ✗（L0 不暫停） | ✓（parent re-Explore 時） |
| done | ✓ | ✓ |
| failed | ✓ | ✓ |
| cancelled | ✓ | ✓（L1 可被取消但通常透過取消整個 L0） |

### 3.3 狀態轉換規則

```
[L0]
exploring → awaiting_approval：plan 寫完且 planning-reviewer pass
awaiting_approval → executing：使用者 /brief-approve
awaiting_approval → exploring：使用者要求修改 plan（回 Step 4-5）
executing → reviewing：所有 children sub-brief state in {done, failed}（即使單 sub-brief 也走此轉換）
reviewing → done：holistic_review = pass
reviewing → exploring：holistic_review = fail（回 Explore Step 3 補訪談 + Step 4 改 plan）
任何狀態 → cancelled：使用者 /brief-cancel
任何狀態 → failed：4 輪上限或不可恢復錯誤

**單 sub-brief / planning_only 場景**：仍必經 reviewing 狀態。Holistic review 內容可極簡（只需確認 sub-brief artifact 滿足 plan 驗收條件），但**不可跳過**——`holistic_review` 欄位必填 pass / fail，state 必經 reviewing。

[L1]
（建立時）→ pending：sub-brief 節點剛建立，尚未啟動
pending → executing：depends_on 全 done 後 main spawn 第一個 stage role
executing → paused：parent 進入 re-Explore 時暫停
paused → executing：parent re-Explore 完成、新 plan 批准後恢復（見 review-loop.md §2.2）
executing → done：所有 pipeline_stages 完成且最終 stage verdict=pass
executing → failed：某 stage 累積 4 輪 reviewer fail（見 review-loop.md §3.2）或 main 經使用者同意放棄
failed → executing：使用者執行 /framework-recover 接續
任何狀態 → cancelled：父節點被取消 OR 使用者明示取消
```

---

## 4. Main 的樹遍歷邏輯

### 4.1 主迴圈（Execute 階段）

```
while root.state == executing:
  available_subs = [s for s in root.children if
    s.state == pending and
    all(_tree.nodes[d].state == done for d in s.depends_on)
  ]

  if not available_subs:
    if all root.children in terminal states:
      → 進 L0 holistic review
      break
    else:
      # 有 sub-brief 在跑但 main 不需動作
      # 例：等使用者批准 needs_dependency
      pause / 等使用者觸發
      continue

  # 並行 spawn
  for sub in available_subs:
    current_stage = next pending stage in sub.pipeline_stages
    spawn role for current_stage  # 同訊息批量

  # 等回 verdicts
  for verdict in collected_verdicts:
    process_verdict(verdict)
    update _tree.yaml
    update _manifest.md
```

### 4.2 Sub-brief 切分（needs_decomposition）

```
on receive verdict.verdict == needs_decomposition:
  if verdict.actor.spec_id is L1:
    # 已是 L1，不能再切（2 層限制）
    → reject decomposition
    → spawn 同 role 第 2 輪，附訊息「請在 L1 範圍內完成」
    → 若連 2 次拒絕仍要切 → 升級使用者：「此 sub-brief 太大，建議 cancel 並用 /brief-new 開多個獨立 brief」
    return

  # spec_id is L0：可切 sub-brief
  rationale = verdict.decomposition_proposal.rationale
  proposed = verdict.decomposition_proposal.sub_briefs

  # main 判斷是否同意（不照單全收）
  if proposed 看起來合理（≥2 sub_briefs，scope 不重疊，rationale 充分）:
    → 切：建立 sub-brief 節點
    → roster 從 root 繼承
    → 寫 _tree.yaml
  else:
    → reject：spawn 同 role 第 2 輪，附「scope 重疊」/「rationale 不足」等具體理由
```

### 4.3 L0 holistic review

L0 holistic review 由 main 自做（不 spawn 專門 role）：

```
1. 收集所有 children sub-brief 的 final.md
2. Read 所有 final.md
3. 檢查項目：
   - 跨 sub-brief 假設一致？（例：sub-A 用 cohort=註冊月份，sub-B 用 cohort=首儲月份 → 不一致）
   - 各 sub-brief 結論彼此衝突？
   - 整體有達到 plan.md 的驗收條件？
   - 缺漏的 sub-brief？（plan 列了但 sub-brief.state=failed/cancelled）
4. 產出 reviews/L0-review.json（依 typed-interfaces.md schema，actor.type=reviewer 但 reviewer name=main）
5. pass → root.state=done；fail → root.state=exploring（回 Explore Step 3）
```

L0-review.json 格式範例：

```json
{
  "verdict": "pass",
  "actor": {
    "role": "main-holistic-review",
    "type": "reviewer",
    "spec_id": "2026-05-06-slot-revenue-q2",
    "round": 1,
    "stage": "L0-holistic",
    "adversarial": false
  },
  "summary": "兩 sub-brief 結論彼此一致、達成 plan 驗收條件",
  "checks": [
    {"name": "cohort_consistency", "result": "pass", "evidence": "both sub-briefs use 首儲月份"},
    {"name": "acceptance_criteria", "result": "pass", "evidence": "..."}
  ]
}
```

---

## 4.4 `_manifest.md` Schema（人類可讀進度檔）

每 brief 一份：`.framework/briefs/{root_id}/_manifest.md`。Sub-brief 也各自一份：`.framework/briefs/{root_id}/sub-briefs/{sub_id}/_manifest.md`。

格式：

```markdown
# Manifest: {brief_id}

- created_at: 2026-05-06T10:00:00
- recipe: data-analytics
- pipeline: full_advisory

## Files Produced

| Time | Path | Producer | Verdict |
|---|---|---|---|
| 10:30 | sub-briefs/a/stages/research/researcher.output.md | researcher | pass |
| 11:00 | sub-briefs/a/stages/research/reviews/source-quality-reviewer.verdict.json | source-quality-reviewer | pass |
| 11:15 | sub-briefs/a/final.md | main-merge | - |

## Review History

| Time | Sub | Stage | Round | Reviewer | Verdict | Summary |
|---|---|---|---|---|---|---|
| 11:00 | .a | research | 1 | source-quality-reviewer | pass | 來源全可追溯 |
| 11:43 | .b | writing | 1 | editor | fail | cohort 描述不一致 |
| 11:55 | .b | writing | 2 | editor | pass | 修正後通過 |

## Phase Transitions

- 10:00 brief created (exploring)
- 10:08 explore → awaiting_approval
- 10:12 awaiting_approval → executing
- 12:10 executing → reviewing
- 12:30 reviewing → done
```

**寫入時機**：
- Brief 建立 → main 寫初始 manifest
- 任何 verdict 收到 → append 一行
- 任何 phase 轉換 → append phase 行
- Sub-brief 完成 → append final.md 行

**寫者**：僅 main。

**用途**：
- `/brief-status` 讀此檔顯示進度
- 中斷後 `/framework-recover` 讀此檔恢復狀態

## 5. Sub-brief id 命名

### 5.1 格式

`{root_id}.{a|b|c|...}`，單字母小寫。

範例：
- Root: `2026-05-06-slot-revenue-q2`
- Sub: `2026-05-06-slot-revenue-q2.a`、`2026-05-06-slot-revenue-q2.b`

### 5.2 字母分配

- 切分順序：a, b, c, ...
- 已用過的字母不重用（即使 sub-brief 取消）
- 已用字母記錄在 root node 的 `consumed_child_ids` 欄位（陣列，append-only）
- Main 切新 sub-brief 時：選 `consumed_child_ids` 之外的最小字母
- 26 個字母用完？實務上 root brief 不該有 ≥27 個 sub-brief（早就要拆 root）。若真撞到 → 升級使用者建議拆 root

`consumed_child_ids` 欄位範例：

```yaml
nodes:
  2026-05-06-slot-revenue-q2:
    state: executing
    consumed_child_ids: [a, b, c]    # c 是已 cancelled 的 sub-brief，仍記錄
    children: [2026-05-06-slot-revenue-q2.a, 2026-05-06-slot-revenue-q2.b]   # 不含已 cancel 的 .c
```

---

## 6. 鐵律

### 6.1 受限 2 層
任何試圖在 L1 切 sub-brief 的 needs_decomposition verdict 都拒絕。`children` 陣列在 L1 永遠空。

### 6.2 Sub-brief 之間不互寫
Sub-A 不能寫 sub-B 的 plan / artifact。Cross-sub-brief 通訊靠 main 在 L0 holistic 階段彙整。

### 6.3 Sub-brief 邊界批准後不變
plan.md 批准後，sub-brief 的 allowed_paths / depends_on 不可悄悄改。要改 → 回 Explore → 改 plan → 重批准。

**唯一例外**：L0 holistic review pass 後的 amendment 流程（`/brief-amend`）允許**使用者明示同意**下擴張 `allowed_paths`，擴張部分寫入 `amendments[].allowed_paths_delta`、不改 plan.md。詳見 `core/amendment.md` §3 Step 2-3。

### 6.4 Children 改變必更新 _tree.yaml
每次 child 加入 / 狀態變化 → main 立即更新 _tree.yaml（不延後批量寫，避免狀態不一致）。

### 6.5 _tree.yaml 衝突處置
若 main 偵測 _tree.yaml 與實際 sub-brief 目錄不一致（例：使用者手動改了）：
- 顯示衝突明細
- 提示使用者：手動修 _tree.yaml 或執行 `/framework-recover`
- 不自動覆寫（信任使用者意圖）

---

## 7. 範例：完整流程的 _tree.yaml 演化

### 7.1 Brief 啟動時

```yaml
root: 2026-05-06-slot-revenue-q2
created_at: 2026-05-06T10:00:00
last_updated: 2026-05-06T10:00:00
nodes:
  2026-05-06-slot-revenue-q2:
    state: exploring
    parent: null
    children: []
    roster: []
    plan: null
    pipeline: .framework/pipeline.yaml
    started_at: 2026-05-06T10:00:00
```

### 7.2 Plan 批准後

```yaml
nodes:
  2026-05-06-slot-revenue-q2:
    state: executing
    children: [2026-05-06-slot-revenue-q2.a, 2026-05-06-slot-revenue-q2.b]
    roster: [data-analyst, analysis-reviewer, writer]
    plan: ./plan.md
    pipeline: .framework/pipeline.yaml
  2026-05-06-slot-revenue-q2.a:
    state: executing
    parent: 2026-05-06-slot-revenue-q2
    children: []
    roster: [data-analyst, analysis-reviewer]
    plan: ./sub-briefs/a/plan.md
    pipeline_stages: [{name: analysis, state: pending, rounds: {producer: 0, reviewer: 0, adversarial: 0}}]
    decomposition_origin: explore_step_4
  2026-05-06-slot-revenue-q2.b:
    state: executing
    parent: 2026-05-06-slot-revenue-q2
    children: []
    roster: [writer, editor]
    plan: ./sub-briefs/b/plan.md
    pipeline_stages: [{name: writing, state: pending, rounds: {producer: 0, reviewer: 0, adversarial: 0}}]
    decomposition_origin: explore_step_4
```

### 7.3 Sub-A 完成、Sub-B 進行中

```yaml
nodes:
  2026-05-06-slot-revenue-q2.a:
    state: done
    artifact: ./sub-briefs/a/final.md
    pipeline_stages:
      - name: analysis
        state: done
        rounds: {producer: 1, reviewer: 1, adversarial: 0}
        verdict: pass
    completed_at: 2026-05-06T11:15:00
  2026-05-06-slot-revenue-q2.b:
    state: executing
    pipeline_stages:
      - name: writing
        state: running
        rounds: {producer: 1, reviewer: 0, adversarial: 0}
```

### 7.4 全完成且 L0 review pass

```yaml
nodes:
  2026-05-06-slot-revenue-q2:
    state: done
    holistic_review: pass
    completed_at: 2026-05-06T12:00:00
    rounds:
      explore: 1
      l0_review: 1
```

---

## 8. 給接手 agent 的提醒

- **`_tree.yaml` 是 main 的寫入特權**：subagent 永遠無權寫，path boundary 必須排除
- **狀態轉換必經狀態機**：不可從 exploring 直接跳 done（必經 awaiting_approval / executing / reviewing）
- **L0 holistic review 是 main 自做**，不要為此設計獨立 reviewer role（複雜化無收益）
- **Sub-brief id 用單字母**：a/b/c 不要用數字（避免與 round number 混淆）
- **Decomposition 在 L1 觸發是錯誤**：永遠拒絕；2 次拒絕仍要切 → 升級使用者
- **2 層限制不要試圖突破**：未來若要升 3 層必須重設計 token 管理
- **崩潰恢復**：_tree.yaml 是恢復狀態的 source of truth；崩潰後重啟 main，從 _tree.yaml + _manifest.md 重建上下文

---

## 9. 相關文件

- `core/control-plane.md`：main 何時建 / 改 _tree.yaml
- `core/typed-interfaces.md`：verdict 中的 `decomposition_proposal` 欄位
- `core/review-loop.md`：fail verdict 的回 Explore 邏輯
- `core/batch-lock.md`：_active.yaml 與 _tree.yaml 的關係
- `core/escalation-rules.md`：何時升級使用者拆 root brief
- `core/amendment.md`：amendments[] 欄位的完整流程規範
