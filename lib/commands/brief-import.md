---
name: brief-import
description: 從 GitHub Issue / 外部來源匯入 brief
allowed-tools: Read, Write, Edit, Bash, Glob, WebFetch, Task
---

# /brief-import

從外部來源匯入 brief（design-summary 8a 路徑 D：GitHub Issue 整合）。

## 用法

```
/brief-import <github-issue-url>
/brief-import <local-md-path>
```

## 前置條件

- 已 init
- 無 active brief（若有，提示如 /brief-new 一樣）
- GH 整合：`gh` CLI 已安裝（用 `gh issue view`）

## 行為（GitHub Issue）

```
1. 解析 URL：https://github.com/{owner}/{repo}/issues/{N}
2. 確認 gh CLI 可用：
   - gh --version → 若失敗 → 顯示「需安裝 gh CLI」退出
3. 抓取 issue：
   gh issue view {N} -R {owner}/{repo} --json title,body,labels,assignees,number,url
4. 顯示給使用者：
   「Issue #{N}：{title}
    Body 摘要：（前 200 字）
    Labels：{labels}

    匯入為 brief？(y/n/edit)
      y → 直接匯入
      edit → 顯示完整 body，使用者可修改後再匯入
      n → 取消」
5. y →
   a. 計算 brief_id：{today}-issue-{N}-{slug from title}
   b. 建 .framework/briefs/{brief_id}/
   c. 寫 brief.md：
      ```markdown
      # Brief: {title}

      ## 來源

      - GitHub Issue: {url}
      - Issue 編號: #{N}
      - 匯入時間: {ISO}
      - Labels: {...}

      ## 原始需求

      {issue body}

      ## 元資料

      - brief_id: {...}
      - imported_from: github-issue
      - source_url: {url}
      ```
   d. 後續流程同 /brief-new（建 _active.yaml / _tree.yaml / 進 Explore）
6. edit → 把 body 填入互動式編輯模式（main 詢問補充 / 修改）
```

## 行為（local md）

```
1. Read 指定路徑（必為 .md 檔）
2. 顯示前 200 字
3. 確認匯入
4. brief_id：{today}-import-{filename slug}
5. 寫 brief.md（複製內容 + metadata）
6. 後續同 GH issue
```

## 後續流程

匯入後 main 自動進入 `/brief-new` 之後的流程：
- recipe 推薦
- Roster 確認
- Explore Step 2-6

唯一差別：**不問需求描述**（已從 issue / md 來）。

## 雙向同步（不實作，留 Phase C）

未來可能加：
- brief 完成後自動 close issue
- brief 進度自動 comment 到 issue
- issue 變動時 brief 同步

當前 v1 不實作（單向 import）。

## 異常

| 狀況 | 處理 |
|---|---|
| URL 格式錯誤 | 重問 |
| gh CLI 未安裝 | 提示安裝步驟 + 退出 |
| Issue 不存在 / 無權限 | 顯示 gh 錯誤訊息 |
| Local md 不存在 | 顯示路徑錯誤 |
| 已有 active brief | 同 /brief-new 處置（等 / 取消 / 升級為 sub-brief） |

## 為什麼匯入 vs 對話

某些情境匯入更好：
- **跨 IDE / 跨工具的需求**：使用者已在 GH 寫好 issue，不用重輸
- **多人協作**：團隊在 GH 討論需求，最終由你執行
- **批次任務**：寫 script 把 N 個 issue 投到 inbox/ 再批次處理

對話更好：
- **需求未成形**：邊談邊釐清
- **快速啟動**：不用先寫 issue

兩者並存，使用者按情境選。

## 相關指令

- `/brief-new`
- `/brief-status`

## 相關文件

- design-summary 第 8a 節（brief 來源討論）
