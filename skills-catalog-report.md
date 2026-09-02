# Skills 目錄整理報告

> 生成時間: 2026-09-02 04:00
> 執行者: Hermes Agent (Agnes)
> 狀態: 待 Git 推送

---

## 統計概覽

| 指標 | 數值 |
|------|------|
| **總技能數** | 423 個 |
| **Hermes Skills** | 171 個 |
| **Agents Skills** | 380 個 |
| **OpenCode Skills** | 346 個 |
| **去重後總數** | 423 個 |

---

## 分類統計

| 分類 | 數量 | 說明 |
|------|------|------|
| Addy Osmani 系列 | 23 | 前端工程化、代碼審查、安全、效能優化 |
| AI Agent | 15 | 多 Agent 協調、LangChain/LangGraph |
| 創意設計 | 45 | 視覺設計、動畫、影像生成、PPT |
| HyperFrames | 12 | 動畫視頻製作框架 |
| DevOps | 38 | CI/CD、Kubernetes、Terraform |
| 安全審計 | 28 | 安全掃描、滲透測試、漏洞修復 |
| 數據科學 | 22 | 數據分析、MLops、向量資料庫 |
| 生產力工具 | 35 | Notion、Airtable、Google Workspace |
| 媒體處理 | 18 | YouTube、GIF、音訊、影片處理 |
| 研究與知識 | 12 | 學術研究、論文檢索、知識庫 |
| 社群媒體 | 15 | X/Twitter、WeChat、微博、FB |
| 台灣本地化 | 8 | 104、旋轉拍賣、台灣網站搜尋 |
| 影片製作 | 10 | 語音轉文字、字幕生成、剪輯 |
| 其他 | 162 | 未分類技能 |

---

## 安裝位置

### 主要目錄

```
~/.hermes/skills/        # Hermes Agent (171 skills)
~/.agents/skills/        # Claude Code (380 skills)
~/.config/opencode/skills/  # OpenCode (346 skills)
```

### 符號連結

部分 skills 使用符號連結共享：
- `captions-overlay` → `../../.agents/skills/captions-overlay`
- `changelog-video` → `../../.agents/skills/changelog-video`

---

## 核心 Skills 清單

### Addy Osmani 系列 (23 個)

| 名稱 | 功能 |
|------|------|
| addyosmani-api-and-interface-design | API 設計最佳實踐 |
| addyosmani-browser-testing-with-devtools | 瀏覽器測試 |
| addyosmani-ci-cd-and-automation | CI/CD 自動化 |
| addyosmani-code-review-and-quality | 代碼審查 |
| addyosmani-code-simplification | 代碼簡化 |
| addyosmani-context-engineering | 上下文工程 |
| addyosmani-debugging-and-error-recovery | 除錯與恢復 |
| addyosmani-deprecation-and-migration | 棄用與遷移 |
| addyosmani-documentation-and-adrs | 文檔與 ADR |
| addyosmani-doubt-driven-development | 懷疑驅動開發 |
| addyosmani-frontend-ui-engineering | 前端 UI 工程 |
| addyosmani-git-workflow-and-versioning | Git 工作流 |
| addyosmani-idea-refine | 想法精煉 |
| addyosmani-incremental-implementation | 增量實現 |
| addyosmani-interview-me | 面試模擬 |
| addyosmani-observability-and-instrumentation | 可觀察性 |
| addyosmani-performance-optimization | 效能優化 |
| addyosmani-planning-and-task-breakdown | 規劃與任務分解 |
| addyosmani-security-and-hardening | 安全加固 |
| addyosmani-shipping-and-launch | 發布與上線 |
| addyosmani-source-driven-development | 源驅動開發 |
| addyosmani-spec-driven-development | 規格驅動開發 |
| addyosmani-test-driven-development | 測試驅動開發 |

### 安全相關 (28 個)

| 名稱 | 功能 |
|------|------|
| security-skills | 安全審計工具集 |
| security-fuzzing | Fuzzing 測試 |
| security-passwords | 密碼列表 |
| security-patterns | 敏感數據模式 |
| security-payloads | 滲透測試 Payloads |
| security-usernames | 用戶名列表 |
| security-webshells | Web Shell 樣本 |
| addyosmani-security-and-hardening | 安全加固 |
| devsecops/* | DevSecOps 相關 |
| open-code-review | 阿里 OpenCodeReview |
| code-review-excellence | 優秀代碼審查 |
| official-code-review | 官方代碼審查 |

### HyperFrames (12 個)

| 名稱 | 功能 |
|------|------|
| hyperframes-core | 核心架構 |
| hyperframes-animation | 動畫系統 |
| hyperframes-audio | 音訊處理 |
| hyperframes-cli | CLI 工具 |
| hyperframes-creative | 創意設計 |
| hyperframes-keyframes | 關鍵幀 |
| hyperframes-registry | 註冊表 |
| motion-doctrine | 動效教義 |
| motion-graphics | 動效圖形 |
| seam-craft | 縫合技巧 |
| general-video | 通用影片 |
| video-shot-demos | 分鏡演示 |

### 影片製作 (10 個)

| 名稱 | 功能 |
|------|------|
| local-speech-transcription | 本地語音轉文字 |
| local-voice-to-text-app | Tauri 語音轉文字 App |
| voice-transcription-app-workflow | 語音轉文字工作流 |
| embedded-captions | 內嵌字幕 |
| captions-overlay | 字幕覆蓋 |
| changelog-video | 更新日誌影片 |
| pr-to-video | PR 轉影片 |
| talking-head-recut | 頭像重剪 |
| product-launch-video | 產品發布影片 |
| music-to-video | 音樂轉影片 |

---

## 使用方法

### 載入 Skills

```bash
# Hermes
hermes skills list
hermes skills view <skill-name>

# OpenCode
opencode skills list
```

### 使用 Skill

```python
# 在對話中自動載入
skill_view(name='skill-name')

# 或在提示中使用
"使用 skill: skill-name 來..."
```

### 遷移 Skills

```bash
# 同步到所有 agent
cd ~/.agents/skills
./skill-manager.sh sync

# 單獨同步
cp -r skill-name ~/.hermes/skills/
cp -r skill-name ~/.config/opencode/skills/
```

---

## Git 推送準備

### 目前狀態

| 組件 | 狀態 |
|------|------|
| Git | ✅ 已安裝 (v2.39.5) |
| GitHub CLI | ✅ 已安裝 |
| gh auth | ⚠️ Token 過期 |
| Repo | ⏳ 等待用戶提供 |

### 準備好的檔案

```
~/Desktop/
├── skills-catalog-full.md      # 完整目錄報告
├── skills-catalog-generator.py # 生成器腳本
├── voice-transcriber-architecture-complete.html  # 架構圖
└── voice-transcriber-architecture-complete.md    # 架構說明
```

### 待執行操作

1. 用戶提供 GitHub Repo URL 和 Token
2. 初始化 git 倉庫
3. 添加 remote
4. 提交並推送

---

## 下一步

請提供以下資訊以繼續：

```bash
# GitHub Repo URL
https://github.com/username/repo-name.git

# Access Token (Personal Access Token with repo scope)
ghp_xxxxxxxxxxxxxxxxxxxx
```

一旦提供，我將：
1. 創建本地 git 倉庫
2. 添加所有架構文件
3. 提交 commit
4. 推送到 remote

---

**狀態**: 準備就緒，等待 GitHub token 以完成 git 推送。
