---
name: framework-role-edit
description: 對話式修改既有 role（也可直接編輯 .md 檔）
allowed_tools: Read, Edit, Glob
---

# /framework-role-edit

修改 `.claude/agents/{name}.md` 的對話流程。也可直接用編輯器改 md 檔（兩條路徑都合法）。

## 用法

```
/framework-role-edit <name>
```

## 對話流程

```
1. Read .claude/agents/{name}.md
2. 顯示當前 frontmatter 與 body 章節摘要
3. 顯示選單：
   (1) 改 frontmatter 欄位（tier / tools / skills / codex / memory）
   (2) 改 body 章節（職責 / Path Boundaries / 執行流程 / 審核清單 / 鐵律）
   (3) 直接開檔自己編輯（顯示路徑後退出）
   (4) 取消

4. (1) → 列現有 frontmatter，逐欄問是否改
5. (2) → 列現有章節，逐章問是否改
6. (3) → 顯示路徑、退出
```

## 修改 frontmatter

```
當前 frontmatter：
  tier: mid
  tools: Read, Bash, Glob, Grep
  skills:
    - global/code-review-checklist
  codex: auto

要改哪個欄位？(tier/tools/skills/codex/.framework/memory/done)
> ____
```

每改一個欄位後，重複問，直到使用者答 `done`。

## 修改 body 章節

```
當前章節：
  1. 職責（45 字）
  2. Path Boundaries（Read 7 條 / Write 2 條 / Forbidden 5 條）
  3. Prerequisite Gate（4 項）
  4. 執行流程（6 步）
  5. 審核動作清單（10 項）
  6. 鐵律（7 條）

要改哪節？(1-6/done)
> ____
```

選擇章節後，main 顯示該節原文，問：
- 改寫整節（使用者貼新內容）
- 加一條（appendix）
- 刪一條（編號刪除）

## 寫檔

每修改：
1. 驗證 schema（依 `core/soul-schema.md`）
2. 驗證失敗 → 顯示錯誤、保留原文、不寫
3. 通過 → Edit `.claude/agents/{name}.md`
4. 顯示「✓ 已更新」

## 衝擊偵測

修改後若：
- 改了 produces / reviews tag → 提示：「.framework/pipeline.yaml 可能受影響，請檢查」
- 改了 tools → 提示：「Path Boundaries 可能不一致，請檢查 §2」
- 改了 skills → 提示：「對應 SKILL.md 必存在；不存在 spawn 時會警告」

## 異常

| 狀況 | 處理 |
|---|---|
| Role 不存在 | 顯示錯誤 + 列當前 role |
| 修改後 schema 違規 | 拒寫，顯示錯誤 |
| Tier 改成不存在的值 | 重問 |
| Tools 含未知值 | 重問 |

## 相關指令

- `/framework-role-list`
- `/framework-role-add`
- `/framework-role-remove`
- `/framework-pipeline-edit`
