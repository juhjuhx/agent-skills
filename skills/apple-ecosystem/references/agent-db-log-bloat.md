# Agent 資料庫與日誌異常膨脹

> 2026-07-07 實際案例整理。

## 問題

多個 AI agent 工具的資料庫和日誌可能異常膨脹，遠超正常範圍。

## 診斷順序

```bash
# 一鍵檢查所有 agent 資料庫和日誌
echo "=== Agent 資料庫與日誌檢查 ==="
echo ""
echo "--- MiMoCode ---"
du -sh ~/.local/share/mimocode/* 2>/dev/null | sort -rh | head -5
echo ""
echo "--- OpenCode ---"
du -sh ~/.local/share/opencode/* 2>/dev/null | sort -rh | head -5
echo ""
echo "--- Hermes ---"
du -sh ~/.hermes/state.db ~/.hermes/logs/* 2>/dev/null | sort -rh | head -10
echo ""
echo "--- Codex ---"
du -sh ~/.codex/* 2>/dev/null | sort -rh | head -10
echo ""
echo "--- 單一異常大 log ---"
find ~/.local/share ~/.hermes -name "*.log" -size +100M -exec ls -lh {} \; 2>/dev/null
echo "--- 舊版本 ---"
ls -lh ~/.local/share/claude/versions/ 2>/dev/null
ls -lh ~/.codex/packages/standalone/releases/ 2>/dev/null
ls -lh ~/.local/bin/*.old 2>/dev/null
ls -lh ~/.hermes/state-snapshots/ 2>/dev/null
ls -lh ~/.hermes/skills/.curator_backups/ 2>/dev/null
```

## 實際案例

### MiMoCode 單一 log 檔 8.3 GB

`~/.local/share/mimocode/log/2026-07-04T033353.log` — 單一 log 檔案 8.3 GB。
其他 log 檔都是 0B 或幾 KB。某個 session 跑太久或卡住產生。

**清理：**
```bash
rm -f ~/.local/share/mimocode/log/2026-07-04T033353.log
```

### OpenCode 資料庫 2.0 GB

`~/.local/share/opencode/opencode.db` — 歷史 session 資料庫累積到 2 GB。

**建議：** 定期清理舊 session，無內建 prune 功能需手動處理。

### Hermes state.db 705 MB

`~/.hermes/state.db` — Hermes 的 session 資料庫。

**建議：** `hermes sessions prune --older-than 30`

### Codex 日誌 128 MB + packages 679 MB

```bash
du -sh ~/.codex/* 2>/dev/null | sort -rh
# packages/standalone/releases/ 累積多個舊版本 (0.139, 0.140, 0.142)
```

## 預防建議

1. **定期檢查單一 log 檔大小** — 如果某個 log 檔 >100 MB，應該檢查
2. **資料庫定期清理** — 使用內建 prune 功能
3. **設定 log rotation** — 避免單一 log 無限增長
4. **監控 ~/.local/share/ 總大小** — 這是 agent 資料的主要存放處
5. **定期清理舊版本** — Claude Code / Codex / 舊二進位
