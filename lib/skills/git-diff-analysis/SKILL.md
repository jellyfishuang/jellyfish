---
name: git-diff-analysis
description: 讀懂 git diff 並判斷影響範圍 / 風險的方法論
scope: global
applicable_roles: [code-reviewer, engineer, planner]
version: 1.0.0
last_updated: 2026-05-06
---

# Git Diff Analysis

> **Worktree-disabled 模式 override（必先讀）**：若專案 worktree=false 且 engineer 不 commit 不 stage——diff 基準一律 working tree vs `HEAD`（`git -C <repo> diff HEAD`），新檔看 `git -C <repo> status --porcelain` 的 `??` 行；本文所有 `main...HEAD` / `main..HEAD` / commit log 範例僅適用 worktree 模式。

任何 code review 或 engineer 自評的起點都是讀 diff。讀 diff 不是逐行看，而是分層理解。

## 1. 四層讀法

從外層往內層讀，越上層越能 fail-fast：

### 1.1 檔案層

```bash
git diff main...HEAD --name-only
git diff main...HEAD --stat
```

**判斷**：
- 哪些檔被改、新增、刪除？
- 跨幾個模組 / 服務？
- 規模（行數）合理嗎？

**警訊**：
- 改 ≥10 個檔但 plan 說 small 任務 → 拆解失敗
- 動到 build / CI 配置但 plan 沒提 → out of scope
- 動到 .env / secrets / config → 高風險

### 1.2 介面層

```bash
git diff main...HEAD -- '**/*.go' | grep -E '^[+-]\s*(func|type|var)'   # Go
git diff main...HEAD -- '**/*.py' | grep -E '^[+-]\s*(def|class)'        # Python
git diff main...HEAD -- '**/*.ts' | grep -E '^[+-]\s*(export|interface)' # TS
```

**判斷**：
- Public API 簽章是否變動？
- 新增 export / 刪除 export？
- 介面契約符合 plan？

**警訊**：
- 函式參數順序變動（caller 全壞）
- Optional 參數變必需
- Return type 結構變動
- 新增的 public API plan 未提

### 1.3 行為層

```bash
git diff main...HEAD <關鍵檔>
```

**判斷**：
- 邏輯改動是否符合 spec？
- 新邏輯有覆蓋對應測試嗎？
- 移除 / 修改的程式碼是否有未察覺的 callers？

**讀法技巧**：
- 先讀 `+` block（新增邏輯）
- 再讀 `-` block（移除邏輯）→ grep 該函式名找 caller
- 變更（- 後接 +）：對比舊新版本，判斷是否語意保持

### 1.4 副作用層

```bash
git diff main...HEAD pyproject.toml package.json go.mod Cargo.toml
git diff main...HEAD .github/workflows/
git diff main...HEAD Dockerfile docker-compose.yml
git diff main...HEAD migrations/
```

**判斷**：
- 依賴變動？
- CI 配置變動？
- 部署 / 容器配置？
- DB migration？（特別敏感）

**警訊**：
- 加 git submodule
- 改 base image
- 改 CI 觸發條件
- 不可逆 migration（drop column / table）

---

## 2. Baseline 對比

很多檢查需要與 main branch 對比是否「新增的問題」：

```bash
# 暫存當前 worktree 改動
git stash

# 切到 main 跑同樣檢查
git checkout main
{check_command}     # 例：pytest, ruff check

# 回 worktree branch
git checkout -
git stash pop
```

如果 main 也 fail 同樣項目 → 屬 baseline，不算本次 regression。

---

## 3. Diff Hunks 解讀

每個 hunk 開頭：
```
@@ -45,7 +45,12 @@ def handler(req):
```

意思：
- `-45,7`：原檔從第 45 行起共 7 行
- `+45,12`：新檔從第 45 行起共 12 行
- `def handler(req):` 後面是 hunk 上下文（最近的 function 簽章）

讀 hunk 時：
- `-` 行：被刪除 / 修改前
- `+` 行：新增 / 修改後
- 不帶符號：上下文，未變

**Tip**：用 `git diff -U10` 增加上下文行數有助於理解 hunk 周邊邏輯。

---

## 4. 常見陷阱

### 4.1 Whitespace-only 改動

```bash
git diff main...HEAD --ignore-all-space --stat
```

對比有 / 沒 ignore whitespace 的 diff。如果差異大，代表很多改動是 reformat（noisy）→ 提示 engineer 應拆 reformat 為獨立 commit。

### 4.2 移動程式碼（detect rename / copy）

```bash
git diff main...HEAD -M -C
```

`-M`：偵測 rename。`-C`：偵測 copy。讀大重構時必加。

### 4.3 二進位檔變動

```bash
git diff main...HEAD --stat | grep "Bin"
```

二進位變動 git 預設 skip 顯示。要警覺：
- 圖片 / 字型：通常 OK
- `.so` / `.dll`：意外變動代表 build artifact 被 commit
- Lock 檔（package-lock.json / poetry.lock）：依賴變動的訊號

### 4.4 Submodule 變動

```bash
git diff main...HEAD | grep -E "^Subproject"
```

Submodule 升級 = 隱形依賴變動，要對照 plan 看是否許可。

---

## 5. 實作練習：一次完整讀 diff

```bash
# Step 1：規模 + 範圍
git diff main...HEAD --stat
git diff main...HEAD --name-only

# Step 2：介面變動
git diff main...HEAD --diff-filter=M -- '**/*.go' \
  | grep -E '^[+-]\s*(func [A-Z]|type [A-Z])'

# Step 3：詳細 hunk
git diff main...HEAD -U10 services/user/api.go

# Step 4：副作用
git diff main...HEAD go.mod go.sum
git diff main...HEAD .github/workflows/

# Step 5：commit history
git log main..HEAD --oneline
git log main..HEAD --stat   # 看每個 commit 動了什麼
```

---

## 6. 給 engineer 的 self-review 流程

寫完 code 後，emit verdict 前：

1. `git diff main...HEAD --stat`：確認規模符合 plan estimated_complexity
2. `git diff main...HEAD --name-only`：確認所有檔在 plan.allowed_paths 內
3. `git diff main...HEAD` 通讀一遍：找 typo / 遺留 print / 未刪 TODO
4. `git log main..HEAD --oneline`：確認 commit 切分合理（一個 commit 一個邏輯單元）

這 4 步省下 reviewer 第一輪 fail 的成本。
