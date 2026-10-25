# macOS 磁碟清理常見模式

> 2026-07-06 會話中驗證的實際數據。最後更新：2026-07-06。

## 實際掃描數據（2026-07-06）

系統總佔用 **~82.9 GB**，主要分佈：

| 路徑 | 大小 | 說明 |
|------|------|------|
| `/Library` | 38.55 GB (mo 快取) → **5.5 GB (du 實際)** | 系統 Library |
| `~` | **24.3 GB** | 使用者目錄 |
| `/Applications` | **12.2 GB** | 應用程式 |
| `~/Library` | **7.8 GB** | 使用者 Library |

## 使用者 Library 大宗佔用

### Application Support (4.6 GB)

| 路徑 | 大小 | 說明 |
|------|------|------|
| `Microsoft Edge/` | **2.7 GB** | Service Worker 286M, Extensions 239M, IndexedDB 70M, **EdgeTranslateKitLanguagePack 790M** |
| `net.imput.helium/` | **411 MB** | Helium Browser |
| `Blackmagic Design/DaVinci Resolve/` | **41 MB** | Resolve Project Library 5.6M |
| `Cursor/` | **17 MB** | Cursor editor |
| `com.colliderli.iina/` | **26 MB** | IINA media player |

### Caches (3.2 GB)

| 路徑 | 大小 | 說明 |
|------|------|------|
| `net.imput.helium/Default/` | **1.4 GB** | Helium 瀏覽器快取 |
| `ms-playwright/` | **1.0 GB** | Chromium 1228/1223 + headless_shell |
| `Microsoft Edge/` | **420 MB** | Edge 快取 |
| `ms-playwright-go/` | **124 MB** | Go 版 Playwright |
| `Homebrew/` | **37 MB** | bootsnap 22M + api 15M |
| `claude-cli-nodejs/` | **15 MB** | Claude CLI 快取 |

### var/folders (1.4 GB)

| 路徑 | 大小 | 說明 |
|------|------|------|
| `C/tw.com.iwplay.nte/` | **762 MB** | 尼特遊戲快取 |
| `X/net.imput.helium.code_sign_clone/` | **661 MB** | Helium code signing clone |
| `C/clang/` | **63 MB** | Clang 快取 |
| `C/com.liuliu.draw-things/` | **37 MB** | Draw Things AI 快取 |
| `T/com.microsoft.EdgeUpdater...` | **156 MB** | Edge updater 暫存 |

### Agent 資料庫與日誌

| 路徑 | 大小 | 說明 |
|------|------|------|
| `~/.local/share/mimocode/log/2026-07-04T033353.log` | **8.3 GB** | ⚠️ **單一異常大 log 檔** — MiMoCode 單一 session 日誌 |
| `~/.local/share/mimocode/mimocode.db` | **774 MB** | MiMoCode 資料庫 |
| `~/.local/share/opencode/opencode.db` | **2.0 GB** | OpenCode 資料庫 |
| `~/.hermes/state.db` | **705 MB** | Hermes session 資料庫 |
| `~/.codex/` | **1.0 GB** | Codex logs_2.sqlite 128M + sessions 120M + packages 679M |
| `~/.hermes/hermes-agent/` | **1.1 GB** | venv 313M + node_modules 307M + tests 30M |
| `~/.local/bin/agy.*.old` | **135 MB** | ⚠️ **舊版 Antigravity 二進位**，可刪 |

### Desktop 專案檔案

| 路徑 | 大小 | 說明 |
|------|------|------|
| `Desktop/你要去哪裡/` | **2.7 GB** | 劇場投影專案（h265.mov 1.05G + alpha.webm 466M） |
| `Desktop/artfactory/` | **345 MB** | ArtFactory 網站專案 |
| `Desktop/artfactory-presentation/` | **127 MB** | 簡報 |

## 典型大檔案位置

| 路徑 | 典型大小 | 說明 |
|------|---------|------|
| `~/Library/Caches/net.imput.helium/Default/` | 1–2 GB | Helium Browser 快取 |
| `~/Library/Application Support/Microsoft Edge/` | 2–3 GB | Edge 快取 + 翻譯套件 |
| `~/Library/Caches/ms-playwright/` | 500 MB–1 GB | Playwright Chromium 版本快取 |
| `~/Library/Caches/Homebrew/` | 20–40 MB | Homebrew 下載快取 |
| `/Library/Application Support/com.apple.idleassetsd/Customer/` | 0–50 GB | macOS 螢幕錄影暫存（Cmd+Shift+5 殘留） |
| `~/.local/share/mimocode/log/` | 0–10+ GB | ⚠️ **單一 log 檔可能異常膨脹** |
| `~/.local/share/opencode/opencode.db` | 500MB–2GB | OpenCode session 資料庫 |
| `~/Library/Caches/` | 500MB–2GB | 各應用程式快取 |

## 常用命令

```bash
# 整體概覽
du -sh /* 2>/dev/null | sort -rh | head -10

# 使用者目錄
du -sh ~/Library/* 2>/dev/null | sort -rh | head -15
du -sh ~/Desktop/* 2>/dev/null | sort -rh | head -10

# 特定目錄深度分析
du -sh ~/Library/Caches/*/ 2>/dev/null | sort -rh | head -10
du -sh ~/Library/Application Support/*/ 2>/dev/null | sort -rh | head -10

# 驗證實際大小（不受 mo 快取影響）
du -sh /Library
du -sh /Library/Application\ Support

# 檢查 agent 資料庫
du -sh ~/.hermes/state.db ~/.local/share/*/ 2>/dev/null | sort -rh

# 檢查 var/folders 臨時快取
du -sh /var/folders/jq/*/C/* 2>/dev/null | sort -rh | head -15
du -sh /var/folders/jq/*/X/* 2>/dev/null | sort -rh | head -10
```

## mo 快取不一致

`mo analyze --json` 對 root 擁有的目錄報告的大小可能過時。當 mo 和 du 結果不一致時，以 du 為準。

## 安全清理建議

可安全清理（不影響資料）：
- `~/Library/Caches/` 下的所有快取
- `~/Library/Caches/ms-playwright/` 中的舊版 chromium（保留最新版）
- `~/Library/Application Support/Microsoft Edge/Default/load_statistics.db`
- `/Library/Application Support/com.apple.idleassetsd/Customer/` 中的 UUID .mov 檔
- `~/.local/bin/agy.*.old` — 舊版二進位檔
- `~/.local/share/mimocode/log/` 中異常大的單一 log 檔（>1GB）

需要確認後清理：
- Edge TranslateKit Language Pack（790 MB，不用翻譯可刪）
- OpenCode opencode.db（2.0 GB，包含歷史 session）
- Hermes state.db（705 MB，包含歷史 session）
- Desktop 上的專案檔案（不是暫存）