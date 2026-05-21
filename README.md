# Multi-Agent Team Framework for Claude Code

> 一套可攜、純文件（Markdown + YAML / JSON、零 shell script）的 multi-agent 編排框架。
> Clone 進任何 Claude Code 專案、跑一次 `/framework-init` 即可使用。

**版本：0.1.0（起點基準）** · 詳見 [`CHANGELOG.md`](CHANGELOG.md)

---

## 這是什麼

讓單一 Claude Code 的 **main session 扮演 control plane（編排者）**，依任務 spawn 一組各司其職的 role subagent，跑一條 **Explore → Execute → Review（E²R）** 流程，並用**機械化的 review gate** 與**使用者把關**控制品質。

核心特性：

- **Control Plane Pattern**：main session 是唯一編排者，所有 subagent 皆為 leaf（不再往下 spawn），規避 nested-Task 限制。
- **純文件**：框架本體只有 `.md` + `.yaml` / `.json`，無任何可執行程式，可直接版控、審閱、攜帶。
- **可組合**：Role / Skill / Codex 三層拆解，依專案自由組合。
- **機械化審核**：reviewer 強制跑 `git diff` / test / lint / 一致性檢查，任一失敗即 `verdict: fail`。
- **學習迴圈**：brief 完成自動寫 session 摘要，並在使用者批准下沉澱 lesson / pattern（local-only，與外部知識庫解耦）。

---

## 核心概念

| 概念 | 說明 |
|---|---|
| **E²R（受限 2 層樹）** | L0 = 使用者開的 brief；L1 = 切出的 sub-brief。不允許 L2。 |
| **四層抽象** | Role（角色）/ Skill（跨專案方法論）/ Codex（專案領域知識）/ Directive（單次任務追加指示）。 |
| **Recipe** | 「建議的 role + skill + pipeline 組合」，落地起點而非強制鎖定。 |
| **Typed Verdict** | producer / reviewer 共用一份 JSON schema，7 種 verdict 驅動 main。 |
| **Trust Mode** | strict / standard / sandbox 三檔，決定 Bash 白名單與依賴策略。 |

---

## 安裝

1. 把本框架放到專案的 `.framework/`
2. 在該專案啟動 Claude Code，執行 `/framework-init`
3. 之後用 `/brief-new "需求"` 開始工作

---

## 目錄結構

```
.framework/
├── CHANGELOG.md
├── README.md
└── lib/
    ├── VERSION
    ├── design-summary.md      # 完整設計總覽（接手 agent 入口）
    ├── models.yaml
    ├── core/                  # control-plane / e2r-tree / review-loop / learning-loop ...
    ├── roles/                 # 各角色定義
    ├── skills/                # 跨專案技能
    ├── commands/              # slash commands（/brief-*, /framework-*）
    ├── init/                  # init 流程與模板
    └── recipes/               # dev-team 等預設組合
```

詳細設計見 [`lib/design-summary.md`](lib/design-summary.md)。
