---
name: framework-role-add
description: 對話式新增 role（問名稱 / 類型 / 職責 / skill / 檢查清單 / tools）
allowed-tools: Read, Write, Glob
---

# /framework-role-add

對話式建立新 role md 檔。

## 用法

```
/framework-role-add
/framework-role-add --from <existing_role>    # 以現有 role 為起點
/framework-role-add --template <recipe_role>  # 從 .framework/lib/roles/ 複製
```

## 對話流程

```
Q1. Role 名稱？（小寫連字號，例：data-analyst-junior）
> ____

Q2. Type？(producer / reviewer)
> ____

Q3. 職責一句話？
> ____

Q4. Tier？(cheap / mid / top；預設 mid)
> ____

Q5. Tools？逗號分隔（Read 預設必選；其他從：Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch）
> ____

Q6. Produces / Reviews tag？
   - producer 必填 produces：[code, plan, analysis, report, ...]
   - reviewer 必填 reviews：同上
> ____

Q7. 要載入哪些 skill？逗號分隔，從 .claude/skills/ 內已有的選；或 none
> ____

Q8. 啟用 codex？(auto / null；auto = 找 .framework/codex/{name}.md)
> ____

Q9. Memory 互動？
   consume（從哪些分類讀 lesson）：[planning, engineering, code-review, ...]
   contribute（suggest_lesson 預設歸入哪類）：同上
> ____

Q10. Worktree 需求？(required / optional / forbidden)
> ____

Q11. （reviewer 才問）審核動作清單？
    每行格式：
      檢查項 | 命令或動作 | 通過條件
    例：
      tests | pytest | 全 pass 或 baseline
      lint | ruff check . | 無新增 error
> （多行輸入，空行結束）
```

## 寫檔（依 control-plane.md §2.1 鐵律：cp > Edit > Write）

### 路徑 A：使用者用 `--from <existing>` 或 `--template <recipe_role>`

```
1. cp 來源檔 → .claude/agents/{name}.md
   - --from <existing>: cp .claude/agents/{existing}.md → 目標
   - --template <recipe_role>: cp .framework/lib/roles/{template}.md → 目標
2. Edit frontmatter（name / description / tier / tools / produces / reviews 等依答案）
3. 若使用者明示要改某章節 → Edit 該章節
4. 不重寫整檔
```

### 路徑 B：純手建（無 template）

```
1. 從 .framework/lib/roles/ 找最相近的 base：
   - producer 取 .framework/lib/roles/engineer.md 為 base
   - reviewer 取 .framework/lib/roles/code-reviewer.md 為 base
2. cp base → .claude/agents/{name}.md
3. Edit frontmatter（全欄位依答案）
4. Edit 各章節（職責 / 流程 / 鐵律）依答案改寫
5. 仍不重寫整檔（Edit 可逐章替換）
```

**永不 Write 整檔**：即使「全部章節都要改」也逐章 Edit。避免雙倍 token。

Body 章節依 `core/soul-schema.md` 第 2.2 節結構：
1. 職責
2. Path Boundaries
3. Prerequisite Gate
4. 執行流程
5. 審核動作清單（reviewer-only）
6. 鐵律

某些章節在 base template 已有合理預設文字（例：鐵律常見項目），可保留 cp 來的內容，使用者後續手動編輯。

## 寫完後

```
✓ 已寫入 .claude/agents/{name}.md
✓ 已偵測：此 role 是 producer，預設加入 dev-team pipeline 的 engineering stage？(y/n)
   y → 提示使用者編輯 .framework/pipeline.yaml
   n → 略過

⚠️ 重要：新增的 role 名稱「{name}」要等重啟 Claude Code session 後才能 spawn

  - 對既有 role 的 Edit（tier / tools / body）→ 立即生效，不需重啟
  - 新增 role 名稱 → 必須重啟（Claude Code 在 session 啟動時鎖定 agent 列表）
  - 同樣，新增 slash command 也要重啟才被認得

下一步：
  - 編輯 .claude/agents/{name}.md 補充 Body 章節細節
  - /framework-pipeline-edit 將此 role 加進 pipeline
  - 重啟 Claude Code（新 role 才生效）
  - 重啟後 /framework-role-list 可看到新 role
```

## 異常

| 狀況 | 處理 |
|---|---|
| Name 已存在 | 拒絕，提示用 /framework-role-edit |
| Name 格式違規 | 重問 |
| Tools 含未知值 | 重問 |
| Reviewer 沒列審核動作清單 | 警告（非阻塞）：「reviewer 無檢查清單會放水」 |

## 不做的事

- 不自動進 .framework/pipeline.yaml（提示但不寫，避免使用者沒料到）
- 不自動建 codex（codex 是另一檔，使用者另外管）
- 不自動建 skill（skill 規模太大、不適合對話建）

## 相關指令

- `/framework-role-edit`
- `/framework-role-list`
- `/framework-role-remove`
- `/framework-pipeline-edit`
