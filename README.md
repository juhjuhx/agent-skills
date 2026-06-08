# 🧠 Agent Skills · 167 個技能，一鍵安裝到所有 AI Agent

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/juhjuhx/agent-skills/main/install.sh)"
```

貼上、Enter，自動完成。支援 OpenCode / Claude Code / Gemini CLI / Cursor / Codex / Windsurf / Continue / Aider 與更多。

---

## 這是什麼？

167 個跨 AI Agent 的專業技能，涵蓋**設計、開發、寫作、圖像生成、調試、規劃**等工作流。每個技能是一個目錄，內含 `SKILL.md` 指令檔，讓 AI 知道如何處理特定領域任務。

```
skills/
├── visual-atelier/     # 超級視覺引擎 — PPT、信息圖、圖表
├── baoyu-imagine/      # AI 圖像生成
├── html-ppt/           # HTML 簡報
├── tdd/                # 測試驅動開發
├── diagnose/           # 系統化除錯
├── writing-plans/      # 實作計畫撰寫
├── ...
```

## 安裝

### 🚀 一鍵全裝（推薦）

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/juhjuhx/agent-skills/main/install.sh)"
```

腳本會自動：偵測你的機器上有哪些 AI agent → 為每個 agent 建立 symlink → 啟用全部技能。

### 更新

```bash
cd ~/.agents/skills && git pull
```

或者直接重新跑安裝指令即可。

## 目錄結構

| 路徑 | 說明 |
|---|---|
| `~/.agents/skills/` | Source of truth（也是 git repo） |
| `~/.config/opencode/skills/` → symlink | OpenCode |
| `~/.claude/skills/` → symlink | Claude Code |
| `~/.gemini/skills/` → symlink | Gemini CLI |
| `~/.cursor/skills/` → symlink | Cursor |
| `~/.codex/skills/` → symlink | Codex |
| `~/.windsurf/skills/` → symlink | Windsurf |
| `~/.continue/skills/` → symlink | Continue |
| `~/.aider/skills/` → symlink | Aider |
| `~/.local/share/agent-skills/` → symlink | 通用 pointer |

所有 agent 共用同一份技能，修改任一個就是全部更新。

## 授權

MIT
