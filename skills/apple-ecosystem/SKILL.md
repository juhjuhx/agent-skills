---
name: apple-ecosystem
description: "macOS and Apple ecosystem: Notes, Reminders, FindMy, iMessage, computer use, disk cleanup. Use when: Apple, macOS, Notes.app, Reminders, FindMy, iMessage, Mac, disk space."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Apple, macOS, Notes, Reminders, FindMy, iMessage, Computer-Use, Cleanup]
    related_skills: [hermes-agent, obsidian]
---

# Apple Ecosystem

macOS-specific tools for Apple services and system management. All require macOS.

## Section 1: Apple Notes (memo CLI)

Manage Apple Notes via `memo` CLI. Notes sync across all Apple devices via iCloud.

```bash
memo notes                        # List all notes
memo notes -s "query"             # Search notes
memo notes -a "Note Title"        # Quick add
memo notes -e                     # Edit (interactive)
memo notes -ex                    # Export to HTML/Markdown
```

**Install:** `brew tap antoniorodr/memo && brew install antoniorodr/memo/memo`

## Section 2: Apple Reminders (remindctl)

Manage Apple Reminders via `remindctl`. Tasks sync across all Apple devices.

```bash
remindctl today                   # Today's reminders
remindctl add "Buy milk"          # Quick add
remindctl add --title "Call mom" --list Personal --due tomorrow
remindctl complete 1 2 3          # Complete by ID
```

**Install:** `brew install steipete/tap/remindctl`

**Due vs Alarm:** `--due` sets due date, `--alarm` sets notification trigger. For 30min early nudge:
```bash
remindctl add --title "Meeting" --due "2026-05-15 14:00" --alarm "2026-05-15 13:30"
```

## Section 3: Find My (AppleScript + Screenshot)

Track Apple devices and AirTags via FindMy.app. No CLI available — uses UI automation.

```bash
osascript -e 'tell application "FindMy" to activate'
sleep 3
screencapture -w -o /tmp/findmy.png
```

Then `vision_analyze(image_url="/tmp/findmy.png", question="What devices are shown and their locations?")`

**With peekaboo (recommended):** `peekaboo see --app "FindMy" --annotate --path /tmp/findmy-ui.png`

**Limitation:** AirTags only update when FindMy page is actively displayed.

## Section 4: iMessage (imsg)

Send and receive iMessages/SMS via `imsg` CLI.

```bash
imsg chats --limit 10 --json                    # List chats
imsg history --chat-id 1 --limit 20 --json      # View history
imsg send --to "+14155551212" --text "Hello!"   # Send message
imsg send --to "+14155551212" --text "Hi" --file /path/to/image.jpg
```

**Install:** `brew install steipete/tap/imsg`

**Always confirm recipient and message content before sending.**

## Section 5: Computer Use (cua-driver)

Drive the macOS desktop in the background — screenshots, mouse, keyboard, scroll, drag — without stealing the user's cursor.

```bash
computer_use(action="capture", mode="som", app="Safari")  # Screenshot + element index
computer_use(action="click", element=7)                     # Click by index
computer_use(action="type", text="Hello")                   # Type text
computer_use(action="key", keys="cmd+s")                    # Keyboard shortcut
```

**Key rules:**
- Always capture before clicking — element indices come from last capture
- Never raise windows unless user explicitly asked
- Scope captures to an app (`app="Safari"`)
- Never click permission dialogs, password prompts, or payment UI

## Section 6: Disk Cleanup (mole CLI)

Analyze and free disk space on macOS.

```bash
# Analyze disk (menu option 4)
script -q /dev/null bash -c '(echo 4; sleep 1; echo 4; sleep 1; echo "")' | mole 2>&1 | cat
```

### ⚠️ mo analyze --json 快取 bug

`mo analyze --json` 對 root 擁有的目錄（如 `/Library/`）會報告**過時/快取的大小**，即使檔案已被刪除。當 mo 顯示某目錄佔用大量空間但 `du -sh` 顯示不同結果時，**以 `du` 為準**。

```bash
# 正確做法：用 du 交叉驗證
mo analyze --json          # 可能不準確（快取 bug）
du -sh /Library            # 實際大小（真實）
```

典型症狀：mo 報告 33 GB 的 `com.apple.idleassetsd`，但 `du` 顯示 16 MB（因為暫存已被刪除）。

### Common disk space hot spots

| Location | Typical Size |
|----------|-------------|
| `~/Library/Caches/` | 500MB–2GB |
| `~/.cache/` | 1–5GB |
| `~/Library/Developer/` | 5–30GB |
| `~/.cache/huggingface/hub/` | 0–10GB |
| `~/Library/Caches/ms-playwright/` | 500–700MB |
| `~/.local/share/mimocode/log/` | 0–10+ GB | ⚠️ 單一 log 異常膨脹 |
| `~/.local/share/opencode/opencode.db` | 500MB–2GB |
| `~/.hermes/state.db` | 100MB–1GB |

### Container cleanup pitfall

macOS protects Containers at top level — delete contents, not the shell:
```bash
rm -rf ~/Library/Containers/com.app.id/Data/Documents/Models/  # ✅
rm -rf ~/Library/Containers/com.app.id  # ❌ "Operation not permitted"
```

**Always verify with `df -h /` after cleanup.**

### idleassetsd 螢幕錄影暫存

System-owned UUID-named `.mov` files in `/Library/Application Support/com.apple.idleassetsd/Customer/4KSDR240FPS/` can accumulate tens of GB. These are orphaned screen recording buffers from Cmd+Shift+5. See `references/macos-idleassetsd-cache-cleanup.md` for diagnosis and cleanup procedure.

### Safari 更新套件殘留

Safari updates downloaded via Software Update can leave multi-GB `.pkg` files in `/Library/Updates/`. See `references/safari-update-pkg-cleanup.md`.

### 磁碟清理常見模式

典型大檔案位置和清理建議見 `references/macos-disk-cleanup-common-patterns.md`。包含 Helium/Edge/Playwright/Homebrew/DaVinci 快取位置。

### 全面大檔案掃描模式

當使用者問「還有什麼暫存很大」或「幫我找大檔案」時，用 `find` 排除已知保留目錄，找出所有 >50MB 檔案：
```bash
find ~ /Library /Applications -type f -size +50M \
  ! -path "*/node_modules/*" \
  ! -path "*/Desktop/你要去哪裡/*" \
  ! -path "*/Library/Application Support/*" \
  ! -path "*/.hermes/hermes-agent/*" \
  ! -path "*/.local/share/claude/versions/2.1.201*" \
  ! -path "*/.codex/packages/standalone/releases/0.142*" \
  2>/dev/null | while read f; do
  sz=$(stat -f%z "$f" 2>/dev/null)
  mb=$((sz / 1048576))
  if [ "$mb" -gt 50 ]; then
    echo "$(printf '%.0f' $mb)MB  $f"
  fi
done | sort -t' ' -k1 -rn
```
**關鍵：** 先列出所有 >50MB 檔案，再跟使用者確認哪些要保留。使用者通常說「必要套件都要留」，然後再掃出真正的暫存/舊版本。

### Agent 資料庫異常膨脹

MiMoCode 單一 log 檔可達 8+ GB、OpenCode db 2 GB、Hermes state.db 705 MB。見 `references/agent-db-log-bloat.md`。

### 舊版本與殘留檔案清理

多個 agent 工具會累積舊版本，可安全刪除：
- **Claude Code 舊版本**：`~/.local/share/claude/versions/`（只留最新的）
- **Codex 舊版本**：`~/.codex/packages/standalone/releases/`（只留最新的）
- **Antigravity 舊二進位**：`~/.local/bin/*.old`（時間戳記結尾）
- **Hermes 狀態快照**：`~/.hermes/state-snapshots/`（更新前備份）
- **Hermes skills 備份**：`~/.hermes/skills/.curator_backups/`（每次 curator 備份）
- **Safari 更新套件**：`/Library/Updates/*/Safari*.pkg`（安裝後可刪）

清理前用 `ls -lh` 確認每個目錄只保留最新版本。

## Section 7: Complete App Removal

Remove a macOS app and ALL its traces. Most users forget CrashReporter logs and Application Scripts.

```bash
# 1. Kill running process
killall AppName 2>/dev/null || pkill -f AppName 2>/dev/null

# 2. Remove app bundle (may need sudo if owned by root)
rm -rf "/Applications/AppName.app"

# 3. Remove all user data
rm -rf ~/Library/Application\ Support/com.developer.AppName
rm -f ~/Library/Preferences/com.developer.AppName.plist
rm -rf ~/Library/Caches/com.developer.AppName
rm -rf ~/Library/Saved\ Application\ State/com.developer.AppName.savedState
rm -rf ~/Library/Containers/com.developer.AppName

# 4. Remove crash logs and extension scripts (often forgotten)
rm -f ~/Library/Application\ Support/CrashReporter/AppName_*.plist
rm -rf ~/Library/Application\ Scripts/com.developer.AppName*

# 5. Remove Launch Agents/Daemons if any
rm -f ~/Library/LaunchAgents/com.developer.AppName*.plist
rm -f /Library/LaunchDaemons/com.developer.AppName*.plist

# 6. Verify — should return 0 results
mdfind "AppName" | wc -l
```

**Finding the bundle identifier:** If you don't know the developer name:
```bash
# From an installed app
defaults read "/Applications/AppName.app/Contents/Info" CFBundleIdentifier

# From a running process
ps aux | grep AppName  # find PID, then:
cat /proc/<PID>/cmdline  # or just use mdfind
```

**Pitfall:** `sudo rm -rf` fails in Hermes terminal (no password input). If the app is owned by root, the user must remove it manually from Finder (right-click → Move to Trash) or run the command in their own terminal. If the app is owned by the current user (check with `ls -la "/Applications/AppName.app"`), `rm -rf` without sudo will work fine — always try without sudo first.

**Verification:** After removal, run `mdfind "AppName" | wc -l` — should return 0. Clean up any remaining CrashReporter or Application Scripts entries found by mdfind.

---

## Common Pitfalls

1. **macOS only** — all tools require macOS with the relevant apps
2. **Permissions needed** — Automation, Full Disk Access, Screen Recording as needed
3. **Interactive prompts** — use `pty=true` for memo/remindctl interactive modes
4. **FindMy has no CLI** — must use UI automation (AppleScript + screenshots)
5. **iMessage requires confirmation** — always confirm before sending
6. **Container deletion** — delete contents, not the container shell
7. **mo analyze --json 快取 bug** — reports stale sizes for root-owned dirs; always cross-check with `du -sh`
8. **sudo in Hermes terminal** — `sudo` requires password input which fails in Hermes; try without sudo first, or ask user to run manually
10. **舊版二進位**：`~/.local/bin/*.old`（時間戳記結尾）是舊版，可刪除
11. **舊版本累積**：Claude Code (`~/.local/share/claude/versions/`)、Codex (`~/.codex/packages/standalone/releases/`)、Safari 更新套件 (`/Library/Updates/*/Safari*.pkg`) 都會累積舊版本，只保留最新即可
10. **Old binary versions** — `~/.local/bin/*.old` files (e.g. agy.timestamp.old) are stale and can be removed

## Verification Checklist

- [ ] Correct macOS permissions granted
- [ ] CLI tools installed (memo, remindctl, imsg)
- [ ] `pty=true` used for interactive commands
- [ ] Confirmations obtained before sending messages
- [ ] Disk cleanup verified with `df -h /`
