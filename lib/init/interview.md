# Init Interview — `/framework-init` 對話腳本

> 本文件規範 `/framework-init` 的對話流程。Main session 載入此檔依步驟執行，最終呼叫 `init/generator.md` 寫檔。

---

## 0. 觸發

| 來源 | 行為 |
|---|---|
| 使用者執行 `/framework-init` | 走完整 6 步 |
| 使用者執行 `/framework-init --reset` | 先備份既有 `.framework/codex/` 到 `.framework/codex/.backup-{timestamp}/`，再走完整 6 步 |
| Main 偵測 `.framework/.initialized` 不存在且使用者未拒 | 提示「偵測到 framework 未初始化，要 init 嗎？(y/n/later)」，y → 走完整 6 步 |

若 `.framework/.initialized` 已存在且非 `--reset` → 顯示「已 init 過。要 `/framework-init --reset` 重來，或用 `/framework-role-add` 等指令調整？」

---

## Step 1. Repo 偵測（main 自動，使用者只看結果）

### 動作

```
1. Read README.md（若存在）
2. Glob 偵測技術棧：
   - go.mod, *.go → Go 專案
   - pyproject.toml, *.py → Python 專案
   - package.json, *.ts, *.tsx → JS/TS 專案
   - Cargo.toml, *.rs → Rust 專案
   - 大量 *.csv, *.ipynb → 數據分析
   - 大量 *.md, *.pdf, 無程式碼 → 研究 / 寫作
3. Glob 偵測情境訊號：
   - .github/workflows/ → CI 存在 → 推薦 trust standard
   - Dockerfile.production / deploy/ → production repo → 推薦 trust strict
   - .devcontainer/ / Dockerfile.dev / dir 名含 sandbox/scratch/playground → 推薦 trust sandbox
   - 空 repo（≤3 檔） → 推薦 trust sandbox
4. 偵測 Recipe 候選（用啟發規則）：
   - go.mod / Cargo.toml / pyproject.toml + 真實 src/ → dev-team
   - 大量 .csv/.ipynb → data-analytics
   - 大量 .md/.pdf 無程式碼 → research-team 或 writing-team
   - README 提到 financial / investment → finance-advisory
   - README 提到 analysis / report → research-team
   - 偵測不到明確訊號 → general-assistant
```

### 顯示

```
偵測到的特徵：
  - 主要語言：Go
  - 有 CI 配置（.github/workflows/）
  - 有 Dockerfile.production
  - README 提及 microservice、deployment

推薦：
  - Recipe: dev-team
  - Trust mode: standard

進入 Step 2 確認...
```

---

## Step 2. Recipe 選擇（單題）

```
請選擇 recipe（會決定本專案用哪些 role + skill + pipeline）：

  (1) 採用推薦 [dev-team]
  (2) 從清單選一個：
      - dev-team           開發 / 寫 code
      - research-team      研究 / 分析
      - writing-team       寫作 / 編輯
      - finance-advisory   金融顧問（research + analysis + writing 整合）
      - data-analytics     數據分析
      - general-assistant  通用助理
  (3) Free-form：手選 role + skill 組合（進階）

預設：(1)
```

收答案後：
- (1) → 載入 `recipes/{recommendation}.yaml`
- (2) → 等使用者選 → 載入對應 yaml
- (3) → 進入 free-form 子對話：
  ```
  請列出要啟用的 role（從 .framework/lib/roles/ 內選，逗號分隔）：
  > engineer, code-reviewer, planner

  請列出要啟用的 skill（從 .framework/lib/skills/ 內選，逗號分隔；可空）：
  > code-review-checklist, git-diff-analysis
  ```

---

## Step 3. 客製問題（4-6 題，依 recipe）

### 共通題

```
Q1. 主要使用情境？（一句話描述，會寫進 CLAUDE.md）
範例：「為金融顧問做股票深度分析報告」、「Go 微服務新功能開發」
> ____

Q2. Trust mode？
  (a) strict     生產 repo / 共用 / 不熟環境
  (b) standard   個人熟悉 repo（**推薦**：{detected_default}）
  (c) sandbox    拋棄式 VM / 空白專案
> ____

Q3. Worktree 啟用？
  (y) 啟用，每 sub-brief 一個 worktree
  (n) 不啟用
推薦：{recipe.default_worktree}
> ____

Q4. Tier 偏好？
  (a) all-mid           全部 sonnet（預設）
  (b) cheap-roles       reviewer 用 haiku、producer 用 sonnet（省成本）
  (c) top-orchestrator  main 用 opus（最佳編排品質，使用者自己 Claude Code 啟動時選）
  (d) custom            手動覆寫個別 role tier
> ____

Q5. 偏好語言？
  程式 / 注解：(a) 英文 (b) 繁中
  artifact（plan / 報告）：(a) 英文 (b) 繁中
  使用者對話：永遠繁中
> ____
```

### Recipe 專屬追加題

從 `recipes/{name}.yaml` 的 `init_questions` 欄位讀取，逐題提問。

範例（dev-team）：

```
Q6. 本專案的測試指令？（會加進 reviewer Bash 白名單）
範例：pytest / go test ./... / npm test / cargo test
> ____

Q7. 本專案的 lint 指令？
範例：ruff check . / go vet ./... / eslint .
> ____

Q8. 主要技術棧？（會寫進 engineer / planner 的 codex）
範例：Python 3.12 + FastAPI / Go 1.22 + Gin
> ____
```

---

## Step 4. Codex 草稿生成（每個 role 一輪輕訪談）

對 recipe 列出的每個 producer role，執行：

```
[Role: data-analyst]

我會為這個 role 生成 codex 草稿（領域知識包）。
Main 會自動掃 repo 補充事實，但有些東西需要你直接告訴我。

Q. 這個 role 在這個 repo 應該知道哪些事？
   舉幾個你覺得這 role 不熟就會踩坑的點。可以是：
   - 重要欄位 / 概念的意義
   - 業務規則
   - 已知陷阱
   - 你的偏好

可空（codex 之後可隨時編輯）。
> ____

[Main 同時跑：]
- Glob *.csv 看有哪些資料表
- Read 主要 .py 檔的 docstring
- Grep README 找關鍵概念
（彙整成補充清單）

最終 codex 草稿（confidence: low，使用者後續修正）：
[顯示草稿]

要採用嗎？(y/edit/skip)
```

**注意**：reviewer role 通常不需 codex 訪談（他們的工作是機械檢查，不是領域知識）；但若 reviewer 有 codex 需求，仍可跑此流程。

---

## Step 5. 檔案生成（main 自動，無使用者互動）

呼叫 `init/generator.md` 流程，依 Step 1-4 答案產出：

```
.claude/agents/{role}.md × N           ← 從 .framework/lib/roles/ 複製，frontmatter 套客製值
.claude/skills/{skill}/SKILL.md × M    ← 從 .framework/lib/skills/ 複製
.framework/codex/{role}.md × N            ← Step 4 草稿
.claude/commands/                       ← 從 .framework/lib/commands/ 複製
.framework/.initialized          ← 客製值 + framework_version + recipe + timestamp
.claude/settings.local.json             ← trust_mode / opt-out 預設
CLAUDE.md                               ← 從 init/claude-md-template.md 套客製
.framework/pipeline.yaml                           ← 從 recipe.default_pipeline + 客製
.framework/memory/MEMORY.md                        ← 索引模板
.framework/memory/architecture.md                  ← 空模板（使用者填）
.framework/memory/preferences.md                   ← 空模板
.framework/memory/lessons/                         ← 空目錄；{category}.md 由 learning loop 寫入時生成
.framework/memory/lessons/escalations/             ← 空目錄；詳細事件檔
.framework/memory/patterns/                        ← 空目錄；同上
.framework/memory/sessions/                        ← 空目錄；brief 完成時 {brief_id}.md 寫入
.framework/briefs/                                 ← 空目錄
.framework/briefs/inbox/                           ← 空目錄（C 專案 Telegram 用）
.framework/briefs/_archive/                        ← 空目錄
.framework/worktrees/                             ← 若 worktree=y
```

生成過程顯示進度：

```
✓ 寫 .claude/agents/planner.md
✓ 寫 .claude/agents/planning-reviewer.md
✓ 寫 .claude/agents/engineer.md
✓ 寫 .claude/agents/code-reviewer.md
✓ 複製 skill code-review-checklist
✓ 複製 skill git-diff-analysis
✓ 寫 .framework/codex/planner.md (v0.1.0)
✓ 寫 .framework/codex/engineer.md (v0.1.0)
✓ 寫 CLAUDE.md
✓ 寫 .framework/pipeline.yaml
✓ 寫 memory 結構
✓ 寫 .framework/.initialized

完成。共產生 N 檔。
```

---

## Step 6. 摘要 + 強制重啟提示

```
Framework 初始化完成。

設定總覽：
- Recipe: dev-team
- Roles: planner, planning-reviewer, engineer, code-reviewer
- Skills: code-review-checklist, git-diff-analysis
- Trust mode: standard
- Worktree: enabled
- 主要技術棧：Go 1.22 + Gin

⚠️ 重要：必須重啟 Claude Code session 才能使用 framework

原因：Claude Code 在 session 啟動時鎖定 .claude/agents/ 與 .claude/commands/ 列表，
本次 init 寫入的 agent / slash command 必須等 session 重啟才會被認得。
若不重啟直接跑 /brief-new，spawn role 會失敗（Agent type not found）。

請現在退出 Claude Code session 並重啟。

重啟後可用：
  /framework-status     確認設定
  /framework-role-list  查看 role 列表
  /brief-new            開始第一個 brief
```

**規範**：
- Step 6 不提供「現在試跑 dummy brief」的選項（spawn 一定失敗，徒增混淆）
- Main 不應在 init 完成後嘗試任何 spawn（同樣會失敗）
- 即使使用者問「現在能不能直接跑 brief」，main 必明確答「不能，請先重啟」

---

## 異常處理

| 狀況 | 處理 |
|---|---|
| 偵測時找不到 README、目錄為空 | 跳到 Step 2 直接給選單，不推薦 |
| 使用者答非預期值（例 Step 2 答 "x"） | 重問該題，最多 3 次 → 強制走預設 |
| Step 4 codex 草稿生成失敗（例：role 不在 .framework/lib/roles/） | 警告但繼續，該 role 的 codex 開白卷 |
| Step 5 寫檔失敗（例：權限問題） | 顯示錯誤、回滾已寫的檔，提示使用者檢查 |
| 已 init 過但使用者執行 `/framework-init`（非 reset） | 提示「要 reset 還是用 role/recipe 子指令？」，不自動 reset |

---

## 給接手 agent 的提醒

- **Step 1 偵測寬鬆，Step 2-3 確認嚴格**：偵測錯了使用者會在 Step 2 改正
- **不要連續問 ≥3 個複雜題**：使用者疲勞，建議用「一題一答」節奏
- **預設值要可空**：使用者按 enter 直接用預設
- **Step 4 codex 草稿是「v0.1.0 confidence: low」**：寫進 codex frontmatter，提醒使用者後續會優化
- **Step 5 全自動**：不要中間問問題（避免打斷流程）；錯誤就 throw、回滾
- **Step 6 強制重啟提示是必要**：不可改為試跑邀請；agent / slash command 列表須 session 重啟才生效，spawn 一定失敗
