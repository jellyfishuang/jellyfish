# Init Generator — 從 interview 答案產出檔案的邏輯

> 本文件規範 `init/interview.md` Step 5 的具體產檔行為。Main session 在 Step 5 載入此檔依步驟執行。

---

## 1. 輸入

從 interview Step 1-4 收集到的答案：

```yaml
# 來自 Step 1
detected:
  language_stack: go
  has_ci: true
  is_production: true
  recommended_recipe: dev-team
  recommended_trust: standard

# 來自 Step 2
selected_recipe: dev-team
free_form_roles: null    # 若 Step 2 選 free-form
free_form_skills: null

# 來自 Step 3
customizations:
  primary_use: "Go 微服務新功能開發"
  trust_mode: standard
  worktree: true
  tier_preset: all-mid
  language_preferences:
    code: en
    artifact: en
    user_dialog: zh-TW
  test_command: "go test ./..."
  lint_command: "go vet ./..."
  language_stack_detail: "Go 1.22 + Gin"

# 來自 Step 4
codex_drafts:
  planner: "<草稿內容>"
  engineer: "<草稿內容>"
```

---

## 2. 產檔流程

### 2.1 載入 recipe yaml

```
recipe = yaml.load(.framework/lib/recipes/{selected_recipe}.yaml)

if free_form:
  recipe.roles = free_form_roles
  recipe.skills = free_form_skills
  recipe.default_pipeline = build_minimal_pipeline(free_form_roles)
  recipe.memory_categories = derived_from_roles(free_form_roles)
  recipe.bash_extra_allow_template = []
  recipe.init_questions = []
  recipe.codex_bootstrap_prompts = {}
```

**`build_minimal_pipeline(roles)` 邏輯**：
1. 從 free_form_roles 找 producer 與配對 reviewer（依 produces / reviews tag）
2. 若 producer 都無 reviewer 配對 → 提示使用者：「找不到對應 reviewer，pipeline 將無 review。確定？(y/N)」
3. 若 ≥2 producer：再追問「執行順序？(序列 / 並行)」
4. 組裝成 single pipeline `default` with stages，每 stage = 1 producer + 1 reviewer
5. 範例（roles: [engineer, code-reviewer]）—— **必含 pipeline-yaml-template.md §1 全部 top-level 欄位**：
   ```yaml
   framework_version: "0.3.0"
   pipelines:
     default:
       description: free-form 生成
       stages:
         engineering:
           role: engineer
           reviewer: code-reviewer
           depends_on: []
   default: default
   review_rounds_override: null
   bash_extra_allow: []
   triage_hints:
     match_keywords: []
     match_recipes: []
   ```

若 free-form roles 無法配對成合理 pipeline → 中止 init，提示使用者選預設 recipe。

## 2.0 檔案產出策略（Token 效率原則）

**優先順序**（低 token → 高 token）：

| 操作 | Token 成本 | 適用 |
|---|---|---|
| `cp` / `cp -r`（Bash） | 極低（一條指令） | 無客製、純複製檔案 / 目錄 |
| `Edit`（行級替換） | 低（只送 diff） | 客製少數行（frontmatter 覆寫、template 替換 placeholders）|
| `Write` | 高（全文進 context 再寫出） | 不可避免：新內容（codex 草稿 / yaml 配置 / 短模板） |

**鐵律**：
- 凡是「.framework/ 內已有的檔案」要進 `.claude/`：永遠用 **cp 起手**
- 客製後續用 **Edit** 改特定行，不要 **Write** 重寫
- 只有「無原檔可拷」（codex 草稿、.framework/.initialized、settings.local.json、CLAUDE.md/.framework/pipeline.yaml 大量 placeholders 替換）才用 Write
- 即使 Write 也應 < 200 行（CLAUDE.md template 100 行、.framework/pipeline.yaml ~50 行）

### 2.2 寫 `.claude/agents/{role}.md`

對 recipe.roles 每項，**優先 cp 再 Edit**：

```
1. cp .framework/lib/roles/{role}.md .claude/agents/{role}.md
2. 判斷是否需客製：
   - 若 customizations.tier_preset == 'all-mid' AND recipe.role_overrides 無此 role → 不需客製，跳 step 3（純 cp 完成）
   - 否則進 step 3
3. 用 Edit 修改目標檔 frontmatter 的對應行（不重寫全文）：
   - tier 覆寫：Edit "tier: mid" → "tier: <new>"
   - tools 增減：Edit "tools: ..." 行
   - skills 列表覆寫：Edit "skills:" 區塊
   - 注意：Edit 必為 unique match，frontmatter 行通常 unique（受 yaml schema 規範）
4. 不解析 / 不重寫 body 章節（cp 已搬完整 body）
```

**Tier 覆寫對照**：
- `all-mid`：全部 tier=mid → framework/roles/ 預設就是 mid，**無需 Edit**
- `cheap-roles`：reviewer=cheap, producer=mid → 對 reviewer 類 role Edit "tier: mid" → "tier: cheap"
- `custom`：跳過自動，保留 framework default
- `top-orchestrator`：不影響 role tier（main session model 由使用者啟動 Claude Code 時自選；`.framework/.initialized.tier_preset` 紀錄但不改 role md）

### 2.3 寫 `.claude/skills/{skill}/`

對 recipe.skills 每項：

```
cp -r .framework/lib/skills/{skill}/ .claude/skills/{skill}/
```

純 cp，無客製。**永遠不要 Read + Write SKILL.md**（skill 體積最大，數百行；Read + Write 會吃光 token 預算）。

### 2.4 寫 `.framework/codex/{role}.md`

**僅對 type=producer 的 role 寫 codex**。Reviewer 通常無 codex（檢查清單已是工作內容，不需領域知識包）。

若使用者選的 role 中有 reviewer 預期要 codex（罕見），需手動建：將該 reviewer 的 frontmatter `codex: auto` 改為 `codex: null`，避免 spawn 時 main 警告「找不到 codex」。

對 recipe.roles 中 type=producer 的 role：

```
codex_template:
---
role: {role}
project: {derived from repo dir name}
version: 0.1.0
last_updated: {today}
last_updated_by: init
---

# Codex: {role} @ {project}

## 0. 概述

（init 時的 Step 4 訪談摘要）
{customizations.primary_use 一段}
{Step 4 訪談主題分類）

## 1. 領域知識點

{Step 4 訪談中提到的「重要欄位 / 概念意義」}

> Source: init / Confirmed: yes / Confidence: low

## 2. 業務規則

{Step 4 訪談中提到的「業務規則」}

> Source: init / Confirmed: yes / Confidence: low

## 3. 已知陷阱

（框架預設通用陷阱，所有 producer 適用——勿刪）
- **引用既有檔 / symbol 必機械驗證，不靠記憶**：引用「既有檔路徑 / symbol 位置 / 出現數量」時，必 `Glob`/`grep` 對應 source 確認，不憑印象。**multi-repo 尤其注意**：跨 repo 同名檔常並存，**行號內容吻合 ≠ repo 前綴吻合**，必驗完整 `<repo>/<path>`。否定式 claim（「無 X」「不存在 Y」）須 grep 反證才寫；找得到但無 import 寫「存在但 dead code」。

（以下為本專案 init 訪談補充）
{Step 4 訪談中提到的「已知陷阱」}

> Source: init / Confirmed: yes / Confidence: low

## 4. 使用者偏好

{Step 4 訪談中提到的「偏好」}

> Source: init / Confirmed: yes / Confidence: low

## 5. 變更紀錄

- {today}: 初始版本（init 對話生成）
```

寫至 `.framework/codex/{role}.md`。

### 2.5 寫 `.claude/commands/`

```
cp -r .framework/lib/commands/* .claude/commands/
```

不客製。

### 2.6 寫 `CLAUDE.md`

**用 cp + Edit 替換 placeholders**，不重寫全文：

```
1. cp .framework/lib/init/claude-md-template.md ./CLAUDE.md
2. 依 customizations 對每個 {{placeholder}} 用 Edit 替換：
   Edit '{{primary_use}}' → customizations.primary_use
   Edit '{{recipe_name}}' → selected_recipe
   Edit '{{language_stack}}' → customizations.language_stack_detail
   Edit '{{trust_mode}}' → customizations.trust_mode
   Edit '{{worktree_enabled}}' → 'enabled' or 'disabled'
   Edit '{{role_list_with_one_line_description}}' → 動態組成 markdown list
   Edit '{{pipeline_options}}' → 從 recipe.default_pipeline.pipelines 列出
3. 注意：Edit 的 unique match 規則 → 每個 placeholder 在 template 內唯一即可一次替換成功
4. 若 template 內有「## 模板內容」這類非 CLAUDE.md 本體的章節（claude-md-template.md 第 1 節是 meta 說明）→ 用 Edit 移除
```

**若使用者既有 CLAUDE.md**：
- 詢問使用者：(a) 覆寫 (b) 備份為 CLAUDE.md.before-init 後覆寫 (c) 略過 init 此步、保留現有
- (b) 是預設推薦

### 2.7 寫 `.framework/pipeline.yaml`

```
1. template = Read .framework/lib/init/pipeline-yaml-template.md
2. base = recipe.default_pipeline（深拷貝，避免改 recipe 本體）
3. 套用 framework_version（讀 .framework/lib/VERSION）
4. 套用 review_rounds_override: null（用預設）
5. 渲染 bash_extra_allow：
   for line in recipe.bash_extra_allow_template:
     # 替換 {test_command} / {lint_command} 等佔位符
     rendered = template_substitute(line, customizations)
     若 rendered 非空且非純佔位符 → 加入 base.bash_extra_allow
6. 套用 triage_hints（從 recipe.triage_hints 或留空）
7. 寫至 .framework/pipeline.yaml
```

**範例**（dev-team + customizations.test_command="go test ./..."）：

`recipe.bash_extra_allow_template`：
```yaml
- "{test_command}"
- "{lint_command}"
- git diff
- git log --oneline
```

渲染後 `.framework/pipeline.yaml.bash_extra_allow`：
```yaml
- go test ./...
- go vet ./...        # 從 customizations.lint_command
- git diff
- git log --oneline
- git status          # 預設加（reviewer 用）
- git diff --stat     # 預設加
```

預設加入清單（無條件，不論 recipe）：
- `git status`
- `git diff --stat`
- `git diff --name-only`
- `git log main..HEAD --oneline`（若 base branch != main 由 recipe 客製）

### 2.8 寫 `.framework/.initialized`

```yaml
# .framework/.initialized
framework_version: <讀 .framework/lib/VERSION>
created_at: <ISO timestamp>
recipe: <selected_recipe 或 "free-form">
trust_mode: <customizations.trust_mode>
worktree_enabled: <bool>
roles: <列出 .claude/agents/ 內所有 role>
skills: <列出 .claude/skills/ 內所有 skill>
customizations:
  language_stack: <...>
  test_command: <...>
  lint_command: <...>
  language_preferences:
    code: en|zh-TW
    artifact: en|zh-TW
tier_overrides: {}    # role name → cheap|mid|top；只記 sub-agent 的 tier 覆寫
                      # **不記 main 的 tier**：main session model 由使用者啟動 Claude Code 時自選，
                      # framework 無法控制；寫了也無效，反而誤導
# knowledge_base:     # 可選 opt-in；不連接外部 KB 則整段省略（local-only，預設）
#   path: <外部 KB 路徑>   # 例如某 Obsidian vault 的絕對路徑
#   promote: false            # true=brief 收尾經批准的 lessons/patterns/preferences 蒸餾升流 KB
#   recall: false             # true=可用 /framework-recall 唯讀查 KB 參考其他 repo
bash_extra_allow: []
bash_extra_deny: []
```

`knowledge_base` 為可選 opt-in 段：init 時若使用者表示要連外部 KB 才寫入並填 `path` / `promote` / `recall`，否則整段省略（local-only）。行為見 `core/control-plane.md §8.5`、`core/learning-loop.md §8.5/§11.5`。

### 2.9 寫 `.claude/settings.local.json`（含 permissions sync）

依 `core/trust-modes.md` § 5.1 寫入 sync 後的 permissions：

```
1. 取當前 trust_mode（customizations.trust_mode）
2. 從 trust-modes.md § 5.1 樣板組裝 allow list：
   - mode 樣板（strict / standard / sandbox 之一）
   - + recipe.bash_extra_allow_template 渲染後的條目（test_command / lint_command 等）
   - + customizations.bash_extra_allow（使用者 init 時追加）
3. 從 trust-modes.md § 5.1 catastrophic_deny_list 取 deny
   - + customizations.bash_extra_deny
4. 寫 .claude/settings.local.json：
```

```json
{
  "framework_disabled": false,
  "trust_mode": "standard",
  "_framework_managed_permissions": {
    "allow": [
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "...（依 mode 樣板 + recipe 添加）..."
    ],
    "deny": [
      "Bash(sudo:*)",
      "...（catastrophic 列表）..."
    ]
  },
  "permissions": {
    "allow": [
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "..."
    ],
    "deny": [
      "Bash(sudo:*)",
      "..."
    ]
  }
}
```

**Init 階段是首次寫**：
- `_framework_managed_permissions.{allow,deny}` = 計算出的 framework 管理項目
- `permissions.{allow,deny}` = 與 `_framework_managed_permissions` 完全相同（沒使用者加項）

**後續 sync**（trust-set / permissions-sync）依 `core/trust-modes.md` § 5.1 演算法執行，保留 `permissions` 內使用者後加的項目。

**重要**：寫入後 Claude Code 須**重啟 session** 才會載入新 permissions（同 agent 列表）。Init 結束的 Step 6 「強制重啟提示」涵蓋此需求。

### 2.10 建 .framework/memory/ 結構

```
寫 .framework/memory/MEMORY.md（索引模板）
寫 .framework/memory/architecture.md（空模板，使用者填）
寫 .framework/memory/preferences.md（空模板）
建 .framework/memory/lessons/         （空目錄，category .md 檔由 learning loop 寫入時生成）
建 .framework/memory/lessons/escalations/   （目錄；放詳細事件檔）
建 .framework/memory/patterns/        （空目錄，同上）
建 .framework/memory/sessions/        （空目錄，brief 完成時 main 寫 {brief_id}.md）
```

**重要**：`memory/lessons/{category}.md` 與 `memory/patterns/{category}.md` 是 **檔案**（learning-loop §8.1 / §8.2 schema），不是目錄。
- ❌ 不要建 `memory/lessons/planning/`、`memory/lessons/engineering/` 等子目錄
- ✓ 建空 `memory/lessons/` 目錄；首次寫 lesson 時由 learning loop 建 `memory/lessons/planning.md` 等檔
- ✓ `memory/lessons/escalations/` 例外——它是目錄，內含 `{file}.md` 詳細事件檔

`.framework/memory/MEMORY.md` 模板：

```markdown
# Memory Index

> 本檔是 memory 索引。Main session 啟動時會載入。
>
> 詳細 lessons / patterns 不全載入，main 在 Explore Step 2 按需 grep。

## 全域檔（每 brief 啟動時讀）

- [architecture.md](architecture.md) — 專案技術事實
- [preferences.md](preferences.md) — 使用者偏好

## Lessons（行為糾正）

依分類存放，**每個 category 是一個 .md 檔**（多條 lesson 在同一檔內以 bullet list 呈現）：
- `lessons/{category}.md` — 各類 lessons 條目（首次寫入時由 learning loop 建檔）
- `lessons/escalations/` — 目錄；詳細事件檔（每事件一檔）

預期 categories（依 recipe.memory_categories）：
- `lessons/planning.md`
- `lessons/engineering.md`
- `lessons/code-review.md`

## Patterns（成功 playbook）

依分類，**每個 category 一個 .md 檔**：
- `patterns/planning.md`
- `patterns/engineering.md`
- `patterns/code-review.md`

## Sessions

- sessions/{brief_id}.md — brief 摘要
```

`.framework/memory/architecture.md` 模板：

```markdown
# Architecture

> 本專案的技術事實。請在 init 後填寫。Main session 在 Explore 時讀此檔。

## 技術棧

{customizations.language_stack_detail}

## 系統架構

（一段話：單體 / 微服務 / 函式庫；主要服務組成；資料流向）

## 模組組成

| 模組 | 路徑 | 職責 |
|---|---|---|
| ... | ... | ... |

## 不可動的原則

- 例：所有 API 必走 middleware/auth
- 例：DB schema 變更必經 migration

## 已知瓶頸 / 痛點

- ...
```

`.framework/memory/preferences.md` 模板：

```markdown
# User Preferences

> 跨 brief 的使用者偏好。Main session 在 Explore 與 spawn role 時參考。

## 對話風格

- （從 customizations 自動填一些）

## 程式風格

- （依 language_preferences 自動填）

## Code review 偏好

- ...

## 報告 / 文件偏好

- ...
```

### 2.11 建 .framework/briefs/ 結構

```
mkdir .framework/briefs/
mkdir .framework/briefs/inbox/
mkdir .framework/briefs/_archive/
mkdir .framework/briefs/_active/     # lock registry（multi-lane，batch-lock.md §2）
```

### 2.12 建 worktrees/（若啟用）

```
mkdir .framework/worktrees/
echo ".framework/worktrees/" >> .gitignore   # 若 .gitignore 存在且未列
```

---

## 3. AGENTS.md 處理

若 repo 已有 AGENTS.md → 不覆寫。
若沒有 → 寫一行指標：

```markdown
# AGENTS.md

This project uses a multi-agent framework. See [CLAUDE.md](CLAUDE.md) for details.
```

---

## 4. .gitignore 處理

確保以下項在 .gitignore（若 .gitignore 存在）：

```
.framework/.initialized      # 個人 init 紀錄不進 git
.claude/settings.local.json         # 個人設定不進 git
.framework/worktrees/                         # 若啟用
.framework/briefs/_archive/                    # 歷史歸檔太大
.framework/briefs/_active/                     # lock registry（執行時狀態）
```

**不**進 .gitignore（這些進 git）：
- `.claude/agents/*.md`
- `.claude/skills/`
- `.framework/codex/*.md`
- `.claude/commands/`
- `CLAUDE.md`、`.framework/pipeline.yaml`
- `.framework/memory/`（讓團隊共享 lessons / patterns）
- `.framework/briefs/{active brief 目錄}`（執行中可進 git；完成後歸檔）

若沒 .gitignore → 不主動建（避免污染 repo）。

---

## 5. 失敗處理

| 失敗 | 處理 |
|---|---|
| Recipe yaml 格式錯誤 | 顯示錯誤行、退出 init |
| Role md frontmatter schema 違規 | 顯示錯誤、跳過該 role、警告 |
| 寫檔權限不足 | 顯示具體路徑、回滾已寫的檔、退出 |
| 同名檔已存在（非 reset） | 提示使用者、提供 (skip / overwrite / abort) 選項 |

---

## 6. 給接手 agent 的提醒

- **產檔順序很重要**：先 .claude/agents → skills → codex → CLAUDE.md → .framework/pipeline.yaml → memory → briefs
- **不在這層做語意檢查**：產檔正確性由 soul-schema.md / 各 schema 文件規範
- **codex 草稿是 v0.1.0**：明確標 confidence: low，main 在後續 Explore 時會視情況提議修正
- **.framework/memory/ 結構是空的**：除了 MEMORY.md / architecture.md / preferences.md 三個有模板，其他子目錄是空的
- **不寫外部 KB**：framework init 預設與外部 KB 解耦（連線為 opt-in）
- **不執行 git 操作**：init 不 commit、不 push、不改 git config
