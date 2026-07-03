---
name: framework-permissions-sync
description: 強制重新同步 Claude Code permissions 與 framework trust mode
allowed-tools: Read, Edit, Write
---

# /framework-permissions-sync

依當前 trust mode 強制重新同步 `.claude/settings.local.json` 的 permissions 區塊。對應 `core/trust-modes.md` § 5.1。

## 用法

```
/framework-permissions-sync           # 依當前 trust_mode 重 sync
/framework-permissions-sync --dry     # 顯示差異但不寫
/framework-permissions-sync --reset   # 重置 user 加的項目（連同 framework 項目都重寫）
```

## 何時用

正常情況下 `/framework-init` 與 `/framework-trust-set` 都會自動 sync。但下列情境需手動：

| 情境 | 用法 |
|---|---|
| 使用者手動編輯 settings.local.json 後想重置成框架預期狀態 | `/framework-permissions-sync` |
| 升級 framework 版本後 trust mode 樣板有更新 | `/framework-permissions-sync` |
| Recipe 改了 bash_extra_allow（rare） | `/framework-permissions-sync` |
| 想清空所有手動加的項目、回 framework 預設 | `/framework-permissions-sync --reset` |

## 行為

```
1. Read .framework/.initialized 取 trust_mode + customizations
2. Read .claude/settings.local.json
3. 依 core/trust-modes.md § 5.1 演算法：
   a. 計算 new_managed_allow / new_managed_deny（由 mode 樣板 + recipe.bash_extra_allow_template 渲染 + customizations.bash_extra_allow / deny）
   b. 取舊 _framework_managed_permissions
   c. 從 permissions.{allow,deny} 移除舊 managed
   d. 加入新 managed
   e. 保留 permissions 內使用者後加的項目（除非 --reset）
4. 顯示差異：
   「以下變動：
      Add to allow: [...]
      Remove from allow: [...]
      Add to deny: [...]
      Remove from deny: [...]
    User entries kept (not in framework managed): [...]
   」
5. 若 --dry → 退出，不寫
6. 否則 → 寫回 settings.local.json
7. 提示重啟：「permissions 已更新，需重啟 Claude Code 才生效」
```

## --reset 模式

```
permissions.allow = new_managed_allow （完全覆寫，使用者手動加的項目會被清掉）
permissions.deny = new_managed_deny （同上）
_framework_managed_permissions.{allow,deny} = new_managed_*
```

⚠️ 此模式破壞性，使用前確認使用者明白會清掉手動項目。建議顯示二次確認：

```
⚠️ --reset 將清除 settings.local.json 內所有手動加的 permissions 項目。
即將被清除的 user-added 項目：
  - Bash(my-custom-tool:*)
  - Bash(...)

確定 reset？(yes/N)
```

## --dry 模式

只顯示會做什麼，不寫檔。給使用者驗證後再執行真正的 sync。

## 異常處理

| 狀況 | 處理 |
|---|---|
| settings.local.json 不存在 | 視為首次寫，建立完整 settings + permissions |
| settings.local.json 格式錯誤 | 拒絕 sync、提示使用者修檔（避免破壞既有設定） |
| .framework/.initialized 缺 trust_mode | 提示「Framework 未 init，請先執行 /framework-init」 |
| 寫檔權限不足 | 顯示路徑、不修改 |

## 不做的事

- 不切換 trust_mode（要切換用 `/framework-trust-set <mode>`）
- 不改 .framework/.initialized
- 不重啟 Claude Code（提醒使用者手動重啟）
- 不影響其他 settings.local.json 欄位（framework_disabled / 自訂等）

## 與 /framework-trust-set 對比

| 指令 | 用途 |
|---|---|
| `/framework-trust-set <mode>` | 切換 trust mode + 自動 sync permissions |
| `/framework-permissions-sync` | 不切 mode，僅依當前 mode 重 sync permissions |

## 相關文件

- `core/trust-modes.md` § 5.1：sync 演算法 + 三 mode 樣板
- `commands/framework-trust-set.md`：切換 mode（含 sync）
- `commands/framework-init.md`：首次 init（含 sync）

## 相關指令

- `/framework-trust-set`
- `/framework-status`
- `/framework-init --reset`
