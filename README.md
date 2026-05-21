# Multi-Agent Team Framework: Jellyfish

> 一套可攜、純文件（Markdown + YAML/JSON、零 shell script）的 multi-agent 編排框架。
> Clone 進任何 Claude Code 專案、跑一次 `/framework-init` 即可使用。

**版本：0.2.0（alpha）** · 詳見 [`CHANGELOG.md`](CHANGELOG.md)

---

## 這是什麼

讓單一 Claude Code 的 **main session 扮演 control plane（編排者）**，依任務 spawn 一組各司其職的 role subagent，跑一條 **Explore → Execute → Review（E²R）** 流程，並用**機械化的 review gate** 與**使用者把關**控制品質。

核心特性：

- **Control Plane Pattern**：main session 是唯一編排者，所有 subagent 皆為 leaf（不再往下 spawn），規避 nested-Task 限制。
- **純文件**：框架本體只有 `.md` + `.yaml` / `.json`，無任何可執行程式，可直接版控、審閱、攜帶。
- **可組合**：Role / Skill / Codex 三層拆解，依專案自由組合，不綁死整包 archetype。
- **機械化審核**：reviewer 強制跑 `git diff` / test / lint / 一致性檢查等動作清單，任一失敗即 `verdict: fail`。
- **學習迴圈**：brief 完成自動寫 session 摘要，並在使用者批准下沉澱 lesson / pattern；可 opt-in 把蒸餾後的跨 repo 知識升流外部知識庫（見 `/framework-recall`）。
- **防幻覺放大**：producer 對「未來會影響執行的東西」（lesson / pattern / codex / skill）只能「提議」，不能直寫；一律經 main + 使用者批准。

---

## 核心概念

| 概念 | 說明 |
|---|---|
| **E²R（受限 2 層樹）** | L0 = 使用者開的 brief；L1 = 切出的 sub-brief。**不允許 L2**——避免 main context 爆掉、使用者跟不上、終止性難保證。 |
| **四層抽象** | **Role**（角色人格＋職責＋工具範圍）/ **Skill**（跨專案重用的方法論）/ **Codex**（專案專屬領域知識）/ **Directive**（單次任務的追加指示）。 |
| **Recipe** | 「建議的 role + skill + pipeline 組合」，是落地起點而非強制鎖定，複製後即為使用者所有。 |
| **Typed Verdict** | producer / reviewer 共用一份寬鬆 JSON schema，以 7 種 verdict（pass / fail / ambiguity / needs_decomposition / needs_dependency / tool_error / partial）驅動 main 的下一步。 |
| **Trust Mode** | `strict` / `standard` / `sandbox` 三檔，決定 Bash 白名單寬嚴與依賴安裝策略。 |
| **Memory** | `lessons`（行為糾正）/ `patterns`（成功 playbook）/ `sessions`（brief 歷史）/ `architecture`（專案事實）/ `preferences`（跨 brief 偏好）。 |

設計受 multi-agent 組織研究啟發：可攜身份「Talent」與 Explore-Execute-Review 遞迴探索取自 **OneManCompany**（arXiv:2604.22446）；結構化記憶儲存的概念取自 **SLIDERS**（arXiv:2604.22294，目前暫緩、僅預留 frontmatter 接口）。框架在此基礎上刻意收斂為 Claude-only、單 active brief、檔案優先的形態。

---

## 架構總覽

### 分層

```
┌──────────────────────────────────────────────────────────────┐
│ Framework lib（出貨層，升級時 overwrite）                      │
│  core/     抽象規範：control plane / E²R / verdict / trust …   │
│  roles/    role template 庫                                    │
│  skills/   skill template 庫                                   │
│  recipes/  建議組合（非強制）                                  │
│  init/     落地時呼叫一次的 interview / generator / 模板       │
│  commands/ slash command 定義                                  │
├══════════════════════════════════════════════════════════════┤
│ 落地專案層（init 產生，使用者隨時改）                          │
│  .claude/agents/{role}.md         ← 本專案 role                │
│  .claude/skills/{skill}/SKILL.md  ← 本專案 skill               │
│  .claude/commands/                ← 從 lib 複製                │
│  .framework/codex/{role}.md       ← 該 role 的專案 codex        │
│  .framework/pipeline.yaml         ← 本專案 pipeline (DAG)       │
│  .framework/memory/               ← 本專案記憶                  │
│  .framework/briefs/               ← brief 工作目錄              │
│  CLAUDE.md                        ← 本專案指示（含啟用判斷）     │
└──────────────────────────────────────────────────────────────┘
```

### 任務流（E²R）

```
使用者：/brief-new "<需求描述>"
  ↓
Main：偵測 active brief（已有則拒）→ 建 brief
  ↓
[Explore L0]
  1. Roster 決策（main 選 role，顯示給使用者可改）
  2. 情報蒐集（讀 codex / memory / repo → intel-pack）
  3. Grill 訪談（main 主持，單題制，cap 20 題）
  4. Plan 草稿（spawn planner）
  5. Plan 審核（spawn planning-reviewer）
  6. 使用者批准（/brief-approve）
  ↓
[Execute L0 → 切 sub-briefs L1]
  for sub_brief in plan.sub_briefs:        # 無依賴者並行
    for stage in pipeline.stages:          # 依 DAG 排程
      main spawn producer → artifact
      main spawn reviewer → verdict        # 1-2 輪同 role / 3+ 輪回 Explore
    → sub_brief/final.md
  ↓
[Review L0 holistic]  main 讀各 final.md，檢查跨 sub-brief 一致性（僅靜態驗證）
  ↓
[Amendment 期 — 可選]  使用者目視 review 後的輕量修訂入口
  ↓
[學習迴圈]  寫 session 摘要 → 詢問品質評分 → 批准後沉澱 lesson / pattern
  ↓
歸檔 + 解鎖
```

---

## Repository Layout

```
.
├── lib/
│   ├── core/            # 不可改抽象層
│   │   ├── control-plane.md      # main session 行為規範
│   │   ├── e2r-tree.md           # _tree.yaml manifest 規範
│   │   ├── review-loop.md        # review 輪次與回退規則
│   │   ├── typed-interfaces.md   # verdict / producer output schema
│   │   ├── batch-lock.md         # _active.yaml 語意
│   │   ├── clarification.md      # grill-me 訪談規則
│   │   ├── trust-modes.md        # 三檔信任模式 + permissions sync
│   │   ├── soul-schema.md        # Role / Skill / Codex schema
│   │   ├── escalation-rules.md   # 高風險動作升級清單
│   │   ├── learning-loop.md      # brief 結束學習迴圈
│   │   └── amendment.md          # L0 review 後的輕量修訂層
│   ├── roles/           # role template 庫
│   ├── skills/          # skill template 庫
│   ├── recipes/         # 建議組合（*.yaml）
│   ├── init/            # interview / generator / claude-md / pipeline 模板
│   ├── commands/        # slash command 定義
│   ├── models.yaml      # tier → model ID 對照
│   ├── VERSION          # 框架版本號（single source of truth）
│   └── design-summary.md # 完整設計總覽（深入細節入口）
├── CHANGELOG.md
└── README.md            # 本檔
```

> `lib/` 是「出貨層」，升級時整包 overwrite；專案的客製與資料都在落地專案的 `.framework/`（非 `lib/`）與 `.claude/` 內，升級時保留。

---

## 落地（Getting Started）

### 前置

- Claude Code CLI
- 你的專案目錄（任何語言皆可；framework 與語言無關）

### 1. 把框架加入專案

把本 repo 的 `lib/` 放到專案的 `.framework/lib/`（擇一）：

```
your-project/
└── .framework/
    └── lib/      ← clone / git submodule / 直接複製本 repo 的 lib/
```

三種方式取捨：

- **複製**：最簡單，升級時重新覆蓋 `lib/`。
- **git submodule**：版本可追，`git submodule update` 升級。
- **symlink**：多專案共用同一份 lib。

### 2. 初始化

在專案根目錄啟動 Claude Code，執行：

```
/framework-init
```

這會跑一段對話式設定：

1. **Repo 偵測** — 掃語言指標 / 配置檔，推薦對應 recipe。
2. **Recipe 選擇** — 採用推薦、從內建 recipe 選一個，或 free-form 手挑 role + skill。
3. **客製問題（4–6 題）** — 主要使用情境、tier 偏好、trust mode、worktree、Bash 白名單追加、語言偏好。
4. **Codex 草稿** — 對每個 role 輕訪談並掃 repo，產出初版專案領域知識。
5. **檔案生成** — 產出 `.claude/agents/`、`.claude/skills/`、`.claude/commands/`、`.framework/codex/`、`CLAUDE.md`、`.framework/pipeline.yaml`、`.framework/memory/`、`.framework/briefs/`、`.framework/.initialized`。

### 3. 重啟 session（必要）

agent 與 slash command 清單在 session 啟動時鎖定。**init 後必須重啟 Claude Code**，否則跑 brief 會失敗。

### 4. 跑第一個 brief

```
/brief-new "<描述你的需求>"
```

接著照 Explore 流程：確認 roster → 回答訪談 → `/brief-approve` 批准 plan → 框架自動執行並回報。

### init 產生什麼（落地專案結構）

```
your-project/
├── .framework/
│   ├── lib/              # 出貨層（你放進來的）
│   ├── codex/{role}.md   # 各 role 的專案領域知識
│   ├── memory/           # MEMORY.md / architecture / preferences / lessons / patterns / sessions
│   ├── briefs/           # _active.yaml / inbox / _archive / {brief_id}/
│   ├── pipeline.yaml     # stage DAG
│   └── .initialized      # init 紀錄（recipe / customizations / framework_version）
├── .claude/
│   ├── agents/{role}.md          # 從 lib/roles 複製並客製
│   ├── skills/{skill}/SKILL.md   # 從 lib/skills 複製
│   ├── commands/                 # 從 lib/commands 複製
│   └── settings.local.json       # opt-out / trust mode / permissions
└── CLAUDE.md                     # 專案指示 + 啟用判斷
```

---

## 啟用機制與 Opt-out

`CLAUDE.md` 開頭做四層啟用判斷，**全滿足才載入框架行為**，任一不滿足即退回一般 Claude Code：

1. 環境變數 `FRAMEWORK_DISABLED` 未設為 `1`
2. `.claude/settings.local.json` 內 `framework_disabled` 不為 `true`
3. `.framework/.initialized` 存在
4. `.framework/lib/core/control-plane.md` 存在

同專案其他人想停用：

- 一次性：`FRAMEWORK_DISABLED=1`（env 優先）
- 長期個人：`settings.local.json` 加 `framework_disabled: true`（不進 git）

---

## 日常使用

### Slash Commands

**`/brief`（高頻）**

| 指令 | 用途 |
|---|---|
| `/brief-new` | 開新 brief（短訪談） |
| `/brief-status` | active brief 進度 + 近期完成 |
| `/brief-approve` | 批准當前 plan（L0 gate） |
| `/brief-amend <sub_id> "..."` | 對已完成 sub-brief 做輕量修訂 |
| `/brief-cancel` | 取消當前 active brief |
| `/brief-reopen <id>` | 重啟已歸檔 brief |
| `/brief-import <url>` | 從 GitHub Issue 匯入 |

**`/framework`（系統管理，少用）**

| 指令 | 用途 |
|---|---|
| `/framework-init` | 初始化（`--reset` 可全重來） |
| `/framework-status` | 顯示啟用狀態 / recipe / roles / active brief |
| `/framework-role-list` · `-add` · `-edit` · `-remove` | 管理 role |
| `/framework-recipe-list` | 列內建 recipes |
| `/framework-pipeline-edit` | 改 pipeline.yaml |
| `/framework-trust-set <mode>` | 切 trust mode（含 permissions sync） |
| `/framework-permissions-sync` | 強制 re-sync 權限 |
| `/framework-recover` · `/framework-unlock` | 中斷恢復 / 強制清 `_active.yaml` |
| `/framework-learn` | 補處理歸檔 brief 的學習沉澱（不需另開 brief） |
| `/framework-recall <主題>` | 唯讀查外部 KB 參考其他 repo（需 opt-in 連接 KB） |

### 批准 Gate

- **只有 L0 plan 需使用者批准**（`/brief-approve`）。
- Sub-brief 自動跑；但涉及高風險動作（動依賴 / 動 schema / 跨模組大改）會強制升級使用者（清單見 `lib/core/escalation-rules.md`）。

---

## 設定

### Recipe（內建建議組合）

| Recipe | 典型場景 | Roles |
|---|---|---|
| **dev-team** | 軟體開發（規劃 + 工程 + 審查） | planner, planning-reviewer, engineer, code-reviewer |
| **research-team** | 研究調查 | researcher, source-quality-reviewer, analyst, reasoning-reviewer |
| **writing-team** | 文件 / 報告產出 | writer, editor |
| **finance-advisory** | 金融顧問（資料 → 分析 → 報告） | researcher, source-quality-reviewer, financial-analyst, reasoning-reviewer, writer, editor |
| **data-analytics** | 資料分析 | data-analyst, analysis-reviewer, writer |
| **general-assistant** | 通用 / 外部觸發助理 | assistant, double-checker |

Recipe 是起點不是鎖定——複製進專案後可任意增刪 role、改 pipeline。

### Trust Modes

| 模式 | 適用 | Bash 哲學 |
|---|---|---|
| **strict** | 生產 / 共用 / 不熟環境 | 最小白名單；嚴格 needs_dependency |
| **standard** | 個人熟悉 repo（預設） | 合理白名單 |
| **sandbox** | 拋棄式 VM / 空白專案 | 大幅放寬，僅擋災難級（`sudo` / `rm -rf /` / `chmod 777 /` 等） |

切換：`/framework-trust-set <mode>`。

### Model Tier

`lib/models.yaml` 把 `cheap` / `mid` / `top` 對應到實際 model ID；role frontmatter 宣告 `tier`。覆寫順序：recipe default → init 覆寫 → 手改 frontmatter。

### Worktree

`dev-team` recipe 預設每 sub-brief 一個 git worktree；其他 recipe 預設不啟用。失敗 / 取消時保留 worktree 並留標記檔，交由使用者處置。

---

## 深入

| 想了解 | 讀 |
|---|---|
| 完整設計總覽 | [`lib/design-summary.md`](lib/design-summary.md) |
| main session 行為 | `lib/core/control-plane.md` |
| Verdict JSON schema | `lib/core/typed-interfaces.md` |
| Tree 結構與遍歷 | `lib/core/e2r-tree.md` |
| Review 輪次規則 | `lib/core/review-loop.md` |
| Role / Skill / Codex schema | `lib/core/soul-schema.md` |
| Trust modes / Bash 白名單 | `lib/core/trust-modes.md` |
| 學習迴圈 | `lib/core/learning-loop.md` |

---

## 設計原則

1. **Framework = 模式 + 工具，不是角色本身。** 框架規範抽象（control plane、E²R、verdict schema），不規範「engineer 是誰、做什麼」。
2. **角色是落地時組合的可攜實體。** Role / Skill / Codex 都在專案內、可被使用者直接編輯；recipe 只是建議起點。
3. **機械化審核 + 使用者把關。** reviewer 跑可驗證的動作清單；producer 對未來生效的東西只能提議，main 與使用者是 gatekeeper。

### 刻意的取捨（不支援）

- Nested Task / subagent 再 spawn subagent（技術限制：leaf subagent 內 Task tool 不可用）
- 多 LLM family（Claude only）
- 可執行 shell script（純文件）
- Producer 自主裝依賴 / 自主寫 skill / codex
- 框架預定義固定整包 archetype
- 多 process / 多 session 同時跑（「multi-agent」= 單一 main session 內 spawn 多 subagent，單 active brief）

---

## 參考

框架的核心概念汲取自以下研究：

- **OneManCompany**（arXiv:2604.22446）— Talent（可攜身份）、E²R（Explore-Execute-Review）、Talent Market。本框架的角色組合與遞迴任務流即源於此。
- **SLIDERS**（arXiv:2604.22294）— 結構化記憶儲存與調和管線。本框架暫緩此路線，但在 memory 條目與 codex 知識點預留 frontmatter 接口，供日後升級結構化儲存。

---

## 狀態

Alpha（0.2.0）。core 抽象與 dev-team recipe 已在實戰中迭代驗證；其餘 recipe 與 edge case 處理持續完善中。歡迎依自身場景 fork 與調整。
