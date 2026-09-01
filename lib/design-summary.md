# Multi-Agent Team Framework — 設計總覽

> ⚠️ **本檔為設計沿革快照（史料），現行制度以 `lib/core/*.md` 為準**——版本迭代（如 2026-07-06
> local_test 代驗制 / brief_close 腳本化）不回頭更新本檔，衝突時一律以 core 文件為權威。
>
> 框架設計的完整入口文件。概念總覽見 [`../README.md`](../README.md)。
>
> 版本：0.4.0 · 最後更新：2026-06-05 · 逐版變更見 [`../CHANGELOG.md`](../CHANGELOG.md)
>
> **0.2.0 修訂摘要**（基於約 10 個 dev-team brief 的實戰回饋）：
> - **深度 review 提前**：code-reviewer 對抗式新增「架構視角」+ checklist 加 plan↔code 對齊 / 跨檔 wiring / 註解 三項機械檢查（攔截過去拖到 holistic / 逐行 review 才爆的架構、命名 drift、wiring 漏接）。
> - **Plan 防肥分層**：planner 強制「架構決策層 vs 實作細節層」分離、plan 是當前狀態規格非 changelog、引用 architecture.md 必 grep 驗證、驗收條件分 [靜態] / [runtime]。
> - **Micro-brief 輕量化**：control-plane 加規模 triage（小改走 bug_fix）+ review-loop §3.4 size-based 對抗式豁免 + pipeline `second_review` 物件寫法。
> - **Test 策略**：engineer 禁自寫自測（球員兼裁判）、test-writer 獨立 session + case 數機器算、整合 / wire 行為標明 unit test 不涵蓋需 localTest。
> - **註解紀律**：engineer 預設不寫註解（只在 code 難懂 / 特殊商業邏輯才寫 WHY，禁 WHAT）、reviewer 同步審註解正確性。
> - **可插拔外部 KB sink（opt-in）**：learning loop 經批准的 lessons / patterns / preferences 可蒸餾升流外部 KB、`/framework-recall` 唯讀查跨 repo 參考；沒接 KB 的 repo 行為不變（解耦維持為預設）。詳見 §12.3。
>
> 本框架歷經數次內部設計迭代提煉而成，吸收 OneManCompany（arXiv:2604.22446）的 Talent + E²R 概念。SLIDERS（arXiv:2604.22294）相關的結構化儲存暫緩，預留 frontmatter 接口。

---

## 目錄

0. [文件目的](#0-文件目的)
1. [設計沿革](#1-設計沿革)
2. [核心哲學](#2-核心哲學)
3. [四層抽象（Role / Skill / Codex / Directive）](#3-四層抽象role--skill--codex--directive)
4. [架構總覽](#4-架構總覽)
5. [Framework 目錄結構](#5-framework-目錄結構)
6. [落地專案結構](#6-落地專案結構)
7. [Role 庫與 Recipe 系統](#7-role-庫與-recipe-系統)
8. [E²R Tree Search 實作](#8-er-tree-search-實作)
9. [Explore 階段](#9-explore-階段)
10. [Execute 階段](#10-execute-階段)
11. [Brief 生命週期](#11-brief-生命週期)
12. [Memory 架構與學習迴圈](#12-memory-架構與學習迴圈)
13. [Typed Interfaces](#13-typed-interfaces)
14. [檔案 Schema：Role / Skill / Codex](#14-檔案-schemarole--skill--codex)
15. [Init 流程與 Recipes](#15-init-流程與-recipes)
16. [Slash Commands 與啟用機制](#16-slash-commands-與啟用機制)
17. [權限 / Trust Modes / Tier / Worktree](#17-權限--trust-modes--tier--worktree)
18. [相對前一代的變更](#18-相對前一代的變更)
19. [仍開放的細節](#19-仍開放的細節)
20. [建議下一步](#20-建議下一步)
21. [給接手 agent 的備註](#21-給接手-agent-的備註)

---

## 0. 文件目的

定義一套可攜的 multi-agent team framework，供任何 Claude Code 專案 clone 進來、執行 init 後即可使用。

典型使用情境（對應內建 recipe）：
- **軟體開發**：主 session 是開發指揮，規劃 → 工程 → 審查，產出 code
- **研究 / 顧問**：主 session 是領域專家，抓資料 → 分析 → 出報告
- **資料分析**：主 session 處理資料集，分析 → 結論
- **通用助理**：主 session 接外部訊息 / 檔案投遞，做跨域協助

核心需求：
- Clone framework 進專案後，使用者執行 `/framework-init` 進行對話式設定
- 不同專案套不同 role 組合（例：A 用 researcher + analyst + writer；B 用 planner + engineer + code-reviewer）
- 品質把關必須機械化（reviewer 跑 git diff / test / lint / citation check 等）
- 同專案其他開發者可 opt-out
- **Framework 本體是純 md + JSON / YAML（零 shell script、零可執行程式）**

---

## 1. 設計沿革

本框架歷經數次內部設計迭代演進而成，關鍵轉折：

| 迭代 | 核心 |
|---|---|
| 初代 | 多階層角色（前台 / 中樞 / 規劃 / 工程主管），假設 nested Task 可用 |
| 第二代 | 撞到「subagent 不能再 spawn subagent」的技術牆 → 確立 Control Plane Pattern（固定數個 leaf subagent） |
| 第三代 | 框架不預定角色，改 archetype 整包 + init 生成 |
| **本框架** | **Talent + E²R + Recipe**——角色拆成可組合單元，受 OneManCompany 論文啟發的下一步 |

本框架是在前一代哲學上再做一次跳躍，非單純增量。

### 從前一代繼承的決議
- Control Plane Pattern（main session 為唯一編排者，subagent 全 leaf）
- 純 md + JSON、零 shell script
- Claude-only、無 multi-LLM family 支援
- 外部知識庫與 framework 解耦（不自動寫；可 opt-in 經批准升流，見 §12.3）
- Fail-closed Bash 白名單
- Brief 目錄約定
- Grill-me 單題制
- Worktree 隔離（dev 場景）
- 使用者授權才寫外部知識庫、依賴安裝走升級流程

### 推翻或重構的部分
見第 18 節「相對前一代的變更」。

---

## 2. 核心哲學

### 三原則

1. **Framework = 模式 + 工具，不是角色本身**
   Framework 規範「main session 為 control plane、E²R 三階段、verdict schema」這類抽象，不規範「engineer 是誰、做什麼」。Role 是落地時可組合的單元。

2. **角色 = 落地時組合的可攜實體**
   Role / Skill / Codex 都在 `.claude/` 內、可被使用者直接編輯。Recipe 是建議起點，不是強制配置。

3. **機械化審核 + 使用者把關**
   Reviewer 強制跑 Bash / 讀檔的審核動作清單，任一 fail 即 `verdict: fail`。Producer 對未來會影響執行的東西（lesson / pattern / codex / skill）只能「提議」，不能直接寫。Main + 使用者是 gatekeeper。

### 從 OMC 論文吸收的核心

| OMC 概念 | 本框架對應 |
|---|---|
| **Talent**（可攜身份 = skill + tool + config） | Role frontmatter 宣告 `skills:` + `tools:` + `tier:` |
| **Talent Market**（動態徵召） | Framework 內建 role 庫 + Recipe 組合（Talent Market 雛形）；未來可開放外部 role package |
| **E²R Tree Search**（Explore-Execute-Review 遞迴樹） | 本框架第 8 節，受限 2 層 |
| **Typed Organizational Interfaces** | 本框架第 13 節 verdict schema |

### 從 SLIDERS 論文吸收的概念（暫緩、預留接口）

- 第 12 節 memory 條目加 `frontmatter`（id / created_at / source_brief / last_referenced / reference_count）
- 第 14 節 codex 知識點下方標 Source / Confirmed / Confidence
- 後期升級結構化儲存時，這些欄位可直接 import 進 SQLite

---

## 3. 四層抽象（Role / Skill / Codex / Directive）

| 層 | 名稱 | 是什麼 | 對應 Claude Code 原生 | 對應 OMC |
|---|---|---|---|---|
| L1 | **Role**（角色） | Agent 人格 + 職責 + 工具範圍 | `.claude/agents/*.md` | Talent 的外殼 |
| L2 | **Skill**（技能包） | 領域方法論可載入封包，**跨專案重用** | `.claude/skills/*/SKILL.md` | Talent 的內含技能 |
| L2.5 | **Codex**（經驗包） | (role × project) 交集的領域知識，**專案專屬** | 新檔案類型 | Talent 的本地化記憶 |
| L3 | **Directive**（指令補充） | 在 brief 內針對單次任務追加的限制 / 重點 | brief.md 內某段 | Task-level prompt |

**關鍵差異**：
- Skill 是穩定方法論（HOW），跨專案重用，使用者批准後寫入
- Codex 是專案內的領域事實（WHAT），會隨專案演進，使用者批准後增修
- Skill 與 Codex 都採「spawn-time inline 載入」（main 把內容塞進 subagent prompt）
- 多個 role 可共用同一個 skill；每個 role 在每個 project 有自己的 codex（一 role 一檔起步）

---

## 4. 架構總覽

### 4.1 分層

```
┌──────────────────────────────────────────────────────────────┐
│ Framework core（寫死，所有專案共用）                         │
│  control plane / E²R tree / typed interfaces / batch lock /  │
│  trust modes / soul-schema / handoff / clarification         │
├──────────────────────────────────────────────────────────────┤
│ Framework roles/（寫死，可被 init 複製）                     │
│  engineer / planner / code-reviewer / data-analyst / writer  │
│  / financial-analyst / researcher / ...（共 N 份）           │
├──────────────────────────────────────────────────────────────┤
│ Framework skills/（寫死，可被 init 複製）                    │
│  pandas-techniques / dcf-valuation / code-review-checklist / │
│  citation-discipline / git-diff-analysis / ...               │
├──────────────────────────────────────────────────────────────┤
│ Framework recipes/（寫死，建議組合，不是強制）               │
│  dev-team / research-team / writing-team / finance-advisory  │
│  / data-analytics / general-assistant                        │
├──────────────────────────────────────────────────────────────┤
│ Framework init/（寫死，落地時呼叫一次）                       │
│  interview / generator / claude-md-template / pipeline-...   │
├──────────────────────────────────────────────────────────────┤
│ Framework commands/（寫死，init 複製到專案 .claude/commands）│
│  /framework * / /brief *                                     │
├══════════════════════════════════════════════════════════════┤
│ 落地專案層（init 產生，使用者隨時改）                         │
│  .claude/agents/{role}.md          ← 本專案 role             │
│  .claude/skills/{skill}/SKILL.md   ← 本專案 skill            │
│  .framework/codex/{role}.md           ← 本 role 的 codex        │
│  .claude/commands/                 ← 從 framework 複製       │
│  CLAUDE.md                         ← 本專案指示              │
│  .framework/pipeline.yaml                     ← 本專案 pipeline (DAG)   │
│  .framework/memory/                           ← 本專案記憶              │
│  .framework/briefs/                           ← 本專案 brief 工作目錄   │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 抽象任務流（E²R 樹，受限 2 層）

```
使用者：/brief-new "分析 Q2 營收異常"
  ↓
Main：偵測 active brief → 若有則拒；否則建 brief
  ↓
[Explore L0]
  Step 1. Roster 決策（main 自選 + 顯示 + 使用者可改）
  Step 2. 情報蒐集（intel-pack.md，讀 codex / memory / repo）
  Step 3. Grill 訪談（main 主持，cap 20 題）
  Step 4. Plan 草稿（spawn planner role；若無則 main 自寫）
  Step 5. Plan 審核（spawn planning-reviewer，1-2 輪）
  Step 6. 使用者批准（/brief-approve）
  ↓
[Execute L0 → 切 sub-briefs L1]
  for sub_brief in plan.sub_briefs:  # 並行（7d 決議）
    [Sub-brief L1 內部]
      for stage in pipeline.stages:  # 依 DAG 排程
        Main spawn producer → artifact
        Main spawn reviewer → verdict
        Verdict 處理（5c 規則：1-2 輪同 role / 3+ 輪回 Explore L0）
      sub_brief/final.md 出爐
  ↓
[Review L0 holistic]
  Main 讀所有 sub-brief 的 final.md
  檢查跨 sub-brief 一致性
  Pass / Fail（fail 回 Explore L0 重新規劃）
  ↓
[Amendment 期 — 可選]
  使用者於目視 code review 時若有小範圍修訂需求 → /brief-amend <sub_id>
  短訪談（cap 3 題） → 寫 amendment.md → spawn 主要 producer → 使用者目視 review
  無 reviewer / 不重跑 L0 holistic / 不寫學習 memory
  詳見第 11.6 節
  ↓
[學習迴圈]
  Main 寫 .framework/memory/sessions/{brief_id}.md（自動）
  Main 詢問品質評分（⭐ / ⚠️ / ❌）
  根據評分產出 lesson / pattern 提議 → 使用者批准 → 寫入
  使用者批准 codex 更新（若 producer 在 verdict 提了 suggest_codex）
  ↓
解鎖 _active.yaml → 完成
```

---

## 5. Framework 目錄結構

Framework 落地專案後的根目錄是 `.framework/`，內含 `lib/`（出貨層）+ 使用者資料目錄（init 生成）。

### 5.1 `.framework/lib/` 出貨層（升級時 overwrite）

```
.framework/lib/
├── core/                            ← 不可改抽象層
│   ├── control-plane.md             ← main session 行為規範
│   ├── e2r-tree.md                  ← E²R tree manifest 規範
│   ├── review-loop.md               ← 1-2-3-4 輪 + 回 Explore
│   ├── typed-interfaces.md          ← Verdict / Producer output schema
│   ├── batch-lock.md                ← _active.yaml 語意
│   ├── clarification.md             ← grill-me 規則（cap 20 題）
│   ├── trust-modes.md               ← strict / standard / sandbox + permissions sync
│   ├── soul-schema.md               ← Role / Skill / Codex schema
│   ├── escalation-rules.md          ← 高風險動作升級清單
│   ├── learning-loop.md             ← brief 結束時的學習迴圈
│   └── amendment.md                 ← L0 review 後的輕量修訂層
│
├── roles/                           ← Role template 庫
│   └── (planner / planning-reviewer / engineer / code-reviewer / researcher /
│        source-quality-reviewer / analyst / financial-analyst / data-analyst /
│        analysis-reviewer / reasoning-reviewer / writer / editor /
│        architecture-analyst / assistant / double-checker .md)
│
├── skills/                          ← Skill template 庫
│   └── ({skill_id}/SKILL.md × N)
│
├── recipes/                         ← 建議組合（非強制整包）
│   └── (dev-team / research-team / writing-team / finance-advisory /
│        data-analytics / general-assistant .yaml)
│
├── init/
│   ├── interview.md                 ← /framework-init 對話腳本
│   ├── generator.md                 ← 答案 → 檔案 的邏輯
│   ├── claude-md-template.md        ← CLAUDE.md 骨架
│   └── pipeline-yaml-template.md    ← .framework/pipeline.yaml 骨架
│
├── commands/                        ← 21 份；init 時複製到 .claude/commands/
│   ├── framework-{init, status, role-add/edit/list/remove}
│   ├── framework-{recipe-list, pipeline-edit, recover, unlock}
│   ├── framework-{trust-set, permissions-sync, learn}
│   └── brief-{new, status, approve, amend, cancel, import, reopen}
│
├── models.yaml                      ← tier → model ID
├── VERSION                          ← framework 版本號
└── design-summary.md                ← 本檔
```

### 5.2 `.framework/` 使用者資料層（init 生成、升級保留）

```
.framework/
├── lib/                             ← 同 5.1
├── codex/                           ← (role × project) 領域知識（init 為 producer 生成）
├── memory/                          ← lessons / patterns / sessions / architecture / preferences
├── briefs/                          ← active brief + inbox + _archive
├── worktrees/                       ← git worktree（dev recipe）
├── pipeline.yaml                    ← stage DAG（init 生成、使用者編輯）
└── .initialized                     ← init 紀錄（personal）
```

---

## 6. 落地專案結構

Init 跑完後：

```
my-project/
├── .framework/                       ← framework 根（lib 出貨 + 使用者資料）
│   ├── lib/                          ← clone / submodule / symlink；升級時 overwrite
│   │   └── (見 5.1)
│   ├── codex/                        ← init 生成（producer 才有）
│   │   └── {role}.md
│   ├── memory/
│   │   ├── MEMORY.md                ← 索引
│   │   ├── architecture.md          ← 專案級事實
│   │   ├── preferences.md
│   │   ├── lessons/                  ← 空目錄；{category}.md 由 learning loop 寫入
│   │   │   └── escalations/         ← 詳細事件檔
│   │   ├── patterns/                 ← 同上
│   │   └── sessions/                 ← brief 完成時 main 寫 {brief_id}.md
│   ├── briefs/
│   │   ├── _active.yaml              ← 當前 active brief
│   │   ├── inbox/                    ← 純檔案投遞入口（外部 script / 訊息機器人）
│   │   ├── _archive/                 ← 完成歸檔
│   │   │   └── {year-month}/{brief_id}/
│   │   └── {brief_id}/               ← 進行中 brief
│   │       ├── brief.md
│   │       ├── intel-pack.md
│   │       ├── clarifications.md
│   │       ├── plan.md
│   │       ├── _tree.yaml
│   │       ├── _manifest.md
│   │       ├── reviews/
│   │       │   └── L0-review.json
│   │       └── sub-briefs/
│   │           └── {sub_id}/
│   │               ├── sub-brief.md
│   │               ├── plan.md
│   │               ├── _manifest.md
│   │               ├── stages/{stage}/
│   │               │   ├── {role}.{type}.md
│   │               │   └── reviews/{reviewer}.verdict.json
│   │               └── final.md      ← 對 L0 的介面
│   ├── worktrees/                    ← dev recipe 才會有
│   │   └── brief--{sub_id}/
│   ├── pipeline.yaml                 ← stage DAG（init 生成）
│   └── .initialized                  ← init 紀錄（含 recipe / customizations / framework_version）
│
├── .claude/                          ← Claude Code native（不可動位置）
│   ├── agents/                       ← init 從 lib/roles/ 複製
│   │   └── {role}.md × N
│   ├── skills/                       ← init 從 lib/skills/ 複製
│   │   └── {skill_id}/SKILL.md
│   ├── commands/                     ← init 從 lib/commands/ 複製
│   │   └── (20 份 slash command)
│   └── settings.local.json           ← opt-out / trust mode / permissions sync
│
├── CLAUDE.md                         ← init 生成（含強制清單 + canonical schema）
└── AGENTS.md                         ← 一行指標指向 CLAUDE.md（可選）
```

---

## 7. Role 庫與 Recipe 系統

### 7.1 設計決議

- Role 是**獨立可組合單元**，不是 archetype 整包的一部分
- Framework 出貨一批 role template（`.framework/lib/roles/`），init 複製選用的進專案 `.claude/agents/`
- 複製進來後是 fork：使用者擁有完整修改權（frontmatter / body 都可改）
- Role 之間不互相點名；配對由 `.framework/pipeline.yaml` 解耦（producer ↔ reviewer 用 tag 配對）

### 7.2 Recipe（建議組合）

Recipe = 「我建議你這幾個 role + 這些 skill + 這條 pipeline 一起用」。落地時複製對應檔案，不是鎖定整包。

| Recipe | 典型場景 | Roles | 預設 trust mode |
|---|---|---|---|
| **dev-team** | 軟體開發 | planner, planning-reviewer, engineer, code-reviewer | standard |
| **research-team** | 研究調查 | researcher, source-quality-reviewer, analyst, reasoning-reviewer | standard |
| **writing-team** | 文件 / 報告產出 | writer, editor | standard |
| **finance-advisory** | 金融顧問 | researcher, source-quality-reviewer, financial-analyst, reasoning-reviewer, writer, editor | standard |
| **data-analytics** | 資料分析 | data-analyst, analysis-reviewer, writer | standard |
| **general-assistant** | 通用 / 外部觸發助理 | assistant, double-checker | standard |

Recipe YAML 範例：

```yaml
# .framework/lib/recipes/finance-advisory.yaml
name: finance-advisory
description: 金融顧問場景（抓資料 → 分析 → 報告）
roles:
  - researcher
  - source-quality-reviewer
  - financial-analyst
  - reasoning-reviewer
  - writer
  - editor
skills:
  - source-evaluation
  - citation-discipline
  - dcf-valuation
  - scenario-analysis
  - reasoning-bias-checklist
  - technical-writing-style
default_pipeline: full_advisory
default_trust_mode: standard
default_worktree: false
memory_categories:
  - research
  - analysis
  - sources
  - biases-avoided
  - drafting
  - editing
```

### 7.3 Role 客製範圍

複製進專案後：
- Frontmatter 全部可改（tier / tools / skills / codex / memory）
- Body 全部可改（職責 / 流程 / 鐵律）
- Framework 升級時 3-way merge（細節留實作階段）

---

## 8. E²R Tree Search 實作

### 8.1 結構

OMC 的 E²R 是遞迴樹。本框架**受限 2 層**：

- L0 = root brief（使用者開的）
- L1 = sub-brief（Explore 階段切的子任務 / Execute 階段 producer 申請拆分）
- L2 不允許

理由：
1. **Token 預算**：main 是樹的唯一遍歷者，深度 ≥3 後 main context 會爆
2. **使用者體感**：3 層以上的分解，使用者跟不上進度
3. **Termination 保證**：論文形式化保證在實作上不易 reproduce，硬限制更安全

### 8.2 Tree Manifest

每 brief 有 `.framework/briefs/{root_id}/_tree.yaml`。**詳細 schema 見 `core/e2r-tree.md` § 2.2（canonical）**。摘要：

- root: 字串（brief id）
- created_at / last_updated: ISO timestamp
- nodes 是 map：每個 brief / sub-brief id → 節點 object
- L0 節點：state ∈ {exploring, awaiting_approval, executing, reviewing, done, failed, cancelled}、含 holistic_review、consumed_child_ids
- L1 節點：state ∈ {pending, executing, paused, done, failed, cancelled}、含 parent / children / depends_on / pipeline_stages / decomposition_origin / worktree

範例見 `core/e2r-tree.md` § 7。Main 是唯一寫者。

### 8.3 Sub-brief 產生時機（5b）

兩條路皆可：
- (a) **Explore Step 4 plan 產出**：plan 直接列 sub-brief 清單
- (b) **Execute 中 producer 回 `needs_decomposition` verdict**：附拆分理由，main 判斷是否同意

producer 觸發 (b) 必須附 rationale 和 sub-brief 提案；main 不照單全收（避免 producer 拿來逃避責任）。

### 8.4 Review 失敗處置（5c）

- 第 1-2 輪：同 role 修改（保留 producer context、附 reviewer 意見）
- 第 3 輪以上：回 Explore 重新規劃（plan 可能改變）
- 第 4 輪強制升級使用者

整樹層級無 token 上限（信任 manifest 機制）；單節點 ≤ 4 輪 review 強制升級。

### 8.5 批准 Gate（5e）

- **僅 L0 plan 需使用者批准**（`/brief-approve`）
- Sub-brief 自動跑
- **例外**：sub-brief 涉及高風險動作（動依賴 / 動 schema / 跨模組大改）→ main 強制升級
- 高風險清單寫在 `core/escalation-rules.md`

### 8.6 並行單位（7d）

- **跨 sub-brief 並行**：無依賴的 sub-brief 同訊息 spawn 各自當前 stage 的 role
- Stage 內若同階段多 role 也並行
- **不**跨 sub-brief 跨 stage 同訊息（會把 token 拉爆）

---

## 9. Explore 階段

### 9.1 六步流程

```
Step 1. Roster 決策（main 獨自）
  - 讀 brief + recipes 配置 + 現有 .claude/agents/
  - 產出候選 role + 理由（一兩句話）
  - 顯示給使用者，使用者可加減（不訪談中問）

Step 2. 情報蒐集（main 獨自，並行）
  - 候選 role 的 Codex（讀全部）
  - .framework/memory/lessons/<相關分類>（grep + recency）
  - .framework/memory/patterns/<相關分類>
  - .framework/memory/sessions/<近 30 天同主題>
  - .framework/memory/architecture.md + preferences.md
  - 相關 repo 檔（Glob/Grep brief 提到的關鍵字）
  - 產出 intel-pack.md（情報摘要 + 不確定點清單）
  - 快取：mtime 比對，重 Explore 時若檔未變則重用

Step 3. 訪談（main 主持，grill-me 風格）
  - 從 intel-pack 不確定點生成題目
  - 單題制：推薦 + trade-off + options
  - **L0 cap 20 題**（單題 2 輪反詰）
  - sub-brief 不訪談；模糊則回 ambiguity verdict
  - 產出 clarifications.md

Step 4. Plan 草稿（spawn planner role；若 roster 無則 main 自寫）
  - 餵 brief + intel-pack + clarifications
  - 產出 plan-draft.md

Step 5. Plan 審核（spawn planning-reviewer，1-2 輪）
  - 機械檢查清單（章節完整 / 踩坑對照 / 架構相容 / 驗收可測）
  - 產出 plan.md（pass）或回 Step 4

Step 6. 使用者批准
  - `/brief-approve` 觸發
  - 呈現：plan + roster + sub-brief 預估 + 風險清單
  - 同意 / 修改 / 拒絕
```

### 9.2 Plan.md Schema（核心 + recipe 擴充）

**Core 必備欄位**（所有 recipe 共通）：
- 背景
- 範圍
- 驗收條件
- 非目標
- 已知風險
- Sub-briefs（若有，列 sub_id / title / scope / depends_on）
- allowed_paths（Producer Write 範圍邊界）

**Recipe 可擴充選用欄位**：
- dev-team：技術選型理由 / 介面契約
- research-team：sources 列表 / 假設
- finance-advisory：估值方法 / 情境參數

---

## 10. Execute 階段

### 10.1 協調模型：DAG（.framework/pipeline.yaml）

Pipeline 範例（完整 schema 見 `init/pipeline-yaml-template.md`）：

```yaml
# .framework/pipeline.yaml
framework_version: "0.3.0"
pipelines:
  full_advisory:
    description: 完整顧問流程
    stages:
      research:
        role: researcher
        reviewer: source-quality-reviewer
        depends_on: []
      analysis:
        role: financial-analyst
        reviewer: reasoning-reviewer
        depends_on: [research]
        skills_extra: [dcf-valuation, scenario-analysis]
      writing:
        role: writer
        reviewer: editor
        depends_on: [analysis]
default: full_advisory
review_rounds_override: null         # 預設 1-2-3-4，可改
bash_extra_allow: []
triage_hints:
  match_keywords: []
  match_recipes: []
```

Main 讀 DAG → 對每 sub-brief 跑選定 pipeline → 無依賴 stage 同訊息 spawn。

### 10.2 Review 雙層

- **Stage 內 review**：每 producer artifact 立即配對 reviewer 機械檢查
- **L0 holistic review**：所有 sub-brief Execute 完之後，main 讀各 sub-brief 的 final.md，檢查跨 sub-brief 一致性

L0 holistic review 不 spawn 專門 role；main 直接做（理由：一致性檢查需要看全局，spawn role 反而複雜化）。

### 10.3 產物路徑（7c）

```
.framework/briefs/{brief_id}/
├── brief.md / intel-pack.md / clarifications.md / plan.md
├── _tree.yaml / _manifest.md
├── reviews/L0-review.json
└── sub-briefs/{sub_id}/
    ├── sub-brief.md / plan.md / _manifest.md
    ├── stages/{stage}/
    │   ├── {role}.{type}.md
    │   └── reviews/{reviewer}.verdict.json
    └── final.md
```

慣例：
- 每 sub-brief 獨立目錄，互不相寫
- `final.md` 是該 sub-brief 對 L0 的介面，L0 review 只讀此檔
- artifact 命名：`{role}.{type}.md`
- code artifact 在 `.framework/worktrees/`，brief/ 內只放 plan/review/diff-summary

---

## 11. Brief 生命週期

### 11.1 來源（8a）

| 來源 | 描述 | 預設啟用 |
|---|---|---|
| **A. 純檔案** | `.framework/briefs/inbox/{name}.md` | 是（外部 script / 訊息機器人投遞用此） |
| **B. 對話偵測** | 使用者打需求 → main 偵測 → 詢問是否進入正式流程 | 是 |
| **C. Slash command** | `/brief-new` 短訪談 → 建檔 | 是（**主推**） |
| **D. GitHub Issue 整合** | `/brief-import <url>` | 可選（git remote 是 GH 才提示） |

### 11.2 ID 格式（8b）

`YYYY-MM-DD-<slug>`，例：`2026-05-06-revenue-q2`。Sub-brief：`{root_id}.{a/b/c/...}`。

### 11.3 並發（8c）

> ⚠️ **本節決議已於 2026-09-01 被取代**（multi-lane 改制，現行規範見 `core/batch-lock.md`）：
> 「全域單 active brief」→「每 scope 單 active」——repo-disjoint 的 brief 可多 lane 並行
> （lock registry `briefs/_active/{brief_id}.yaml`，每 lane 一個 session）。以下為原決議史料。

- **單 active brief**（`.framework/briefs/_active.yaml` 為單一進行中 brief 的鎖）
- 試開新 brief 時若已 active → 提示：等待 / 升級為 sub-brief / 取消當前
- 「multi-agent」=「同一個 main session 內 spawn 多 subagent」，**不是**多 process / 多 session 同時跑

### 11.4 完成處置（8d）

- Brief 完成 → main 寫 `.framework/memory/sessions/{brief_id}.md` 摘要 + archive 路徑
- Brief 詳細目錄移至 `.framework/briefs/_archive/{year-month}/{brief_id}/`
- 學習迴圈詢問品質評分，產出 lesson / pattern 提議（見第 12 節）

### 11.5 /brief-new 對話流程（13e）

```
/brief-new
  → 描述需求（一行或多行）
  → main 偵測關鍵字 → 建議 recipe + roster + 理由
  → 使用者：y / edit / other
  → 建 brief 目錄 → 進入 Explore Step 1（roster 確認顯示） → Step 2-6
```

### 11.6 Amendment 層（L0 review 後、歸檔前的輕量修訂）

L0 holistic review pass 後、學習迴圈前（控制面 Step F'），使用者可對任一 sub-brief 觸發 `/brief-amend <sub_id> "<一句話>"`，做小範圍修訂。設計動機：使用者目視 code review 時若發現小範圍規格 / coding style 建議，打回 Explore 重 plan 太重、開新 brief 又破壞追蹤性。

**核心特徵**：
- **無 reviewer**：信任使用者目視審；主要 producer 改完即交付
- **單 producer 動作**：最多 spawn 2 次（初始 + 1 次 ambiguity 續答）
- **訪談 cap 3 題、無反詰**：求快
- **通用 recipe**：主要 producer 從 sub-brief pipeline 最末 stage 對應 role 推導（dev → engineer / writing → writer / data-analytics → data-analyst 等），不限 dev-team
- **不參與學習迴圈**：不寫 lessons / patterns / sessions
- **不允許拆分 / 新依賴**：`needs_decomposition` / `needs_dependency` 直接 reject
- **次數軟限**：第 2 次需警告同意、第 3 次強制 reject（訊號為原 plan 不貼合，應改走 plan）
- **路徑邊界**：producer 寫 `plan.allowed_paths ∪ amendment.allowed_paths_delta` 之外的檔視為 tool_error
- **spec_id**：amendment verdict 用 `{root}.{sub}#{a_id}` 格式

**檔案結構**：

```
.framework/briefs/{root}/sub-briefs/{sub_id}/amendments/a1/
├── amendment.md                ← 規格 + path delta
├── clarifications.md           ← 訪談紀錄（0 題時不寫）
├── {producer-role}.patch.md    ← 例 engineer.patch.md / writer.patch.md
└── outcome.md                  ← done / done_with_notes / rejected / cancelled
```

**`_tree.yaml` 變動**：sub-brief 節點下加 `amendments[]` 陣列（含 id / state / summary / allowed_paths_delta / created_at / completed_at）。Amendment **不算 sub-brief 節點**，不進 `nodes` map。

**回滾策略**：純靠 git。Framework 不做版本管理。

完整規範見 `lib/core/amendment.md`、`lib/commands/brief-amend.md`。

---

## 12. Memory 架構與學習迴圈

### 12.1 子分類

| 類別 | 用途 | 寫入時機 | 讀取時機 |
|---|---|---|---|
| **lessons/** | 行為糾正 | 失敗 / 使用者糾正 / Review 不過 | Explore Step 2，餵相關 producer/reviewer |
| **patterns/** | 成功 playbook | brief 完成且品質高 | Explore Step 4，餵 planner |
| **sessions/** | brief 歷史摘要 | brief 完成（無論成敗） | Explore Step 2 找近期同主題 |
| **preferences.md** | 跨 brief 偏好 | 使用者明示 / 偵測重複糾正 | 每 brief 啟動 |
| **architecture.md** | 專案級事實 | init / 使用者編輯 | Explore Step 2、Roster 決策 |

### 12.2 Codex vs Memory 邊界

- **Codex** = 靜態領域知識（資料欄位意義、估值公式適用條件等）；變動慢
- **Memory** = 動態經驗累積（這次怎麼做的、為什麼成功/失敗）；變動快

### 12.3 學習迴圈（brief 完成時）

詳見 `core/learning-loop.md` § 3。摘要：

```
Step 1. Main 自動寫 .framework/memory/sessions/{brief_id}.md（**絕不可省**，無需批准）
Step 2. 詢問品質評分：⭐ 滿意 / ⚠️ 還行 / ❌ 不行 / 跳過
Step 3. 彙整 verdict.suggest_* + main 補充 → 提議清單
Step 4. 使用者批准（y / n / edit / yes-all）
Step 5. Main **直接寫**：
  - lesson → .framework/memory/lessons/<cat>.md
  - pattern → .framework/memory/patterns/<cat>.md
  - codex 更新 → .framework/codex/<role>.md
  - skill → .claude/skills/<name>/SKILL.md
[歸檔 + 解鎖] .framework/briefs/{brief_id}/ → .framework/briefs/_archive/{year-month}/{brief_id}/；刪 _active.yaml
```

**鐵律**：
- Step 1 sessions 自動寫——**brief 必走、不論 verdict 全 pass / 評分跳過**
- Main 不在 mid-execution 寫 memory；但 learning loop 階段使用者批准後 **可直接寫**
- **永遠不需另開 brief 寫 memory**（漏跑用 `/framework-learn` 補）

**外部 KB sink（opt-in）**：repo 若在 `.initialized` 宣告 `knowledge_base{path,promote,recall}`，Step 5 寫完 local 後可把經批准的 lessons / patterns / preferences 蒸餾升流外部 KB（Step 4 的 `(m)` 選項），`/framework-recall` 則唯讀查 KB 參考其他 repo。沒宣告 = local-only（預設）。詳見 `core/learning-loop.md` §8.5 / §11.5。

### 12.4 Memory 紀律

- patterns 一條 ≤ 3 行 + 詳情指標檔
- 同分類上限 30 條，超出時 main 提議淘汰最久未引用的
- 同 lesson 重複 ≥3 次 → 升級為 preferences.md 硬規則

### 12.5 Memory 餵誰（9c）

| 來源 | 餵給 | 數量上限 |
|---|---|---|
| architecture.md | main + 所有 spawn 的 role | 全文 |
| preferences.md | main + 所有 role | 全文 |
| lessons/<cat> | 對應類別 producer + reviewer | 3-5 條（main 篩） |
| patterns/<cat> | 對應類別 planner | 3 條（main 篩） |
| sessions/ | main 自己 | 3 個摘要連結 |

注：(i) 起步，(ii) 是「每 role 餵全部、role 自己挑」是落地後可優化方向。

### 12.6 SLIDERS 預留接口（9d）

每個 memory 檔（`lessons/{cat}.md` / `patterns/{cat}.md`）用**整檔一個 frontmatter**（檔級 metadata），body 為 bullet list（每條 entry 帶 inline metadata）：

```markdown
---
category: data-analysis
created_at: 2026-05-06T10:00:00
last_updated: 2026-05-06T11:30:00
entry_count: 2
---
# Lessons: data-analysis

- [2026-05-06] [id:lesson-2026-05-06-001] cohort 切法影響 revenue baseline 計算
  - source_brief: 2026-05-06-revenue-q2
  - last_referenced: 2026-05-06
  - reference_count: 0
- [2026-05-06] [id:lesson-2026-05-06-002] ...
```

完整 schema 見 `core/learning-loop.md` §8.1。

升級 SLIDERS 時：寫 import 工具掃 inline bullet metadata 進 SQLite（每行 = 一個 entry），檔級 frontmatter 對應檔級欄位。md 仍為 source of truth、DB 為查詢索引。

---

## 13. Typed Interfaces

### 13.1 Verdict types（10a）

| Verdict | 語意 | 觸發者 | Main 處理 |
|---|---|---|---|
| **pass** | 機械檢查全過 | reviewer | 進下一 stage |
| **fail** | 機械檢查不過 | reviewer | 1-2 輪同 role / 3+ 回 Explore |
| **ambiguity** | 缺資訊無法繼續 | producer / reviewer | 自行補 / 升級 L0 / 累積升級 |
| **needs_decomposition** | 任務太大 | producer | Main 判斷是否拆 sub-brief |
| **needs_dependency** | 需新依賴 | producer | 升級使用者裝 |
| **tool_error** | 檢查工具本身壞 | reviewer | 升級使用者修工具 |
| **partial** | 部分完成 | producer | Main 判斷接受或要求補完 |

### 13.2 統一寬鬆 Schema（10b/10c）

Producer 與 Reviewer 共用一份 schema，actor.type 區分：

```json
{
  "verdict": "pass|fail|ambiguity|needs_decomposition|needs_dependency|tool_error|partial",
  "actor": {
    "role": "code-reviewer",
    "type": "producer|reviewer",
    "spec_id": "2026-05-06-revenue-q2.a",
    "round": 1,
    "stage": "analysis",
    "adversarial": false
  },
  "summary": "<一句話>",
  "checks": [
    {"name": "tests", "result": "pass|fail", "evidence": "..."}
  ],
  "questions": [...],
  "decomposition_proposal": {
    "rationale": "...",
    "sub_briefs": [{"title": "...", "scope": "...", "depends_on": [...]}]
  },
  "missing_dependency": {"package": "...", "version": "...", "reason": "..."},
  "tool_error_details": "...",
  "partial_completed": [...],
  "partial_missing": [...],
  "artifact": "<path or null>",
  "suggest_lesson": null,
  "suggest_pattern": null,
  "suggest_codex": null,
  "suggest_skill": null
}
```

Verdict 可用範圍依 actor.type：
- `producer`：pass / partial / ambiguity / needs_decomposition / needs_dependency
- `reviewer`：可加 fail / tool_error

### 13.3 Handoff Block 取消（10d）

不再 emit 人類可讀 handoff block。JSON 的 `summary` 欄位即可，main 在進度顯示時格式化。Next 由 .framework/pipeline.yaml 決定，不需 role 自己宣告。

### 13.4 Schema 版本（10e）

Framework version 統管 schema version，role md 不重複宣告。落地專案的 `.claude/agents/*.md` 在 framework 升級時走 3-way merge。

---

## 14. 檔案 Schema：Role / Skill / Codex

> 細節可在落地後跑幾個 repo 根據回饋調整（使用者明示）。本節為起步骨架。

### 14.1 Role frontmatter

```yaml
---
name: code-reviewer
description: 審 code（讀 diff / 跑 test / lint）
type: reviewer                # producer | reviewer
tier: mid                     # cheap | mid | top
tools: Read, Bash, Glob, Grep

produces: []                  # tag 系統用於 .framework/pipeline.yaml 配對
reviews: [code]

skills:
  - global/code-review-checklist
  - global/git-diff-analysis

codex: auto                   # auto / explicit-path / null

memory:
  consume: [code-review, engineering]
  contribute: [code-review]

worktree: optional            # required | optional | forbidden（依場景；詳見 soul-schema.md §2.1）
---
```

### 14.2 Role body（章節順序固定）

1. 職責（一段話）
2. Path Boundaries（Read 白名單 / Write 白名單 / Forbidden）
3. Prerequisite Gate（啟動時必檢查，標 BLOCKING vs non-blocking）
4. 執行流程（編號步驟）
5. 審核動作清單（reviewer-only，必跑 Bash / 必讀檔）
6. 鐵律（禁止事項）

相對早期設計的精簡：
- 早期的「輸出 JSON Schema」章節 → 統一引用 `core/typed-interfaces.md`
- 早期的「Handoff Block」章節 → 取消（見 §13.3）

### 14.3 Skill 檔（`.claude/skills/{skill_id}/SKILL.md`）

```yaml
---
name: code-review-checklist
description: 機械化 code review 必查項目
scope: global                 # global | local
applicable_roles: [code-reviewer, planning-reviewer]
---

# Code Review Checklist
（純知識文檔，無強制 schema）
```

對齊 Claude Code 既有 Skill 系統格式。`.claude/skills/{skill_id}/` 內可放輔助檔。

### 14.4 Codex 檔（`.framework/codex/{role}.md`）

```yaml
---
role: data-analyst
project: analytics-q4
version: 0.3.2
last_updated: 2026-05-06
last_updated_by: 2026-05-06-revenue-q2
---

# Codex: data-analyst @ analytics-q4

## 1. 領域知識點
### <欄位名>
- 含義：...
> Source: 2026-04-12-revenue-baseline / Confirmed: yes / Confidence: high

## 2. 業務規則
## 3. 已知陷阱
## 4. 使用者偏好
## 5. 變更紀錄
```

每知識點下方標 Source / Confirmed / Confidence（SLIDERS provenance 雛形）。

### 14.5 多 Codex 策略

**起步：一 role 一檔**。上限約 500 行，超過再升級到主檔 + 子檔引用結構。

---

## 15. Init 流程與 Recipes

### 15.1 觸發

Main 偵測 `.framework/.initialized` 不存在 → 提示「偵測到 framework 未初始化，要 init 嗎？(y/n/later)」。`later` 不強制（CLAUDE.md 會走一般 Claude Code 行為）。

### 15.2 六步流程

```
Step 1. Repo 偵測（main 自動）
  - 掃 README / 配置檔 / 程式語言指標
  - 偵測 recipe 候選 + 信心度

Step 2. Recipe 選擇（單題）
  (a) 採用 main 推薦
  (b) 從 6 個 recipe 選一個
  (c) free-form：手選 role + skill

Step 3. 客製問題（4-6 題）
  - 主要使用情境（一句話 → CLAUDE.md）
  - Tier 偏好
  - Trust mode（含偵測推薦）
  - Worktree y/n
  - Bash 白名單追加（free-form）
  - 偏好語言

Step 4. Codex 草稿生成
  - 對每個 role 輕訪談 + main Glob/Grep 補充
  - 寫 .framework/codex/{role}.md v0.1.0（confidence: low）

Step 5. 檔案生成（main 自動）
  - .claude/agents/ / .claude/skills/ / .framework/codex/
  - .claude/commands/ 複製
  - CLAUDE.md / .framework/pipeline.yaml
  - .framework/memory/ 結構
  - .framework/briefs/ 結構
  - .framework/.initialized

Step 6. 摘要 + 強制重啟提示
  - 列生成清單
  - 強制提示「必須重啟 Claude Code session 才能使用 framework」（agent / slash command 列表須 session 啟動時鎖定，不重啟跑 brief 必失敗）
  - **不**提供「現在試跑 dummy brief」選項
```

### 15.3 重新 init（12d）

- `/framework-init --reset`：全重來。先備份既有 codex 到 `.framework/codex/.backup-{timestamp}/`
- 修改個別 role：用 `/framework-role-edit` 等指令，不需要 reset

### 15.4 Recipe 偵測規則

| 偵測 | 推薦 |
|---|---|
| go.mod / Cargo.toml / pyproject.toml + cmd/ src/ tests/ | dev-team |
| 大量 .csv / .ipynb | data-analytics |
| 大量 .md / pdf / 無程式碼 | research-team 或 finance-advisory |
| 空 / .devcontainer/ | sandbox trust + general-assistant |
| README 提及「analysis」/「report」 | research-team |
| README 提及「financial」/「investment」 | finance-advisory |

---

## 16. Slash Commands 與啟用機制

### 16.1 Namespace（13a）

`/framework`（系統管理，少用）+ `/brief`（日常，高頻）。`/memory` 暫時併進 `/framework`。

### 16.2 指令列表（13b，共 21 個）

#### `/framework`

| 指令 | 用途 |
|---|---|
| `/framework-init` | 初始化（加 `--reset` 旗標可全重來） |
| `/framework-status` | 顯示啟用狀態 / recipe / roles / active brief |
| `/framework-role-list` | 列當前 role |
| `/framework-role-add` | 對話式新增 |
| `/framework-role-edit <name>` | 對話式修改 |
| `/framework-role-remove <name>` | 移除（提示連帶 pipeline 影響） |
| `/framework-recipe-list` | 列內建 recipes |
| `/framework-pipeline-edit` | 改 .framework/pipeline.yaml |
| `/framework-recover` | 從中斷 brief 恢復 |
| `/framework-unlock` | 強制清 _active.yaml |
| `/framework-trust-set <mode>` | 切 trust mode + sync settings.local.json permissions |
| `/framework-permissions-sync` | 強制 re-sync settings.local.json permissions |
| `/framework-learn` | 補處理歸檔 brief 的 _suggestions / ad-hoc 加 lesson / pattern（不需另開 brief） |
| `/framework-recall <主題>` | 唯讀查外部 KB 參考其他 repo（opt-in，recall=true 才可用） |

#### `/brief`

| 指令 | 用途 |
|---|---|
| `/brief-new` | 開新 brief（短訪談） |
| `/brief-import <url>` | GH issue 匯入 |
| `/brief-status` | active brief 進度 + 近期完成 |
| `/brief-approve` | 批准當前 plan（L0 gate） |
| `/brief-amend <sub_id> "..."` | 對 done 的 sub-brief 做輕量修訂（L0 review pass 後、歸檔前） |
| `/brief-cancel` | 取消當前 active brief |
| `/brief-reopen <id>` | 重啟歸檔 brief |

### 16.3 啟用偵測（13c）

CLAUDE.md 開頭四層判斷：

```markdown
## Framework 啟用判斷
1. 環境變數 FRAMEWORK_DISABLED 未設為 1
2. .claude/settings.local.json 內 framework_disabled 不為 true
3. .framework/.initialized 檔存在
4. .framework/lib/core/control-plane.md 檔存在

四條件全滿足 → 載入 framework 行為
任一不滿足 → 略過本檔，正常使用 Claude Code
```

### 16.4 Opt-out（13d）

- (1a) env `FRAMEWORK_DISABLED=1`：個人一次性
- (1b) `.claude/settings.local.json` 加 `framework_disabled: true`：個人長期（不進 git）

兩者皆可，env 優先。

---

## 17. 權限 / Trust Modes / Tier / Worktree

### 17.1 Tool 權限矩陣（14a）

| 角色 | Read | Write | Edit | Bash | Task | WebFetch | Skill |
|---|---|---|---|---|---|---|---|
| main | ✓ | ✓ | ✓ | 白名單 | ✓ | 可選 | ✓ |
| producer | ✓ | ✓（限自己 subdir） | 視 | 視 | ✗ | 視 | ✓（spawn-time inline） |
| reviewer | ✓ | ✗ | ✗ | 白名單 | ✗ | 視 | ✓（spawn-time inline） |

**檔案類型寫入權**：

| 檔案 | 寫者 |
|---|---|
| `.claude/agents/*.md` | 僅 main，透過 slash command |
| `.claude/skills/**` | 僅 main，使用者批准 |
| `.framework/codex/*.md` | 僅 main，使用者批准 |
| `.framework/briefs/{id}/sub-briefs/{sub_id}/stages/{stage}/*.md` | 對應 producer |
| `.framework/briefs/{id}/_tree.yaml`、`_manifest.md` | 僅 main |
| `.framework/memory/sessions/*.md` | 僅 main 自動 |
| `.framework/memory/lessons/*.md`、`patterns/*.md` | 僅 main，使用者批准 |
| `.framework/memory/architecture.md`、`preferences.md` | 使用者直接 / main 提議 |

**Producer 不能直寫 `.claude/skills/`、`.framework/codex/`、`.framework/memory/lessons/`、`.framework/memory/patterns/`**（這四者分散在 `.claude/` 與 `.framework/` 兩個 root，不在同目錄下）。要更新只能透過 verdict 的 `suggest_*` 欄位 → main 收 → 使用者批准 → main 寫。理由：避免幻覺放大鏈（第 14a 詳述）。

### 17.2 Trust Modes（14b）

三檔信任模式：

| 模式 | 適用 | Bash 哲學 | 依賴安裝 |
|---|---|---|---|
| **strict** | 生產 / 共用 / 不熟環境 | 最小白名單 | 嚴格 needs_dependency |
| **standard** | 個人熟悉 repo（預設） | 合理白名單 | needs_dependency |
| **sandbox** | 拋棄式 VM / 空白專案 | 大幅放寬 | 直接允許 install |

**各模式 deny**：

- **strict**：standard 全部 + `git merge --no-ff`、所有 `rm`、所有網路指令
- **standard**：`git push`、`reset --hard`、`config`、`rm -rf`、`sudo`、`chmod`、`chown`、`curl`、`wget`、`pip install`、`npm install`、`go get`、`ssh`
- **sandbox**（只擋災難級）：
  - `sudo`（trust escalation 永遠擋）
  - `rm -rf /`、`rm -rf ~`、`rm -rf $HOME`
  - `chmod -R 777 /`、`chmod -R 777 ~`
  - `git push --force` to main / master
  - `git config --global`
  - `ssh` 到非 localhost
  - `> /etc/...`、`> /usr/...`

**模式切換**：`/framework-trust-set <mode>`，含警告確認。

**自動偵測**（init Step 3 給推薦預設）：

| 偵測 | 推薦 |
|---|---|
| `.github/workflows/`、`Dockerfile.production`、`deploy/`、CI 配置 | strict |
| 有真實程式碼但無 production indicator | standard |
| 空專案 / 只有 `.devcontainer/` / dir 名含 sandbox/scratch/playground | sandbox |
| 偵測不到 | standard（讓使用者自選） |

寫進 `.framework/.initialized`：

```yaml
trust_mode: sandbox
bash_extra_allow: []
bash_extra_deny: []
```

### 17.3 Model Tier（14c）

```yaml
# .framework/lib/models.yaml
cheap: claude-haiku-4-5-20251001
mid:   claude-sonnet-4-6
top:   claude-opus-4-7
```

覆寫順序：recipe default → init 覆寫 → 手改 frontmatter。Main session model 不受 framework 控制。

### 17.4 Worktree（14d）

- `dev-team` recipe 預設啟用，每 sub-brief 一個 worktree
- 其他 recipe 預設不啟用
- 失敗 / 取消 → 保留 worktree + 留 `WORKTREE_ABANDONED.md` 標記，使用者手動處置

生命週期（main 管理）：
- Sub-brief Execute 開始 → `git worktree add .framework/worktrees/brief--{sub_id} -b brief/{sub_id}`
- Sub-brief 完成 + L0 review pass → `git merge brief/{sub_id}` → `git worktree remove`
- Sub-brief 取消 / 失敗 → 保留

---

## 18. 相對前一代的變更

### 保留
- Control plane 模式 / main session 為唯一編排者
- 純 md + JSON、零 shell script
- Claude-only
- 外部知識庫解耦（預設；可 opt-in 升流，見 §12.3）
- Fail-closed Bash（但加 trust mode 三檔）
- Spec/brief 目錄約定（.framework/briefs/ 取代 specs/，結構類似）
- Grill-me 單題制
- Worktree 隔離（dev recipe 預設）
- 使用者授權才寫外部知識庫、依賴安裝走升級流程
- Subagent 全 leaf（nested Task 不可用）
- 早期版本的 core/* 概念大部分保留

### 重構
- **Archetype 拆成 Role + Skill + Recipe 三層**：role 獨立可組合，skill 跨 role 共用，recipe 是建議組合
- **新增 Codex 層（L2.5）**：(role × project) 領域知識，與 Skill / Memory 分離
- **平面 review loop → E²R 2 層樹**：sub-brief 是第一公民、Explore 流程明確化（6 步）、Execute 用 DAG pipeline、Review 雙層（stage + L0 holistic）
- **Verdict 擴展**：從早期的 pass/fail + handoff，擴展為 7 個 verdict types（含 ambiguity / needs_decomposition / needs_dependency / tool_error / partial）
- **取消 Handoff Block**：JSON summary 欄位代替
- **Producer 不直寫 `.claude/skills/` / `.framework/codex/` / `.framework/memory/{lessons,patterns}/`**：必須走 verdict 的 suggest_* 欄位 + 使用者批准（防幻覺放大）
- **Trust Modes 三檔**：strict / standard / sandbox（解決沙盒場景痛點）
- **Memory 子分類擴展**：lessons / **patterns**（新）/ sessions / preferences / architecture
- **Brief 取代 spec/batch**：`/brief-new`、ID 用日期+slug、_active.yaml 取代 _batch.lock

### 新增
- 學習迴圈：brief 完成時詢問品質評分 → 產出 lesson/pattern 提議
- SLIDERS provenance frontmatter 預留接口（每 memory 條目 + codex 知識點）
- /brief namespace（與 /framework 分離）
- /framework-trust-set 模式切換指令
- 可插拔外部 KB sink（opt-in）：learning loop 升流蒸餾後 lessons/patterns/preferences + /framework-recall 唯讀跨 repo 查詢；沒接 KB 維持解耦（見 §12.3）
- **Amendment 層**：L0 review 後、歸檔前的輕量修訂入口（無 reviewer、cap 3 訪談、單 producer 動作、第 2 次警告 / 第 3 次拒）

### 推翻（早期即已捨棄，本框架延續）
- Nested Task / 池主管獨立 subagent
- 多 LLM family 支援
- Shell script 檔案
- Producer 自主裝依賴
- Framework 預定義固定 4 個 subagent

---

## 19. 仍開放的細節

### 19.A. Core 層具體 md 內容（最高優先）

需逐份撰寫：
1. `core/control-plane.md`
2. `core/e2r-tree.md`
3. `core/review-loop.md`
4. `core/typed-interfaces.md`
5. `core/batch-lock.md`
6. `core/clarification.md`
7. `core/trust-modes.md`
8. `core/soul-schema.md`
9. `core/escalation-rules.md`
10. `core/learning-loop.md`
11. `core/amendment.md`

建議順序：8 → 1 → 2 → 3 → 4 → 7 → 10 → 6 → 5 → 9 → 11。

### 19.B. Roles 庫各 role md 內容

16 個 role template 逐份撰寫。dev-team 系列（planner/planning-reviewer/engineer/code-reviewer）最急（驗證最深的場景）。

### 19.C. Skills 庫各 skill 內容

優先級：code-review-checklist、git-diff-analysis、citation-discipline、source-evaluation、reasoning-bias-checklist。

### 19.D. Recipes 6 份 yaml 內容

dev-team / data-analytics / finance-advisory 三份最急（對應軟體開發、資料分析、顧問場景）。

### 19.E. Init 對話腳本

`init/interview.md` 的實際題目與分支邏輯、`init/generator.md` 把答案轉檔的具體邏輯、`init/codex-bootstrap.md` 第 4 步輕訪談流程。

### 19.F. Slash commands 20 份 md 內容

每個指令的對話腳本與檔案操作邏輯。

### 19.G. Pipeline.yaml 完整 schema

`stages` / `depends_on` / `review_rounds_override` / 各欄位驗證、recipe 擴充欄位、跨 sub-brief 依賴表達。

### 19.H. Plan.md 完整 schema

Core 必備欄位的具體格式、recipe 擴充欄位約定、解析邏輯。

### 19.I. _tree.yaml 完整 schema

Node state machine、寫入時機、衝突處理。

### 19.J. 錯誤處理細節

Subagent Task call 失敗的重試策略、JSON 解析失敗的修正回合、tool_error 的升級流程細節。

### 19.K. 中斷恢復細節

Ctrl-C 後 _active.yaml 的處置、`/framework-recover` 的逐 sub-brief 詢問流程、worktree 取捨。

### 19.L. Framework 升級同步

3-way merge 機制、版本號比對、role/skill 客製保留策略。

### 19.M. 落地後的調整（使用者明示）

第 11 題的檔案 schema、第 9c 題 memory 餵 role 策略、第 14b 的細部白名單規則——都先以骨架落地，跑幾個 repo 再根據回饋調整。

### 19.N. 學習迴圈優化（暫緩）

第 14a 的「auto_approve」信任模式（已用熟的 repo 自動批准低風險類別），落地後再討論。

### 19.O. SLIDERS 結構化儲存升級

整個結構化儲存路線。落地後若 memory / codex 規模膨脹明顯，再啟動 import 工具設計。

### 19.P. Amendment 層落地細節

`core/amendment.md` 已寫，但以下細節落地後才能定：
- Step F' 期間 `_active.yaml.phase` 與 `_tree.yaml.root.state` 的具體 enum 值（與 batch-lock.md / e2r-tree.md 對齊）
- Engineer role md 是否需特別處理 `mode: amendment` 旗標（目前預設不處理）
- Amendment 失敗 / 拒絕後是否要在 `.framework/memory/lessons/escalations/` 留 mirror（目前不留）
- Phase B 的 `/brief-reopen` 與 amendment 次數計算如何延續

---

## 20. 建議下一步

實作順序（落地優先級）：

1. **寫 `core/soul-schema.md`**——所有 role 必遵循的地基
2. **寫 `core/control-plane.md`**——main session 行為規範
3. **寫 `core/typed-interfaces.md`**——verdict / handoff 的 JSON schema
4. **寫 `core/e2r-tree.md` + `core/review-loop.md`**——任務流核心
5. **寫 `core/trust-modes.md`**——權限機制
6. **寫 dev-team recipe 全套**（4 個 role + 必要 skill + recipe.yaml）——dev 場景最先驗證
7. **驗證**：在一個 dev 專案下實際跑一個 dummy brief，看 main 能不能跑完一輪
8. **寫 finance-advisory recipe 全套**——驗證跨 domain，是本框架最大的改進方向
9. **寫 init 對話 + 20 個 slash commands**
10. **寫剩餘 recipes**
11. **錯誤處理 / 中斷恢復 / 升級同步等 edge cases**

---

## 21. 實作備註

### 已明確排除的方向

**不要**再提：
- Nested Task / 池主管獨立 subagent / 獨立前台 subagent
- 多 LLM family（Claude only）
- Shell script 可執行檔
- Producer 自主裝依賴 / 自主寫 skill / codex
- Framework 預先定義固定整包 archetype
- 全自動寫外部知識庫（gated opt-in 升流是已接受方案，見 §12.3）

### 容易被新 agent 誤解的點

- **Role 是落地專案的財產，不是 framework 的**：framework 出貨 template，使用者複製進 .claude/agents/ 後就是 fork
- **Skill 跨專案、Codex 專案內**：兩者都可被 role 在 spawn-time inline 載入
- **Producer 對未來生效的東西只能「提議」，不能直寫**（防幻覺放大）
- **E²R 受限 2 層**：不要試圖做無界遞迴
- **Sub-brief 不訪談使用者**：模糊就回 ambiguity verdict
- **Single active brief**：multi-agent ≠ multi-process（⚠️ 2026-09-01 已放寬為「每 scope 單 active」multi-lane，見 `core/batch-lock.md`）
- **Trust mode 是模式選擇，不是繞過權限**：sandbox 仍擋 sudo / rm -rf / / chmod 777 /

### 實測過的技術限制

1. **Nested Task 不可用**：subagent frontmatter 即使宣告 `tools: Task`，執行時 Task tool 不可用。錯誤：`Task tool is not available in this environment`。實測 2026-04-24，Claude Code `2.1.119`。
2. **Main session spawn leaf subagent 可行**：實測 main → producer artifact → reviewer verdict JSON，兩個 Task call 真的發生，成本約 $0.25 / 20 秒。
3. **Headless mode 可行**：`claude -p ... --permission-mode=bypassPermissions --output-format=json`。

### 概念參考

- **OneManCompany**（arXiv:2604.22446）——Talent + E²R + Talent Market
- **SLIDERS**（arXiv:2604.22294）——結構化儲存 + 調和管線（結構化儲存路線預留）

