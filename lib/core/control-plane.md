# Control Plane — Main Session 行為規範

> 本文件規範 main session 在 framework 啟用模式下的行為。Main 是唯一的編排者（control plane），所有 subagent 都是 leaf（不能再 spawn）。
>
> 對應 OMC（arXiv:2604.22446）論文中**沒有專門 orchestrator agent**，編排責任由 main session 承擔——這是 v3 已驗證可行、且符合 Claude Code 技術限制的選擇。

---

## 1. Main session 的職責

### 1.1 是
- **編排者**：決定何時 spawn 誰、按什麼順序、傳什麼參數
- **狀態管理者**：寫 `_tree.yaml`、`_active.yaml`、`_manifest.md`
- **訪談者**：grill-me 風格主持與使用者的釐清對話（Explore Step 3）
- **Roster 決策者**：選擇本 brief 用哪些 role
- **情報蒐集者**：讀 codex / memory / repo，產出 intel-pack.md
- **批准 gate**：呈現 plan 給使用者批准
- **學習迴圈主持者**：brief 結束時詢問品質、彙整 suggest_*、寫 memory

### 1.2 不是
- **不寫 artifact**：不自己寫 code、寫 plan、寫 research notes（這些是 subagent 的事）
- **不審核**：不取代 reviewer 做機械檢查
- **不繞過 user approval 直寫 .framework/memory/skills/codex**：流程必為「subagent suggest → 使用者批准 → main 寫」
  - 「不直寫」= 不在 mid-execution 偷偷寫、不跳過 user approval gate
  - **不等於**「main 永遠不能寫 memory」——learning loop 階段使用者批准後 main **直接寫**，這是設計、不是繞過
  - **永遠不需要為了寫 memory 開新 brief**。Brief 結束時 learning loop 內處理；錯過或漏跑時用 `/framework-learn` 補（lightweight，無 brief overhead）
- **不繞過 verdict**：reviewer 回 fail 時不能說「我覺得可以」放行

### 1.3 例外：Main 可直寫的東西
- `_tree.yaml`、`_manifest.md`、`_active.yaml`（狀態檔，main 獨佔）
- `.framework/briefs/{id}/{intel-pack.md, clarifications.md}`（Explore 階段產出）
- `.framework/briefs/{id}/_suggestions.json`（彙整 verdict 的 suggest_* 欄位）
- `.framework/briefs/{id}/_escalations/{timestamp}-{reason}.md`（升級事件即時紀錄；見 escalation-rules.md §1）
- `.framework/memory/sessions/{brief_id}.md`（brief 完成自動寫，不需批准）
- `.framework/memory/lessons/escalations/{root_id}-{sub_id}-{stage}.md`（learning loop 失敗版迴圈時 mirror 自 brief 內 _escalations/）
- 使用者在學習迴圈批准後，main 替使用者寫 .framework/memory/lessons、patterns、codex、skills

---

## 2. Main 的工具集

| Tool | 是否可用 | 用途 |
|---|---|---|
| Read | ✓ | 讀任何檔案（含 codex / memory / repo） |
| Write | ✓ | 限第 1.3 節的允許檔 |
| Edit | ✓ | 限第 1.3 節的允許檔 |
| Glob / Grep | ✓ | 情報蒐集、找 lessons / patterns 相關條目 |
| Bash | 白名單 | 見 `core/trust-modes.md` |
| Task | ✓ | spawn subagent（main 獨有） |
| WebFetch / WebSearch | 可選 | 由 recipe / init 決定 |

**注意**：Main 的 Write 權雖然技術上可寫任何路徑，但**鐵律是只寫第 1.3 節列舉的檔案**。違反鐵律是行為錯誤，不是技術錯誤。

---

## 2.1 檔案產出鐵律：cp > Edit > Write

**框架運作中所有檔案落地，必依此優先順序選工具**（不僅限 init）：

| 工具 | Token 成本 | 適用情境 |
|---|---|---|
| `cp` / `cp -r`（Bash） | 極低（一條 Bash 指令） | 從 `.framework/` 已有檔複製到 `.claude/` / 從 template 複製到目標位置 |
| `Edit`（行級替換） | 低（只送 diff） | 改少數行（frontmatter 覆寫、template `{{placeholder}}` 替換、yaml 欄位調整） |
| `Write` | 高（全文進 context、再寫出） | 不可避免：純新內容（codex 草稿、`_active.yaml`、`_tree.yaml`、verdict suggestions 彙整、新建 brief.md） |

### 鐵律

1. **任何「`.framework/` 內已有的檔案」需要進 `.claude/`**：必先 `cp`，再 `Edit` 客製
2. **任何 template 檔（`.framework/lib/init/*-template.md`）填 placeholders**：必先 `cp` 至目標位置，再 `Edit` 替換每個 `{{placeholder}}`
3. **使用者既有檔被覆蓋前**：先 `cp` 備份至 `{path}.before-{operation}` 再操作
4. **Edit 使用要求**：必為 unique match（frontmatter 行 / placeholder 字串通常天然 unique）；非 unique 時可加上下文行
5. **永不 Read 一個 `.framework/` 內檔再 Write 同內容到 `.claude/`**：這是雙倍 token 浪費

### 觸發場景速查

| 場景 | 工具選擇 |
|---|---|
| Init: 複製 `.framework/lib/roles/{r}.md` → `.claude/agents/{r}.md`（無客製） | 純 `cp` |
| Init: 複製同上 + tier 客製 | `cp` + `Edit "tier: mid" → "tier: cheap"` |
| Init: 複製 `.framework/lib/skills/{s}/` → `.claude/skills/{s}/` | `cp -r` |
| Init: 複製 `.framework/lib/commands/*` → `.claude/commands/` | `cp -r` |
| Init: CLAUDE.md template → 專案 root | `cp` + N 個 `Edit` 替換 placeholders |
| Init: .framework/pipeline.yaml template → 專案 root | `cp` + `Edit` 替換 |
| Init: 寫 `.framework/codex/{role}.md`（從 Step 4 訪談） | `Write`（純新內容） |
| Init: 寫 `.framework/.initialized` | `Write`（純新內容、~30 行 yaml） |
| Init: 寫 `.framework/memory/{MEMORY,architecture,preferences}.md` | `Write`（純新內容） |
| Brief: 建 `.framework/briefs/{id}/brief.md`（從使用者描述） | `Write`（純新內容） |
| Brief: 建 sub-brief plan.md（從 L0 plan 推導） | `Write`（推導內容） |
| Brief: 寫 verdict.json | `Write` 由 subagent 做（main 收後不重寫） |
| 學習迴圈：寫 `.framework/memory/lessons/{cat}.md`（append 一條） | `Edit`（append 至檔尾） |
| 學習迴圈：寫 `.framework/memory/sessions/{id}.md`（新檔） | `Write`（純新內容） |
| `/framework-role-add`：基於 framework template | `cp .framework/lib/roles/{template}.md` + `Edit` 客製 |
| `/framework-role-edit`：改既有 role | `Edit`（直接改 `.claude/agents/`） |
| `/framework-recover`：歸檔還原 | `mv`（從 `_archive/` 移回） |

### 為什麼這條鐵律重要

- Init 一次落地 ~25 檔（4 roles + 多 skills + commands + templates + memory + briefs 結構）。Read + Write 模式 token 消耗 = ~30k；cp + Edit 模式 = ~500-2000。**60 倍差距**。
- 長期使用中（每 brief 多次 verdict 寫入、學習迴圈 append、role 增改），累積差距更大
- 浪費 token 不是「貴一點」——超過 main session context 上限會強制壓縮，丟失工作記憶

---

## 3. 批次流程骨架（每個 brief）

```
[啟動：使用者開新 brief]
  ↓
Step A. 鎖定（寫 .framework/briefs/_active.yaml）
  - 偵測既有 _active.yaml → 拒新 brief，提示既有 active
  - 無 → 建立 _active.yaml { brief_id, started_at, phase: exploring }
  ↓
Step B. 建 brief 目錄
  - .framework/briefs/{brief_id}/{brief.md, _tree.yaml(初始), _manifest.md(初始)}
  - _tree.yaml 初始：root node, state=exploring, no children
  ↓
Step C. Explore 階段（見 Explore Section 4）
  ↓
Step D. 等使用者批准（/brief-approve）
  ↓
Step E. Execute 階段（見 Execute Section 5）
  ↓
Step F. L0 holistic review（main 自做，**必跑、即使單 sub-brief / 即使 pipeline 簡單**）
  - 讀所有 sub-brief 的 final.md（單 sub-brief 場景讀該 sub-brief artifact）
  - 檢查驗收條件、跨 sub-brief 一致性（若多）
  - **僅靜態驗證**：holistic review 是 main 讀檔 + 跨檔一致性判斷，**不跑實機**。
    plan 標 [runtime] 的驗收項（config / dispatch / 跨 service wiring 等整合行為）
    框架流程**無法**確認——unit test 全綠 ≠ wire 已驗證（典型：config key 漏接 registration map，unit 過但 runtime panic）。
  - 對所有 [runtime] 項，在完成摘要明列「需使用者端 localTest 驗證」清單，**不標成「已完成」**
  - 寫 _tree.yaml.holistic_review = pass | fail
  - pass → Step F'（可選 amendment 期）；fail → 回 Explore（review-loop.md 第 3 輪以上規則）
  ↓
Step F'. Amendment 期（**可選、由使用者觸發**）
  - holistic review pass 後，使用者可開 /brief-amend 對 sub-brief 做小範圍修訂
  - main 處於 idle，等使用者觸發指令
  - 使用者直接進 Step G（無觸發） / 一次或多次 amendment 後再進 Step G
  - 完整規範見 core/amendment.md
  ↓
Step G. 學習迴圈（見 learning-loop.md，**必跑、即使 verdict 全 pass**）
  - Step 1 必寫 sessions（即使無 suggest_* / 無評分）
  - Step 2-5 可視情況跳（learning-loop §3.1 規則）
  ↓
Step H. 歸檔
  - .framework/briefs/{brief_id}/ 移至 .framework/briefs/_archive/{year-month}/{brief_id}/
    （**注意 year-month 子層**，例 .framework/briefs/_archive/2026-05/2026-05-06-x/）
  - .framework/memory/sessions/{brief_id}.md 已在 Step G 寫好
  ↓
Step I. 解鎖
  - 刪 _active.yaml
  - 回覆使用者完成
```

**brief 生命週期鐵律**：
- Step F、G、H、I **皆不可省**。即使 brief 流程順利、verdict 全 pass、使用者都點 yes，仍必經此四步。
- 跳過 Step G Step 1（寫 sessions）→ 下次 brief 的 Explore Step 2 找不到歷史，學習迴圈失效
- 跳過 Step H 的 year-month 子層 → 歸檔目錄將被未分類 brief 塞滿，後續難找
- 中斷恢復：使用者 Ctrl-C 後 `_active.yaml` 還在 → 重新啟動 main → 偵測到 active brief → 提示使用者執行 `/framework-recover`。詳見 `core/batch-lock.md`。

---

## 4. Explore 階段（main 執行細節）

### Step 0. 規模 triage（micro-brief 快篩，在 Step 1 之前）

開 brief 後、決 roster 前，main 先快篩改動規模，選對 pipeline——**避免小改動被重流程過度工程化**：

```
若 brief 明顯是 micro-change（任一成立）：
  - 單檔、預估 ≤ 5 行
  - 純參數 / 設定 / 版本號 / 單行邏輯調整
  - 使用者描述本身就是「把 X 改成 Y」這種點狀修改
→ 建議走 bug_fix pipeline（跳過 planning stage：不 spawn planner + planning-reviewer + 對抗式）
  顯示：「這像 micro-change（單檔小改），建議走 bug_fix 跳過正式規劃，省下 planner + 雙審成本。
         要改走 new_feature 嗎？(用 bug_fix / 改 new_feature)」
否則 → 照常 new_feature（或 triage_hints / default）
```

**為什麼**：實測 2 行改動走 `new_feature`，planning 階段對抗式 reviewer 仍被要求找 gap，硬擠出 9 個（6 個是 over-engineering），撞 adversarial 上限後升級——interview + planner + 雙審 + 升級的成本遠大於 2 行改動本身。第二道防線見 `review-loop.md` §3.4（已進 new_feature 才發現小改時，size gate 自動跳過 adversarial）。

### Step 1. Roster 決策

```
1. Read brief.md
2. Read recipes/*.yaml（找匹配本 brief 類型的 recipe）
3. Read .claude/agents/*.md（列當前可用 role 與其 type / produces / reviews）
4. 產出候選 roster：
   - 從 recipe 預設 roster 起步
   - 依 brief 內容增減
5. 顯示給使用者：
   "建議 roster: data-analyst, analysis-reviewer, writer
    理由：本 brief 涉及數據分析 + 報告產出
    要修改嗎？(y/edit/keep)"
6. 使用者確認 → 寫進 _tree.yaml.root.roster
```

### Step 2. 情報蒐集（並行讀）

```
1. 候選 role 的 Codex（讀全部）
   for role in roster:
     if exists .framework/codex/{role}.md → Read 全文
2. .framework/memory/lessons/<相關分類>（grep + recency）
   - 用 brief 標題、關鍵字 grep lesson body
   - 取近 90 天 + reference_count > 0 的優先
3. .framework/memory/patterns/<相關分類>（同上邏輯）
4. .framework/memory/sessions/（找近 30 天同主題）
5. .framework/memory/architecture.md + preferences.md（全讀）
6. 相關 repo 檔（Glob/Grep brief 提到的關鍵字 / 檔名）
7. 產出 intel-pack.md：
   - 摘要（main 自寫，總結上述蒐集到的東西）
   - 不確定點清單（main 自寫，標出哪些事 brief 沒說清楚）
   - 已知陷阱（從 lessons 摘）
   - 跨 repo 參考（若 knowledge_base.recall=true 且使用者曾下 /framework-recall：併入 main 從外部 KB 撈回的其他 repo lessons/patterns/ADR；見 commands/framework-recall.md）
8. 寫 .framework/briefs/{brief_id}/intel-pack.md
9. 快取 mtime，下次 Explore 比對是否需重 build
```

### Step 3. 訪談（grill-me）

```
1. 從 intel-pack.md 不確定點清單生成題目（依 core/clarification.md）
2. 單題提問：
   "Q1: 此 brief 的 cohort 切法應該按註冊月份還是首次儲值月份？
    我推薦：首次儲值月份（更貼合 revenue 分析）
    理由：...
    Trade-off：註冊月份對 onboarding 漏斗友善，但 revenue 分析會誤差
    Options: (a) 註冊月份 (b) 首次儲值月份 (c) 你判斷"
3. 收使用者答 → 若使用者說「你判斷」→ 採推薦並註明
4. 重複直到沒不確定點 OR 達 cap 20 題
5. 寫 .framework/briefs/{brief_id}/clarifications.md（一問一答 + 我的解讀）
```

### Step 4. Plan 草稿

```
1. 若 roster 內有 planner role：
   spawn planner，傳：brief.md + intel-pack.md + clarifications.md
   等回 verdict
2. 若 roster 無 planner：
   main 自寫 plan-draft.md（限簡單 brief，例 general-assistant 場景）
3. 寫至 .framework/briefs/{brief_id}/plan-draft.md
```

### Step 5. Plan 審核

```
1. 若 roster 內有 planning-reviewer role：
   spawn planning-reviewer，傳：plan-draft.md + 相關 lessons + architecture.md
   等回 verdict
2. verdict pass → mv plan-draft.md → plan.md
3. verdict fail → 把 reviewer 意見回給 planner（第 2 輪）
4. 第 3 輪起若仍 fail → 視為 plan 本身有問題 → 回 Explore Step 3 補訪談
5. 若 roster 無 planning-reviewer → 跳過此 step（plan-draft.md → plan.md）
```

### Step 6. 使用者批准

```
1. 顯示給使用者：
   - plan.md 全文
   - roster
   - sub-briefs 清單（從 plan.sub_briefs）
   - 風險清單（從 plan.known_risks）
2. 提示：「執行 /brief-approve 批准；或回覆修改意見」
3. 使用者修改 → main 把意見回給 planner（同 Step 5 第 2 輪邏輯）
4. /brief-approve → 寫 _tree.yaml.root.state=executing → 進 Execute
```

---

## 5. Execute 階段（main 執行細節）

### 5.1 Sub-brief 切分（若 plan 有 sub_briefs）

```
1. 對 plan.sub_briefs 每項建子節點：
   for sub in plan.sub_briefs:
     - 建 .framework/briefs/{root}/sub-briefs/{sub_id}/{sub-brief.md, plan.md}
     - 寫進 _tree.yaml
2. 若 plan 無 sub_briefs：
   - 視整個 brief 為單 sub-brief（root 同時是 leaf）
3. Worktree 建立（dev recipe）：
   - for sub in sub_briefs:
       git worktree add .framework/worktrees/brief--{sub_id} -b brief/{sub_id}
```

### 5.2 並行排程

```
loop until all sub-briefs in terminal states (done | failed | cancelled):
  available = sub_briefs where:
    - state == pending
    - 所有 depends_on 已 done
  for sub in available:
    sub.state = executing
  在同訊息中 spawn available 各 sub-brief 的當前 stage role
  收回各 verdict
  for each verdict:
    process_verdict(sub_id, stage, verdict)  # 見 5.3
  若 sub-brief 內所有 stage 完成 → sub.state = done
```

### 5.3 Verdict 處理（每個 sub-brief 內）

```
process_verdict(sub_id, stage, verdict):
  switch verdict.verdict:
    case pass:
      若是 producer 的 pass → spawn reviewer（checklist mode，無 mode flag）
      若是 reviewer 的 pass:
        若 verdict.actor.adversarial == true:
          → adversarial pass，stage 真正通過 → 進下一 stage
        若 stage.second_review == true（pipeline.yaml）且 adversarial 還沒跑:
          → spawn 同 reviewer round 1 with `mode: adversarial`
          → 等其 verdict（若 adversarial fail 走下方 fail 路徑、視同 producer 重做觸發）
        否則:
          → 進下一 stage（按 .framework/pipeline.yaml depends_on）
      若已是最後 stage → 寫 sub-brief/final.md（main 摘要）→ state=done
    case fail:
      入 review-loop.md 邏輯（1-2 輪同 role / 3+ 回 Explore L0）
      注意：adversarial reviewer 的 fail 與 checklist reviewer 的 fail 同等對待——都觸發 producer 重做
    case ambiguity:
      若是 sub-brief 內 → 不訪談使用者，main 自行從 intel-pack 補 OR 升級 L0 補訪談
    case needs_decomposition:
      入 e2r-tree.md：判斷是否同意，同意則切子節點
    case needs_dependency:
      升級使用者；暫停此 sub-brief
    case tool_error:
      升級使用者；暫停此 sub-brief
    case partial:
      顯示給使用者，問：接受 / 要求補完 / 取消
```

**Adversarial pass 的 spawn prompt 約定**（second_review=true 時）：

當 main 對某 stage spawn 第二輪 reviewer：

```
Spawn-time 注入：
  - 你是 {reviewer_role}
  - mode: adversarial         ← 關鍵旗標，role md §5.y 觸發此模式
  - spec_id, stage, round 同前
  - 你的 input：
    - brief, plan, 上游 artifact（不變）
    - **不讀前一輪 verdict**（避免被前一輪框架影響）
  - 提醒：依 role md §5.y 跑（不跑 §5 checklist、只跑對抗式視角）
```

Round 計數（與 review-loop.md §3.1 §3.2 一致）：
- `pipeline_stages[i].rounds.reviewer` = checklist reviewer cumulative 跑次（adversarial 不計）
- `pipeline_stages[i].rounds.adversarial` = adversarial reviewer cumulative 跑次（**跨 cycle 計**）
- `pipeline_stages[i].rounds.producer` = producer cumulative 跑次（含 adversarial fail 觸發的重做）

**Cycle 語意**：
- 「Cycle」 = 一輪「producer 出 → checklist reviewer 過 → adversarial reviewer 過 / 不過」
- 每 cycle 內，**checklist 僅跑一次 / adversarial 最多跑一次**
- 跨 cycle cumulative：`rounds.adversarial >= 2` 觸發 escalation `adversarial-deadlock`（review-loop §3.2）

**4 輪上限只算 `rounds.reviewer`（cumulative）**；adversarial 自有 cap=2；producer cap=5 涵蓋 adversarial fail 觸發的重做。

### 5.4 Stage 內並行

若同 stage 同時有多 producer（.framework/pipeline.yaml 設定）：

```
spawn 多 producer 同訊息（avoid 序列化）
等所有 producer 回 verdict
若全 pass → spawn 對應 reviewer（也同訊息並行）
```

---

## 5.5 Amendment 流程（Step F' 期間）

Amendment 是 L0 holistic review pass 後、Step G 學習迴圈前的可選輕量修訂入口。設計目的：使用者目視 review sub-brief 產出時若有小範圍規格 / 風格建議，不必打回 Explore 重 plan、也不必另開新 brief。適用所有 recipe（dev-team / writing-team / finance-advisory 等），不限程式碼場景。

完整規範見 `core/amendment.md`。Main 在此期間的行為摘要：

```
觸發：使用者輸入 /brief-amend <sub_id> "<一句話>"
  ↓
1. 前置檢查：sub-brief.state==done、brief 未歸檔、roster 含 producer、次數規則
2. Main 短訪談（cap 3 題、無反詰；0 題情況不寫 clarifications.md）
3. 寫 amendment.md + 使用者複誦確認
4. Spawn 主要 producer（mode: amendment, spec_id={root}.{sub}#{a_id}）→ 收 verdict
5. 處理 verdict（pass / partial / ambiguity 1 次續答 / 其他類型直接 reject）
6. Pass：append amendment 章節到 sub-brief final.md → 通知使用者 → 回 idle 等下一指令
7. Reject：寫 outcome.md → 通知使用者建議下一步 → 回 idle
```

### 鐵律（與 Execute 階段不同處）

- **無 reviewer**：amendment 層不 spawn 任何 reviewer。使用者目視審。
- **單 producer 動作**：最多 spawn 2 次（初始 + 1 次 ambiguity 續答）
- **主要 producer 推導**：取 sub-brief pipeline 最末 stage 對應 role；無則前置條件失敗、拒 amendment
- **不允許 needs_decomposition / needs_dependency**：直接 reject
- **不寫學習迴圈 memory**：lessons / patterns / sessions 仍綁原 brief Step G 觸發
- **不重跑 L0 holistic review**：amendment pass 不影響 holistic 結果
- **不改變 sub-brief.state**：amendment 全程 sub-brief.state=done，amendment 自身的 state 寫在 `amendments[]` 內
- **次數軟限**：sub-brief 累積非 cancelled amendments：1 次 → 2 次需警告同意；≥ 3 次直接拒
- **path boundary**：producer 寫超出 `plan.allowed_paths ∪ amendment.allowed_paths_delta` 視為 tool_error

### Main 在 Step F' 期間的狀態

- `_active.yaml.phase` 維持 `holistic_review_passed`（或新增 `awaiting_amendment_or_next`，落地時擇一）
- `_tree.yaml.nodes.{root}.state` 維持 `done` 直到使用者觸發進 Step G（或維持 `reviewing` 過渡，落地時擇一）

> **落地待定**：Step F' 期間 root.state 與 active.phase 的具體值由 batch-lock.md / e2r-tree.md 決定；本文件描述行為層、不鎖具體 enum 值。實作時須與 `core/batch-lock.md` 一致。

---

## 6. Spawn Subagent 的具體做法

### 6.1 Spawn 前準備

```
1. 讀目標 role 的 .claude/agents/{role}.md
2. 解析 frontmatter：
   - tier → 解析 .framework/lib/models.yaml 取 model ID
   - tools → 設 subagent 可用 tool
   - skills → Read 各 SKILL.md 全文
   - codex (auto) → Read .framework/codex/{role}.md if exists
   - memory.consume → 從各 lessons/<cat>.md 挑 3-5 條
3. 組 spawn prompt：
   [Role body 章節 1-6]
   [Spawn-time 注入：
     - 你是 {role}
     - 你正在處理 spec_id={sub_id}, stage={stage}, round={round}
     - 你的 input：
       - brief: .framework/briefs/{root_id}/brief.md
       - plan: .framework/briefs/{root_id}/sub-briefs/{sub_id}/plan.md
       - 上游 artifact: ...
     - 相關 skills（inline，依 role.skills 列表，每項讀全文塞入）：
       <SKILL.md 1 全文>
       <SKILL.md 2 全文>
     - Codex（inline，僅當 role.codex != null 且 .framework/codex/{role}.md 存在；不存在則整節省略，不寫 "(no codex)"）：
       <codex 全文>
     - 相關 memory（依 role.memory.consume）：
       Lessons（main grep + recency 挑 3-5 條）：
         <lesson 1 一行>
         <lesson 2 一行>
       Patterns（**僅 planner / 規劃類 producer 才注入**，main 挑 3 條）：
         <pattern 1 一行>
         <pattern 2 一行>
     - 你必須 emit 的 verdict JSON schema：
       見 core/typed-interfaces.md Section 3
       注意：訊息中只能有一個 ```json 區塊；JSON 之後不可有任何文字
   ]
```

### 6.2 Task call 範例

```
Task(
  subagent_type=<role.name>,
  description=<role.description>,
  prompt=<上述組好的 prompt>
)
```

### 6.3 等回後

```
1. 從 subagent 最後訊息抓 ```json``` 區塊
2. 驗證 schema（見 core/typed-interfaces.md Section 3）
3. 若 schema 違規 → retry 1 次（給 role 修正機會）→ 仍違規 → 視為 tool_error
4. 寫 verdict 到 .framework/briefs/{root}/sub-briefs/{sub}/stages/{stage}/reviews/{role}.verdict.json
5. 收 suggest_* 欄位累積進 .framework/briefs/{root}/_suggestions.json
6. 更新 _manifest.md（人類可讀進度）
7. process_verdict（見 5.3）
```

---

## 7. 並行呼叫的訊息打包規則

Main 在同訊息中可放多個 Task call：

```
本訊息包含 3 個 Task call（並行）：

Task(subagent_type=engineer, ..., spec_id=sub-A)
Task(subagent_type=engineer, ..., spec_id=sub-B)
Task(subagent_type=engineer, ..., spec_id=sub-C)
```

**規則**：
- 同訊息內的 Task call 並行執行（Claude Code 行為）
- **同 stage 內並行**：同時 spawn 該 stage 的多 producer 或多 reviewer
- **跨 sub-brief 並行**：sub-A 和 sub-B 都在 stage X 時，同訊息 spawn 兩者
- **不**跨 sub-brief 跨 stage 同訊息（會把 token 拉爆，main 也難追責）
- 同訊息 Task call 數量上限：實務 ≤ 4（避免 main context 爆）

---

## 8. 鐵律

### 8.1 不寫 artifact
Main 不能取代 producer 寫 plan / code / research notes。即使「我直接寫比較快」也不行——破壞 review 機制。

### 8.2 不繞過 reviewer fail
即使 reviewer 看起來太嚴格，main 也不能直接放行。要走 review-loop.md 規則。

### 8.3 不自做 schema 違規處理
Verdict schema 違規 → 視為 role 錯誤，不要 main 「猜意圖」自填。退回 role retry。

### 8.4 不私改 sub-brief 邊界
Sub-brief 切分後，邊界（allowed_paths / depends_on）寫進 plan.md，main 不可在 Execute 中悄悄改。要改 → 回 Explore 改 plan → 重新批准。

### 8.5 外部知識庫（KB sink）：預設解耦、可 opt-in
Framework 內部循環預設自給自足，不依賴外部知識庫（KB）。

repo 若在 `.framework/.initialized` 宣告 `knowledge_base{ path, promote, recall }`：
- `promote: true` → brief 收尾經 learning loop Step 4 `(m)` 批准的 lessons/patterns/preferences 蒸餾升流至 KB（見 learning-loop.md §8.5 / §11.5）
- `recall: true` → 使用者可 `/framework-recall <主題>` 令 main 唯讀查 KB、把跨 repo 參考折進 intel-pack.md（見 §4 Step 2 + commands/framework-recall.md）

block 不存在 = local-only（行為不變）。升流必經 Step 4 批准、不自動；KB 的手動寫入由該 KB 自己的入口處理（與框架無關）。設計細節見 `core/learning-loop.md` §8.5 / §11.5。

### 8.6 不接受 producer 直寫 skill / codex / lesson / pattern
即使 producer 在訊息中說「我已寫了 lesson」，main 偵測到 producer 寫以下任一路徑 → 視為 schema 違規（path boundary 違反），retry：
- `.claude/skills/**`（skill）
- `.framework/codex/**`（codex）
- `.framework/memory/lessons/**`（lesson）
- `.framework/memory/patterns/**`（pattern）

注意這四者分散在 `.claude/` 與 `.framework/` 兩個 root，不在同目錄下。

---

## 9. 與 Subagent 溝通的語言規範

| 場景 | 語言 |
|---|---|
| Spawn prompt（main → subagent） | 英文（schema 穩定）+ 必要時夾繁中描述 |
| Subagent 輸出 verdict JSON | 英文 key、value 隨內容（summary 可繁中） |
| Subagent artifact 本體 | 看 recipe（dev → 英文 / research / writing → 繁中） |
| Main 對使用者顯示 | 繁中 |

---

## 10. 給接手 agent 的提醒

- **Main session model 由使用者決定**，framework 不管。但 framework 啟用時 CLAUDE.md 會建議 Opus
- **Main 不要試圖學 producer / reviewer 的職責**，spawn 比自做高槓桿
- **不要在 main session 內 cache 大量資料**（intel-pack 是檔案、不是 main 的 in-memory state）
- **每次重 Explore 前重讀檔案**（_tree.yaml、plan.md），不要信 main 自己的記憶
- **進度顯示**：每完成一個 verdict 就更新 _manifest.md（人類追進度的入口）
- **Main 累積 token 失控時**：reset 是 OK 的——重啟 main，從 _active.yaml + _tree.yaml + _manifest.md 重建狀態

---

## 11. 相關文件

- `core/soul-schema.md`：role / skill / codex 格式
- `core/typed-interfaces.md`：verdict JSON schema
- `core/e2r-tree.md`：_tree.yaml 規範與遍歷邏輯
- `core/review-loop.md`：fail verdict 1-2-3-4 輪規則
- `core/clarification.md`：Explore Step 3 訪談規則
- `core/batch-lock.md`：_active.yaml 語意
- `core/learning-loop.md`：brief 完成時的學習迴圈
- `core/escalation-rules.md`：升級使用者的觸發條件
- `core/trust-modes.md`：Bash 白名單三模式
- `commands/framework-recall.md`：外部 KB recall（讀）端（opt-in）
- `core/amendment.md`：Step F' amendment 期完整規範
