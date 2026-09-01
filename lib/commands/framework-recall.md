---
name: framework-recall
description: 唯讀查詢外部知識庫（KB）參考其他 repo 的既有紀錄；結果折進當前 brief 的 intel-pack
allowed-tools: Read, Glob, Grep
---

# /framework-recall

純命令驅動的**跨 repo 唯讀查詢**入口。讓使用者主動叫 main 去外部知識庫（KB）撈其他 repo 的做法當參考——不自動、不靠自然語言偵測、不寫回 KB、不存進 local memory。

對應 `core/control-plane.md §8.5`（KB sink）、§4 Step 2（情報蒐集）。

## 設計理由

Framework 落地在各 repo、各自維護 local `.framework/memory`；外部 KB 是跨 repo 的知識庫。起 brief 時常想參考「別的 repo 當初怎麼做這件事」。

但 planner 是 subagent，使用者沒辦法對跑到一半的 planner 下指令。**main 才是情報蒐集者**（讀 memory、產 intel-pack、spawn 時注入 planner）。所以這個命令打給 **main**：main 查 KB、把結果折進 `intel-pack.md`，planner 循 §6.1 既有注入路徑就吃得到。

預設關閉，符合「framework 與 KB 解耦」的不變式——只有 repo 在 `.framework/.initialized` 宣告 `knowledge_base.recall: true` 才可用。

## 用法

```
/framework-recall <主題>                  # 跨所有 project 搜 KB
/framework-recall <主題> --project <name>  # 限定某 repo/project（如 fishhunter）
```

## 行為

```
1. 讀 .framework/.initialized 取 knowledge_base
   - block 不存在 OR recall != true → 回「本 repo 未連接外部 KB（或 recall 未啟用）」，結束（不報錯）
2. 取 knowledge_base.path（外部 KB 路徑）
3. 跨 project 搜尋（唯讀）：
   - Grep KB 內 技術決策/ + 筆記/ + projects/ 的 .md，用 <主題> 關鍵字
   - 靠 frontmatter / #project/* tag 標出每條來自哪個 repo
   - --project 指定時，只回該 project tag 的條目
4. 彙整回報給使用者（不改任何檔）：
   - 命中的 lessons / patterns / ADR，標來源 repo + 檔名 + 一句摘要
   - 找不到 → 「KB 內查無 <主題> 相關，建議換關鍵字或直接看 codebase」
5. 若本 session 有正在處理的 brief（解析：本 session 的 brief → registry 唯一 lock → 多 lane 則問；
   且該 brief 有 intel-pack.md）：
   - 把命中結果**唯讀引用**折進 intel-pack.md 的「## 跨 repo 參考」段（無則新建該段）
   - 標明來源（KB 路徑 + 檔名 + project），供後續 spawn planner 時循 §6.1 注入
   - 不複製進 .framework/memory（不是 ingest、是 reference）
```

## 落點：intel-pack 的「跨 repo 參考」段範例

```markdown
## 跨 repo 參考（/framework-recall：<主題>）

> 來源：<knowledge_base.path>（唯讀引用，未納入 local memory）

- [<repo-A>] <某 ADR / 決策標題> — 一句摘要
- [<repo-B>] <某筆記標題> — 一句摘要
```

## 不做的事

- **不寫回 KB**：本命令唯讀（allowed-tools 無 Write / Edit）。寫 KB 走 learning loop 升流 `(m)` 或使用者透過該 KB 自身的入口手動寫
- **不存進 local memory**：撈回的是 reference，不是 ingest；不寫 `.framework/memory/`
- **不自動觸發**：只有使用者明確下 `/framework-recall` 才查；planner / 其他 role 不得自行呼叫
- **沒接 KB 不報錯**：`recall != true` 直接回提示
- **不開新 brief**

## 異常處理

| 狀況 | 處理 |
|---|---|
| `.initialized` 無 `knowledge_base` | 回「本 repo 未連接外部 KB」 |
| `knowledge_base.recall: false` | 回「本 repo 未啟用 recall（promote 可能仍開）」 |
| `knowledge_base.path` 不存在/讀不到 | 回錯誤 + 提示檢查路徑與全域 settings additionalDirectories |
| 無 active brief | 仍回報查詢結果給使用者，只是不折進 intel-pack（無 brief 可折） |

## 與其他指令對比

| 指令 | 方向 | 用途 |
|---|---|---|
| `/framework-recall` | 讀 KB | 撈其他 repo 做法當參考（唯讀） |
| learning loop Step 4 `(m)` | 寫 KB | brief 收尾升流蒸餾後 lessons/patterns/preferences |
| KB 自身寫入入口 | 寫 KB | 使用者手動記筆記（與 framework 無關） |
| `/framework-learn` | 寫 local | 補 local memory，不碰 KB |

## 相關文件

- `core/control-plane.md §8.5`：KB sink 設計；§4 Step 2：情報蒐集與 intel-pack
- `core/learning-loop.md §8.5 / §11.5`：升流（寫）端
