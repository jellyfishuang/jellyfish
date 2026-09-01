---
name: framework-unlock
description: 強制清除指定 lane 的 lock（緊急 escape hatch；含警告）
allowed-tools: Read, Bash
---

# /framework-unlock

強制刪除指定 lane 的 `.framework/briefs/_active/{brief_id}.yaml`。**不接續**，純粹解鎖；只清指定那份，他 lane 不動。

## 用法

```
/framework-unlock <brief_id>          # 多 lane 下必帶（registry 僅一份時可省）
/framework-unlock <brief_id> --force  # 略過確認（給 script 用）
```

## 行為

```
1. 解析 brief_id（registry 唯一 lock 時可省參數），Read _active/{brief_id}.yaml
   （目標是 legacy 單檔 _active.yaml 時同樣適用——刪該單檔）
2. 若不存在 → 顯示「無此 lane 的 lock，無需 unlock」+ 列出現有 lanes
3. 顯示警告：
   「⚠️ 即將強制刪除 _active/{brief_id}.yaml

    當前狀態：
      brief_id: {...}
      phase: {...}
      啟動：{started_at}（{x}h ago）
      最後活動：{last_heartbeat}

    Unlock 後：
      - brief 目錄保留（.framework/briefs/{brief_id}/）
      - _tree.yaml 不變動
      - 進度資訊不丟失，但無法再 /framework-recover 接續
      - 若要接續，建議改用 /framework-recover

    確定要 unlock 嗎？(yes/N)」
4. yes → rm .framework/briefs/_active/{brief_id}.yaml；顯示「✓ 已 unlock」
5. N → 取消
```

## --force 模式

略過確認直接刪。

⚠️ 不建議互動式使用，主要給 script。

## 為什麼有此指令

`/framework-recover` 是首選，但有些情境 recover 跑不了：
- _tree.yaml 完全損毀（手動誤改）
- 多 session 衝突嚴重
- 使用者明確想拋棄當前 brief 進度（不想花時間 recover）

unlock 是 last resort。

## Unlock 後的後續

```
brief 目錄仍在（.framework/briefs/{brief_id}/）
要查看：cat .framework/briefs/{brief_id}/_tree.yaml / _manifest.md
要清除：rm -rf .framework/briefs/{brief_id}/
要恢復：手動編輯 _tree.yaml、自建 _active/{brief_id}.yaml（不建議）
要丟棄：直接開新 brief（/brief-new）
```

## 不做的事

- 不刪 brief 目錄
- 不刪 worktree
- 不解開 worktree branch
- 不清 memory / sessions
- 不接續任何工作

## 安全考量

unlock 是不可逆操作。執行前 framework 不會自動備份 brief 目錄（避免污染）。

若 brief 進度寶貴，使用者應先：
```
cp -r .framework/briefs/{brief_id} .framework/briefs/_archive/{date}-manual-backup-{brief_id}/
```

再 unlock。

## 相關指令

- `/framework-recover`（首選）
- `/brief-cancel`（明確取消當前 brief，較 unlock 乾淨）
- `/framework-status`

## 相關文件

- `core/batch-lock.md`：unlock 是 batch lock 的逃生口
