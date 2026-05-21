# Soul Schema — Role / Skill / Codex 檔案格式規範

> 本文件規範三類檔案的格式：Role（agent 人格）、Skill（跨專案方法論）、Codex（專案內領域知識）。所有 framework 出貨的、init 生成的、使用者編輯的此類檔案都必遵循。
>
> Main session 與 init / slash commands 解析這些檔案時，依此 schema 驗證。

---

## 1. 三類檔案總覽

| 類型 | 路徑 | 對應抽象層 | 寫者 | 讀者 |
|---|---|---|---|---|
| **Role** | `.claude/agents/{name}.md` | L1 | Main（透過 slash command）/ 使用者 | Main（spawn 時）/ Subagent（spawn-time prompt） |
| **Skill** | `.claude/skills/{id}/SKILL.md` | L2 | Main（使用者批准後）/ 使用者 | Main / Subagent（spawn-time inline） |
| **Codex** | `.framework/codex/{role}.md` | L2.5 | Main（使用者批准後）/ 使用者 | Main / Subagent（spawn-time inline） |

**通用原則**：
- 純 markdown + YAML frontmatter
- UTF-8 無 BOM、LF 換行
- Frontmatter 必備欄位 + 可選欄位明確區分
- Body 章節有固定順序與標題
- 任何欄位驗證失敗 → init / slash command 拒寫，並提示具體錯誤

---

## 2. Role Schema

### 2.1 Frontmatter（必備 + 可選）

```yaml
---
# 必備
name: code-reviewer                # 必須匹配檔名（不含 .md）
description: 審 code（讀 diff / 跑 test / lint / 比對 spec 範圍）
type: reviewer                     # producer | reviewer
tier: mid                          # cheap | mid | top（解析 .framework/lib/models.yaml）
tools: Read, Bash, Glob, Grep      # 逗號分隔，role/subagent 僅以下值合法：Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch
                                   # Task 排除：Task 是 main 獨有（spawn subagent 用）；role 不能 spawn role（leaf）

# 配對 tag（.framework/pipeline.yaml 用此自動配對 producer ↔ reviewer）
produces: []                       # 此 role 輸出的 artifact 類別（producer 必填、reviewer 留空）
reviews: [code]                    # 此 role 審核的 artifact 類別（reviewer 必填、producer 留空）

# 可選
skills:                            # 此 role spawn 時 inline 載入的 skill
  - global/code-review-checklist
  - global/git-diff-analysis
codex: auto                        # auto | <path> | null（auto = .framework/codex/{name}.md if exists）
memory:
  consume: [code-review, engineering]    # spawn 時 main 從這些 memory 分類挑條餵
  contribute: [code-review]              # suggest_lesson/pattern 預設歸入此類別
worktree: required                 # required | optional | forbidden（worktree 場景需求）
---
```

**欄位驗證**：

| 欄位 | 驗證 |
|---|---|
| `name` | `^[a-z][a-z0-9-]*$`，必須匹配檔名 |
| `description` | 非空，建議 ≤ 80 字 |
| `type` | enum: `producer`, `reviewer` |
| `tier` | enum: `cheap`, `mid`, `top` |
| `tools` | 逗號分隔；每項必為合法 tool 名 |
| `produces` / `reviews` | 字串陣列；type=producer 時 produces 至少一項；type=reviewer 時 reviews 至少一項 |
| `skills` | 字串陣列；每項格式 `<scope>/<id>`，scope ∈ {global, local} |
| `codex` | `auto` / 路徑 / `null` |
| `memory.consume` / `contribute` | 字串陣列 |
| `worktree` | enum: `required`, `optional`, `forbidden` |

**禁止欄位（顯式拒絕）**：
- `model`（用 tier，模型 ID 在 .framework/lib/models.yaml）
- `prompt` / `system_prompt`（人格寫在 body 章節）
- 任何不在上表的欄位（嚴格 schema，避免 typo）

### 2.2 Body 章節（順序固定）

```markdown
## 1. 職責

（一段話描述本 role 是誰、做什麼、不做什麼。建議 ≤ 80 字。）

## 2. Path Boundaries

**Read 白名單**：
- .framework/briefs/{root_id}/sub-briefs/{sub_id}/**
- .framework/memory/lessons/{consume_category}.md
- ...

**Write 白名單**：
- .framework/briefs/{root_id}/sub-briefs/{sub_id}/stages/{stage}/**

**Forbidden**：
- .framework/briefs/{root_id}/_tree.yaml
- .framework/briefs/{root_id}/_manifest.md（main 獨佔）
- 其他 sub-brief 目錄

## 3. Prerequisite Gate

啟動時必檢查（任一 BLOCKING fail → 不執行，回 verdict ambiguity 或 tool_error）：

| 檢查 | 等級 | 失敗動作 |
|---|---|---|
| spec.md 存在 | BLOCKING | 回 ambiguity, missing_input |
| 上游 stage artifact 存在 | BLOCKING | 回 ambiguity |
| pytest 可執行（reviewer 才檢查） | BLOCKING | 回 tool_error |
| ... | | |

## 4. 執行流程

編號步驟，每步動作具體（哪個工具、讀什麼、寫什麼）：

1. 讀 brief.md 與 plan.md 範圍
2. ...
N. emit verdict JSON（schema 見 core/typed-interfaces.md）

## 5. 審核動作清單（reviewer-only，producer 不寫此節）

| 檢查項 | 動作（具體 Bash / 讀檔） | 通過條件 |
|---|---|---|
| 測試 | `cd .framework/worktrees/{sub_id} && pytest` | 全 pass 或 baseline |
| Lint | `ruff check .` | 無新增 error |
| ... | | |

任一 fail → verdict: fail，於 checks[] 陣列填證據。

## 6. 鐵律

- 不直接寫 `.claude/skills/`、`.framework/codex/`、`.framework/memory/lessons/`、`.framework/memory/patterns/`
- 不執行 deny 清單內的 Bash 指令（見 core/trust-modes.md）
- 不對 brief 範圍外的檔案做 Write / Edit
- ...
```

**章節必備性**：

| 章節 | producer | reviewer |
|---|---|---|
| 1. 職責 | ✓ | ✓ |
| 2. Path Boundaries | ✓ | ✓ |
| 3. Prerequisite Gate | ✓ | ✓ |
| 4. 執行流程 | ✓ | ✓ |
| 5. 審核動作清單 | ✗（必略） | ✓ |
| 5.x 對抗式審視 | ✗ | ✓（mandatory；checklist 後跑、單 pass 也跑） |
| 5.y Adversarial 專屬模式 | ✗ | 視 recipe 而定（pipeline.yaml 有 `second_review: true` 的 stage 需求；其他 reviewer 可省） |
| 6. 鐵律 | ✓ | ✓ |

**移除（vs empire v3）**：
- v3 第 6「輸出 JSON Schema」→ 統一引用 `core/typed-interfaces.md`，role 不重抄
- v3 第 7「Handoff Block」→ 取消（10d）

---

## 3. Skill Schema

### 3.1 Frontmatter

```yaml
---
# 必備
name: code-review-checklist        # 必須匹配目錄名
description: 機械化 code review 必查項目（lint / diff scope / 依賴 / hook 繞過 / API 穩定）
scope: global                      # global | local

# 可選
applicable_roles: [code-reviewer, planning-reviewer]   # 建議使用此 skill 的 role 類型
version: 1.0.0
last_updated: 2026-05-06
---
```

**欄位驗證**：

| 欄位 | 驗證 |
|---|---|
| `name` | `^[a-z][a-z0-9-]*$`，必須匹配目錄名 |
| `description` | 非空 |
| `scope` | enum: `global`, `local` |
| `applicable_roles` | 字串陣列（建議性，非強制） |

### 3.2 Body

純知識文檔，無強制章節 schema。建議內容：
- 概念說明
- 步驟 / 流程
- 檢查清單
- 範例
- 反例與陷阱

### 3.3 Skill 目錄結構

```
.claude/skills/code-review-checklist/
├── SKILL.md                       ← 主檔（本 schema 規範）
├── examples/                      ← 可選，範例檔
├── references.md                  ← 可選，外部資料
└── ...                            ← 任意輔助檔
```

**載入機制**：spawn-time inline。Main spawn role 時，把 `SKILL.md` 全文 inline 進 subagent prompt。Role 啟動後可主動 Read 子目錄輔助檔（若需要）。

---

## 4. Codex Schema

### 4.1 Frontmatter

```yaml
---
role: data-analyst                 # 對應 .claude/agents/{role}.md
project: slot-game-q4              # 專案識別（自由命名）
version: 0.3.2                     # SemVer，每次更新遞增
last_updated: 2026-05-06
last_updated_by: 2026-05-06-slot-revenue-q2   # 觸發此次更新的 brief id
---
```

**欄位驗證**：

| 欄位 | 驗證 |
|---|---|
| `role` | 對應的 role name |
| `project` | 非空字串 |
| `version` | SemVer 格式 |
| `last_updated` | YYYY-MM-DD |
| `last_updated_by` | brief id 或 `init` 字串 |

### 4.2 Body 章節（建議結構，非強制）

```markdown
# Codex: {role} @ {project}

## 0. 概述
（一段話描述本 codex 涵蓋哪些主題）

## 1. 領域知識點

### {知識點標題}
- 含義：...
- 範例：...

> Source: {brief id 或 init} / Confirmed: yes|no / Confidence: high|medium|low

## 2. 業務規則
（同上格式）

## 3. 已知陷阱
（同上格式）

## 4. 使用者偏好
（同上格式）

## 5. 變更紀錄

- 2026-05-06: 加入 X 知識點（brief-...）
- ...
```

**Provenance 標註**（SLIDERS 預留接口）：
每個知識點下方都建議有一個 blockquote 行：

```
> Source: <brief id 或 init> / Confirmed: <yes|no> / Confidence: <high|medium|low>
```

意義：
- `Source`：知識點寫入時的來源 brief（追溯用）
- `Confirmed`：使用者是否明確確認（vs 推測）
- `Confidence`：寫入者信心度

**規模上限**：建議單檔 ≤ 500 行。超過時 main 提議切分（多 codex 策略，本框架 v1 起步用一 role 一檔）。

---

## 4.6 路徑佔位符約定

Path Boundaries 與其他位置引用 brief 路徑時，使用以下佔位符：

| 佔位符 | 對應 |
|---|---|
| `{root_id}` | Root brief id（例：`2026-05-06-slot-revenue-q2`） |
| `{sub_id}` | Sub-brief id（例：`2026-05-06-slot-revenue-q2.a`） |
| `{stage}` | Pipeline stage 名稱（例：`engineering`、`research`） |

**禁止**用 `{spec_id}` 作為路徑佔位符（與 typed-interfaces.md 的 `actor.spec_id` JSON 欄位混淆）。

`actor.spec_id`（JSON 欄位）的值在 L0 時等於 `{root_id}`、L1 時等於 `{sub_id}`，但**不**作為路徑模板。

## 5. 命名規則

### 5.1 Role name
- 小寫字母、數字、連字號
- 開頭必為字母
- 例：`code-reviewer`, `data-analyst`, `financial-analyst`
- 反例：`Code-Reviewer`（大寫）、`-engineer`（開頭連字號）、`engineer_2`（底線）

### 5.2 Skill id（即目錄名）
- 同 role name 規則
- 例：`code-review-checklist`, `dcf-valuation`, `pandas-techniques`

### 5.3 Codex 檔名
- 必為 `{role}.md`，role 為對應的 role name

### 5.4 Brief / Sub-brief id
- Brief: `YYYY-MM-DD-{slug}`，slug 為小寫連字號短語
- Sub-brief: `{root_id}.{a|b|c|...}`
- 例：`2026-05-06-slot-revenue-q2`、`2026-05-06-slot-revenue-q2.a`

---

## 6. 驗證點

以下時機必驗證 schema：

| 時機 | 驗證者 | 失敗動作 |
|---|---|---|
| `/framework-init` 生成檔案前 | init/generator | 拒寫，提示錯誤 |
| `/framework-role-add/edit` 寫檔前 | slash command | 拒寫 |
| Main 啟動載入 role 時 | main session | 拒 spawn，提示使用者修正 |
| Main 載入 skill / codex 時 | main session | 略過該 skill / codex，警告但不阻塞 |
| Framework 升級 3-way merge 後 | upgrade tool | 拒合併，提示衝突 |

---

## 7. 範例

### 7.1 Role 範例（producer）

```markdown
---
name: engineer
description: 在指定 worktree 內實作 code（讀 spec / 寫 code / 跑測試）
type: producer
tier: mid
tools: Read, Write, Edit, Bash, Glob, Grep
produces: [code]
reviews: []
skills:
  - global/git-diff-analysis
codex: auto
memory:
  consume: [engineering]
  contribute: [engineering]
worktree: required
---

## 1. 職責

在 main 指定的 worktree 內實作 plan.md 規範的功能。產出：code 變動 + 簡短 commit message + 自評 verdict JSON。

## 2. Path Boundaries

**Read 白名單**：
- .framework/worktrees/brief--{sub_id}/**
- .framework/briefs/{root_id}/sub-briefs/{sub_id}/{plan.md, sub-brief.md}
- .framework/memory/lessons/engineering.md

**Write 白名單**：
- .framework/worktrees/brief--{sub_id}/** （除 .git/）
- .framework/briefs/{root_id}/sub-briefs/{sub_id}/stages/{stage}/{engineer.output.md, engineer.diff-summary.md}（範例：engineer role 對應 dev-team `engineering` stage 的展開）

**Forbidden**：
- 其他 sub-brief 目錄
- main 管理檔（_tree.yaml、_manifest.md）
- .claude/skills/、.framework/codex/、.framework/memory/（任何寫入操作）

## 3. Prerequisite Gate

| 檢查 | 等級 | 失敗 |
|---|---|---|
| .framework/worktrees/brief--{sub_id}/ 存在 | BLOCKING | tool_error |
| plan.md 存在 | BLOCKING | ambiguity |

## 4. 執行流程

1. Read brief.md / plan.md / 上游 artifact
2. 進入 .framework/worktrees/{sub_id}
3. 依 plan 實作（Write / Edit）
4. 跑 plan 指定的測試（Bash）
5. 寫 engineer.output.md（變動摘要）
6. emit verdict JSON

## 6. 鐵律

- 不對 plan.allowed_paths 外的檔案做 Write / Edit
- 不執行 git push / reset --hard / 安裝依賴指令（回 needs_dependency）
- 不繞過 hook（無 --no-verify）
```

### 7.2 Role 範例（reviewer）

（略，結構相同但加第 5 章審核動作清單，type=reviewer）

### 7.3 Skill 範例

```markdown
---
name: git-diff-analysis
description: 讀懂 git diff 並判斷影響範圍 / 風險的方法論
scope: global
applicable_roles: [code-reviewer, engineer]
version: 1.0.0
---

# Git Diff Analysis

## 概念

任何 code review 的起點是讀 diff。讀 diff 不是逐行看，而是分層理解：

1. **檔案層**：哪些檔案被改、新增、刪除？
2. **介面層**：public API 簽章是否變動？
3. **行為層**：邏輯改動是否符合 spec？
4. **副作用層**：是否動到依賴、設定、build 配置？

...
```

### 7.4 Codex 範例

```markdown
---
role: data-analyst
project: slot-game-q4
version: 0.1.0
last_updated: 2026-05-06
last_updated_by: init
---

# Codex: data-analyst @ slot-game-q4

## 0. 概述

本 codex 涵蓋 slot-game-q4 專案的數據定義、業務規則、已知陷阱。

## 1. 領域知識點

### slot_id
- 含義：每個 slot 機台的唯一識別碼。格式 `S{4 digits}`，例 `S1024`。
- 範圍：S0001 - S9999

> Source: init / Confirmed: yes / Confidence: high

### win_rate vs payout_rate
- 含義差別：
  - `win_rate`：玩家獲勝場次比例（贏 / 總場）
  - `payout_rate`：派彩金額比例（派彩 / 投注）
- 重要：兩者不可混用，分析 revenue 時通常看 `payout_rate`

> Source: 2026-04-12-revenue-baseline / Confirmed: yes / Confidence: high

## 2. 業務規則

### Q2 預算重設
- 每年 4 月 1 日 Q2 預算重設，前一日的歷史數據不可跨 Q2 平均

> Source: init / Confirmed: yes / Confidence: medium

## 5. 變更紀錄

- 2026-05-06: 初始版本（init 生成）
```

---

## 8. 給接手 agent 的提醒

- **三類檔案的 frontmatter 都嚴格驗證**：意外欄位拒寫，避免 typo 變正確
- **Body 章節順序固定**：main spawn 時依章節編號塞 prompt，順序錯會解析失敗
- **Skill 載入是 spawn-time inline**：role frontmatter `skills:` 列誰，main 把該 SKILL.md 全文塞進 spawn prompt（不是 Read 路徑指引）
- **Codex 載入同 Skill**：`codex: auto` 時 main 找 `.framework/codex/{role}.md`，存在則 inline、不存在則略過
- **Producer 的 Path Boundaries 必含 worktree 路徑**（若 worktree: required）
- **Reviewer 的 Path Boundaries 必排除 Write**：第 17.1 節權限矩陣強制
- **不允許 Role md 出現 Handoff Block 節**：v3 取消，schema 驗證會拒此節

---

## 9. 相關文件

- `core/control-plane.md`：main session 何時 spawn / 怎麼解析這些檔案
- `core/typed-interfaces.md`：role 輸出的 verdict JSON schema
- `core/trust-modes.md`：tools 欄位允許值受 trust mode 影響
- `.framework/lib/models.yaml`：tier 對應 model ID
