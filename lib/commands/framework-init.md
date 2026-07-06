---
name: framework-init
description: 初始化 framework（從 recipe 選擇 + 客製問題 + 產出 .claude/ 結構）
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# /framework-init

執行 framework 初始化對話流程。

## 用法

```
/framework-init           # 標準初始化
/framework-init --reset   # 重來（先備份既有 .framework/codex/）
```

## 行為

依 `.framework/lib/init/interview.md` Step 1-6 執行：

1. **偵測 repo 特性**（main 自動掃 README / 配置 / 程式碼）
2. **選 recipe**（從 6 個內建 recipe 或 free-form）
3. **客製問題**（4-6 題：使用情境 / trust mode / worktree / tier / 語言 / recipe 專屬題）
4. **Codex 草稿生成**（對每個 producer role 輕訪談 + main 補充）
5. **產出檔案**（`.claude/agents/`, `.claude/skills/`, `.framework/codex/`, `.claude/commands/`, `CLAUDE.md`, `.framework/pipeline.yaml`, `.framework/memory/`, `.framework/briefs/` 結構）
6. **部署機械閘**：跑 `/framework-hooks-sync`（`lib/scripts/hooks_sync.py`——複製 gate scripts、渲染 hooks 設定合併進 `.claude/settings.json`、跑回歸；詳見該指令）
7. **摘要 + 強制重啟提示**（**不**提供試跑 dummy brief 選項；agent / slash command 列表須 session 重啟才生效）

## 前置條件

- `.framework/` 目錄存在於專案 root（clone / submodule / symlink）
- 使用者有 repo 寫入權

## 異常

| 狀況 | 處理 |
|---|---|
| `.framework/.initialized` 已存在且非 `--reset` | 提示「已 init 過，要 reset 還是用其他子指令？」 |
| `.framework/` 不存在 | 顯示錯誤：「找不到 framework 目錄。請先 clone 或 submodule 加入 framework。」 |
| 寫檔失敗（權限） | 回滾已寫的檔，提示具體路徑 |

## 對話腳本

執行此指令後，main session 載入 `.framework/lib/init/interview.md` 並依步驟對話。完整流程見該檔。

## 產出

完成後 repo 結構：

```
{repo}/
├── .framework/
│   ├── lib/                              ← 既有（複製自 framework master）
│   ├── codex/{role}.md × N producer roles
│   ├── memory/
│   │   ├── MEMORY.md
│   │   ├── architecture.md
│   │   ├── preferences.md
│   │   ├── lessons/                      ← 空目錄；{category}.md 由 learning loop 寫入
│   │   │   └── escalations/              ← 詳細事件檔
│   │   ├── patterns/                     ← 空目錄；同上
│   │   └── sessions/                     ← 空目錄；brief 完成時 main 寫
│   ├── briefs/
│   │   ├── inbox/
│   │   └── _archive/
│   ├── worktrees/                        ← 若 worktree=y
│   ├── pipeline.yaml
│   └── .initialized
├── .claude/
│   ├── agents/{role}.md × N              ← Claude Code native（從 lib/roles 複製）
│   ├── skills/{skill}/SKILL.md × M       ← Claude Code native（從 lib/skills 複製）
│   ├── commands/{cmd}.md                 ← Claude Code native（從 lib/commands 複製）
│   └── settings.local.json
└── CLAUDE.md
```

## 後續

`/framework-init` 跑完後，**必須先重啟 Claude Code session**（agent / slash command 在 session 啟動時鎖定，不重啟跑 brief 會 spawn 失敗）。

重啟後使用者可：
- `/brief-new` 開第一個 brief
- `/framework-status` 確認設定
- `/framework-role-list` 列當前 role
- 直接編輯 `.claude/agents/{role}.md` 客製
- 編輯 `.framework/memory/architecture.md` 填專案技術事實

## 相關指令

- `/framework-status`
- `/framework-role-add | edit | list | remove`
- `/framework-recipe-list`
- `/framework-pipeline-edit`
- `/framework-trust-set`
