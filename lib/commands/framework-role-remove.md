---
name: framework-role-remove
description: 移除 role（含連帶 pipeline 影響檢查）
allowed_tools: Read, Edit, Bash, Glob
---

# /framework-role-remove

移除 `.claude/agents/{name}.md` + 連帶清理。

## 用法

```
/framework-role-remove <name>
/framework-role-remove <name> --force    # 略過確認
```

## 流程

```
1. 確認 role 存在
2. 偵測連帶影響：
   a. Read .framework/pipeline.yaml，搜尋此 role 是否被引用：
      - role / reviewer 欄位
      - depends_on 引用的 stage 是否該 stage 用此 role
   b. Read 其他 .claude/agents/*.md，搜尋是否有 produces/reviews 配對依賴
   c. Read .framework/codex/{name}.md 是否存在
3. 顯示影響：
   「移除 role {name} 將：
      - 影響 .framework/pipeline.yaml 的以下 stage（會引用 missing role）：
        * new_feature.engineering（用此 role 為 reviewer）
      - 連帶 codex/{name}.md 也會被視為 orphan
      - .framework/.initialized.tier_overrides 中相關欄位失效

    確定要移除嗎？(y/N)」
4. y → 執行移除
   - rm .claude/agents/{name}.md
   - 提示使用者：「請手動編輯 .framework/pipeline.yaml 移除引用 / 換 role」
   - 不自動改 .framework/pipeline.yaml（避免破壞使用者意圖）
   - 不自動刪 codex/{name}.md（可能仍有歷史價值，使用者手動決定）
5. n → 取消
```

## 寫檔

只刪 `.claude/agents/{name}.md`。其他連帶檔由使用者手動處理。

## --force 模式

略過影響顯示與確認，直接刪。給 script / batch 用。**不建議互動式使用**。

## 不做的事

- 不自動改 .framework/pipeline.yaml
- 不自動刪 codex
- 不自動 cancel active brief（即使 brief 用此 role 也不主動干預）

## 移除後檢查

執行：
```
/framework-status
```

確認 role 已移除、其他配置 OK。

## 相關指令

- `/framework-role-list`
- `/framework-pipeline-edit`
- `/framework-status`
