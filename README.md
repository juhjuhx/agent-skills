# Agent Skills Matrix

One canonical skill library. Native workflows for multiple AI agents.

The current machine-readable baseline contains **214 indexed skills**, exposed through **10 installer categories** and **9 registry taxonomy tags**. The registry is authoritative; the installer categories are a separate selection projection. Existing shared-skill workflows support **OpenCode / Claude Code / Gemini CLI / Cursor / Codex / Windsurf / Continue / Aider** and more. Agent Skills Matrix v3 adds native adapter contracts for **Codex / Claude Code / OpenCode / Hermes / MiMo Code / ZCode / DeepSeek Harness** without forking the canonical skills.

> Counts are derived from `.superpowers/SKILLS_INDEX.json` and `categories.json`. The detailed catalog below is a curated presentation; machine-readable metadata wins when prose drifts.

---

## Quick Install

> `install.sh` 是歷史相容的分類安裝器，會依其舊流程寫入使用者範圍；它不是
> v3 Phase 3P 的產品流程。v3 的新 clone 請先閱讀
> [`docs/v3/CLONE_TO_USE.md`](docs/v3/CLONE_TO_USE.md)：它先做 static diagnostics，
> PROJECT apply 使用明確專案根，Claude USER apply 僅在 virtual HOME 測試環境可用。
> 本穩定化 epoch 不執行 real-home 安裝。

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/juhjuhx/agent-skills/main/install.sh)"
```

Without flags → **interactive mode**: pick which categories to install / 不帶參數 → **互動模式**：選擇要安裝的分類。

## Installation Options

| Command | What it installs / 安裝內容 |
|---|---|
| `bash install.sh` | Interactive — pick your categories / 互動模式 — 選擇分類 |
| `bash install.sh --minimal` | Essential + Coding only (59 unique manifest skills) / 僅 Essential + Coding |
| `bash install.sh --default` | Essential + Coding + Design (84 unique manifest skills) / Essential + Coding + Design |
| `bash install.sh --all` | All 10 installer categories (165 unique manifest skills) / 全部 10 分類 |
| `bash install.sh --category essential,coding,design` | Specific categories only / 指定分類 |

---

## Profiles

| Profile | Categories / 包含分類 | Description / 說明 |
|---|---|---|
| `minimal` | essential, coding | Minimum viable agent / 最小可用 Agent |
| `default` | essential, coding, design | Recommended for most developers / 大多數開發者推薦 |
| `full` | All 10 installer categories / 全部 10 分類 | Install every category-listed skill / 安裝分類清單中的全部技能 |

---

## Architecture v3

Agent Skills Matrix v3 is now a tested static/productization candidate for the
**Canonical Core + Generated Native Adapters** architecture. The repository has a
metadata-first Stage Router, deterministic runtime projections, a safe PROJECT
installer, and a Claude-only MANAGED_COPY virtual-HOME installer. Real-home mutation,
live model execution, and model/effort routing remain explicitly gated.

### Supported runtime targets

| Runtime | Adapter guide |
|---|---|
| Codex | [native Codex adapter](docs/v3/agents/CODEX.md) |
| Claude Code | [native Claude Code adapter](docs/v3/agents/CLAUDE_CODE.md) |
| OpenCode | [native OpenCode adapter](docs/v3/agents/OPENCODE.md) |
| Hermes | [native Hermes adapter](docs/v3/agents/HERMES.md) |
| MiMo Code | [native MiMo Code adapter](docs/v3/agents/MIMO_CODE.md) |
| ZCode | [native ZCode adapter](docs/v3/agents/ZCODE.md) |
| DeepSeek Harness | [native DeepSeek Harness adapter](docs/v3/agents/DEEPSEEK_HARNESS.md) |

These are v3 contract targets, not claims that every adapter is implemented or installed today.

### How routing works

```text
Task Intake
  → Risk / Complexity / Ambiguity
  → TaskSpec
  → Stage Planner
  → Stage-local Skill Router
  → Agent Adapter
  → Model Profile
  → Execution
  → Evidence Gate
  → Reroute / Next Stage
```

Stages route independently: Understand, Research, Design, Plan, Implement, Review, Verify, Harden, and Handoff/Learn. A typical stage uses 3–7 relevant skills; a complex stage may use 5–10, and a complex project may naturally produce 30–50+ activations. These are guidance ranges, not quotas: unrelated skills are never loaded to satisfy a number, and skill reuse is expected.

### Documentation

- [v3 documentation index](docs/v3/README.md)
- [Architecture and ADRs](docs/v3/ARCHITECTURE.md)
- [Using-Superpowers v3](docs/v3/USING_SUPERPOWERS.md)
- [Stage Router](docs/v3/STAGE_ROUTER.md)
- [Skill Metadata and Graph](docs/v3/SKILL_METADATA_AND_GRAPH.md)
- [Agent and Model contracts](docs/v3/AGENT_ADAPTER_CONTRACT.md)
- [Learning, evaluation, provenance, and review](docs/v3/LEARNING_AND_EVALS.md)

The legacy `install.sh` remains available for compatibility, but it is not the v3
installer authority. The current v3 product flow is documented in
[`docs/v3/CLONE_TO_USE.md`](docs/v3/CLONE_TO_USE.md); it does not change
`.superpowers/ROUTING_POLICY.yaml`, invoke a model, or enable real-home mutation.

## Complete Skills Catalog

### 🧰 Essential — 基礎必備

Foundational skills every agent should have / 每個 Agent 都應具備的基礎技能。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `agent-development` | Create and configure agents / 建立與設定 Agent | Building custom agents / 建立自訂 Agent |
| `command-development` | Create slash commands / 建立斜線命令 | Adding CLI commands / 新增 CLI 命令 |
| `find-skills` | Discover and install skills / 發現並安裝 Skills | Looking for new capabilities / 尋找新功能 |
| `output-skill` | Force complete code output / 強制完整輸出 | Ensuring no truncation / 確保代碼不被截斷 |
| `handoff` | Compact conversation for handoff / 壓縮對話交棒 | Transferring to another agent / 交棒給其他 Agent |
| `hook-development` | Create event hooks / 建立事件 Hook | Automating workflows / 自動化工作流 |
| `mcp-integration` | Integrate MCP servers / 整合 MCP Server | Connecting external services / 連接外部服務 |
| `plugin-settings` | Configure plugin settings / 設定 Plugin 設定檔 | Customizing plugin behavior / 自訂 Plugin 行為 |
| `plugin-structure` | Scaffold plugin architecture / 建立 Plugin 架構 | Creating new plugins / 建立新 Plugin |
| `skill-development` | Create new skills / 建立新 Skill | Authoring skills / 撰寫 Skill |
| `using-superpowers` | Meta-skill for skill discovery / Skill 發現元技能 | Starting any session / 任何 session 開始時 |
| `write-a-skill` | Write skills with proper structure / 以正確結構撰寫 Skill | Creating skills / 建立 Skill |
| `writing-rules` | Write hookify rules / 撰寫 hookify 規則 | Configuring hooks / 設定 Hook |
| `writing-skills` | Verify skills work / 驗證 Skill 正常運作 | Before deployment / 部署前驗證 |

---

### 💻 Coding — 程式開發

Code review, debugging, TDD, architecture, logic analysis, algorithms / 程式碼審查、除錯、TDD、架構、邏輯分析、演算法。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `brainstorming` | Explore ideas before implementation / 實作前探索構想 | Before coding / 寫碼前 |
| `brooks-brooks-audit` | Architecture audit with 12 classic books / 基於 12 本經典書的架構審計 | Reviewing structure / 審查結構 |
| `brooks-brooks-debt` | Tech debt assessment / 技術債評估 | Prioritizing refactoring / 重構優先級 |
| `brooks-brooks-harness` | Maintenance orchestrator for brooks-lint / brooks-lint 維護編排 | Maintaining brooks-lint / 維護 brooks-lint |
| `brooks-brooks-health` | Codebase health dashboard / 程式碼庫健康儀表板 | Overall quality check / 整體品質檢查 |
| `brooks-brooks-review` | PR code review with decay risk surfacing / PR 審查與劣化風險揭示 | Reviewing PRs / 審查 PR |
| `brooks-brooks-sweep` | Full-sweep: audit + auto-fix / 全面掃描：審計 + 自動修復 | Cleaning up entire project / 清理整個專案 |
| `brooks-brooks-test` | Test quality review / 測試品質審查 | Reviewing test suite / 審查測試套件 |
| `brooks-new-skill` | Scaffold brooks-lint skill / 建立 brooks-lint skill | Adding brooks-lint modes / 新增 brooks-lint 模式 |
| `brooks-release` | Cut brooks-lint release / 發佈 brooks-lint | Releasing new version / 發佈新版本 |
| `claude-opus-4-5-migration` | Migrate to Opus 4.5 / 遷移至 Opus 4.5 | Updating model strings / 更新模型字串 |
| `code-review-skill-main` | Comprehensive code review for 10 languages / 10 種語言全方位審查 | Reviewing code / 審查程式碼 |
| `complexity-cuts` | Refactor poor Big-O complexity / 重構 Big-O 效能 | Optimizing slow code / 最佳化慢速代碼 |
| `debugging-code` | Interactive debugger with breakpoints / 互動式除錯器 | Runtime inspection / 時式檢查 |
| `diagnose` | Systematic diagnosis for hard bugs / 疑難 bug 系統性診斷 | Hard bugs / 疑難 bug |
| `dispatching-parallel-agents` | Spawn parallel agents / 派發並行 Agent | Multiple independent tasks / 多個獨立任務 |
| `executing-plans` | Execute written implementation plans / 執行實作計畫 | Following a plan / 按計畫執行 |
| `finishing-a-development-branch` | Complete dev branch integration / 完成開發分支整合 | After implementation / 實作完成後 |
| `improve-codebase-architecture` | Find refactoring targets / 找重構目標 | Improving codebase / 改善程式碼庫 |
| `invariant-guard` | Algorithm correctness guard / 演算法正確性守衛 | Writing complex algorithms / 寫複雜演算法 |
| `lemmaly` | Algorithmic thinking before code / 寫碼前演算法思維 | Before writing loops/collections / 寫迴圈/集合前 |
| `logic-logic-diff` | Compare two code versions semantically / 兩版本語意比對 | Verifying refactors / 驗證重構 |
| `logic-logic-explain` | Step-by-step code execution trace / 逐步執行追蹤 | Understanding code / 理解程式碼 |
| `logic-logic-fix-all` | Autonomous repo-wide audit and fix / 自動全倉審計修復 | Fixing all bugs / 修復所有 bug |
| `logic-logic-health` | Codebase logic health dashboard / 程式碼庫邏輯健康儀表板 | Health overview / 健康概覽 |
| `logic-logic-locate` | Root cause of confirmed failure / 確認失敗的根因 | Tracking crashes / 追蹤崩潰 |
| `logic-logic-review` | Single-file logic bug finder / 單檔案邏輯 bug 尋找 | Reviewing functions / 審查函式 |
| `mathguard` | Approximate math for large-scale data / 大規模近似數學 | n >= 10^6 / 大數據量 |
| `official-code-review` | PR code review / PR 程式碼審查 | Reviewing pull requests / 審查 Pull Request |
| `official-feature-dev` | 3-agent feature development / 3 Agent 功能開發 | End-to-end features / 端到端功能 |
| `pr-review-toolkit` | 6 professional review agents / 6 個專業審查 Agent | Comprehensive PR review / 全面 PR 審查 |
| `prototype` | Throwaway prototype / 拋棄式原型 | Exploring designs / 探索設計 |
| `receiving-code-review` | Handle code review feedback / 處理審查反饋 | After receiving feedback / 收到反饋後 |
| `requesting-code-review` | Request code review / 請求審查 | Before merging / 合併前 |
| `runaway-guard` | Prevent API runaway costs / 防止 API 失控費用 | When calling paid APIs / 呼叫付費 API 時 |
| `setup-matt-pocock-skills` | Setup skill context / 設定 Skill 上下文 | First use of skills / 首次使用 skill |
| `subagent-driven-development` | Execute via subagents / 透過 Subagent 執行 | Large implementation plans / 大型實作計畫 |
| `systematic-debugging` | Root-cause first debugging / 先找根因再修復 | Any bug / 任何 bug |
| `tdd` | Test-driven development / 測試驅動開發 | Implementing features / 實作功能 |
| `test-driven-development` | Test-driven development / 測試驅動開發 | Before writing code / 寫碼前 |
| `triage` | Issue state machine workflow / 問題狀態機工作流 | Managing issues / 管理問題 |
| `using-git-worktrees` | Git worktree for isolation / Git worktree 隔離 | Feature work / 功能開發 |
| `verification-before-completion` | Verify before claiming done / 完成前驗證 | Before committing / 提交前 |
| `writing-plans` | Write implementation plans / 撰寫實作計畫 | Planning work / 規劃工作 |
| `zoom-out` | High-level perspective / 高層次視角 | Unfamiliar code / 不熟悉的程式碼 |

---

### 🎨 Design — 設計

UI/UX, brand, design systems, frontend aesthetics, accessibility / UI/UX、品牌、設計系統、前端美學、無障礙。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `baseline-ui` | Validate animation, typography, accessibility / 驗證動畫、字型、無障礙 | UI audit / UI 審計 |
| `brand` | Brand identity and consistency / 品牌識別與一致性 | Brand work / 品牌工作 |
| `brand-guidelines` | Anthropic brand colors / Anthropic 品牌色彩 | Applying Anthropic brand / 套用 Anthropic 品牌 |
| `brandkit` | Premium brand-kit generation / 高端品牌套件生成 | Brand guidelines / 品牌規範 |
| `brutalist-skill` | Industrial brutalist UI / 野獸派 UI | Raw industrial aesthetic / 原始工業美學 |
| `claude-design` | One-off HTML artifacts / 一次性 HTML 作品 | Landing, deck, prototype / 落地頁、簡報、原型 |
| `design` | Unified design skill (55 logo styles) / 統一設計 Skill | Design, logo, banners / 設計、logo、banner |
| `design-md` | Google DESIGN.md spec files / Google DESIGN.md 規格檔 | Token spec files / Token 規格檔 |
| `design-system` | Three-layer design token architecture / 三層設計 Token 架構 | Design systems / 設計系統 |
| `fixing-accessibility` | Audit and fix HTML accessibility / 審計並修復無障礙 | WCAG compliance / WCAG 合規 |
| `fixing-metadata` | Audit HTML metadata (SEO, OG) / 審計 HTML metadata | SEO optimization / SEO 最佳化 |
| `fixing-motion-performance` | Audit animation performance / 審計動畫效能 | Jank / stutter issues / 卡頓問題 |
| `frontend-design` | Production-grade frontend / 生產級前端 | Building webpages / 建構網頁 |
| `gpt-tasteskill` | Elite UX/UI + GSAP motion / 精英 UX/UI + GSAP 動效 | Premium landing pages / 高端落地頁 |
| `image-to-code-skill` | Image to website code / 圖片轉網站代碼 | From mockup / 從 mockup |
| `imagegen-frontend-mobile` | Mobile app screen images / 手機 App 畫面圖 | Mobile design / 手機設計 |
| `imagegen-frontend-web` | Web design reference images / 網頁設計參考圖 | Web design / 網頁設計 |
| `minimalist-skill` | Premium minimalist UI / 高端極簡 UI | Clean editorial design / 淨簡編輯設計 |
| `popular-web-designs` | 54 real design systems as HTML/CSS / 54 個真實設計系統 | Reference / 參考 |
| `redesign-skill` | Upgrade existing websites / 升級既有網站 | Improving existing UI / 改善既有 UI |
| `soft-skill` | Awwwards-tier UI / Awwwards 級 UI | Premium design / 高端設計 |
| `stitch-skill` | Google Stitch DESIGN.md / Google Stitch DESIGN.md | Agent-friendly tokens / Agent 友善 Token |
| `styleseed` | Design system + motion seeds / 設計系統 + 動畫種子 | Brand skins / 品牌外觀 |
| `taste-skill` | Anti-slop frontend design / 反 slop 前端設計 | Avoiding AI generic look / 避免 AI 通用感 |
| `taste-skill-v1` | Original taste-skill v1 / 原始 taste-skill v1 | Backward compatibility / 向後相容 |
| `ui-styling` | shadcn/ui + Tailwind styling / shadcn/ui + Tailwind 樣式 | UI components / UI 組件 |
| `ui-ux-pro-max` | UI/UX intelligence (50+ styles) / UI/UX Intelligence | Any UI work / 任何 UI 工作 |

---

### 🖼️ Visual Media — 視覺媒體

Image generation, diagrams, infographics, banners, slide decks, comics / 圖片生成、圖表、信息圖、橫幅、幻燈片、漫畫。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `agnes-vision` | Vision models for image analysis / 視覺模型圖片分析 | Analyzing images / 分析圖片 |
| `algorithmic-art` | Generative art with p5.js / p5.js 生成藝術 | Creating algorithmic art / 建立算法藝術 |
| `banner-design` | Banner design (22 styles) / 橫幅設計 | Social media, ads / 社群、廣告 |
| `baoyu-article-illustrator` | Article illustration / 文章配圖 | Adding images to articles / 為文章配圖 |
| `baoyu-comic` | Educational comics / 教育漫畫 | Knowledge comics / 知識漫畫 |
| `baoyu-compress-image` | Image compression / 圖片壓縮 | Optimizing images / 最佳化圖片 |
| `baoyu-cover-image` | Article cover images / 文章封面圖 | Generating covers / 生成封面 |
| `baoyu-danger-gemini-web` | Gemini Web API for image gen / Gemini Web API 圖片生成 | When other backends unavailable / 其他後端不可用時 |
| `baoyu-diagram` | Dark-themed SVG diagrams / 深色 SVG 圖表 | Architecture, flowcharts / 架構圖、流程圖 |
| `baoyu-image-cards` | Xiaohongshu image cards / 小紅書圖文卡片 | Social media infographic / 社群信息圖 |
| `baoyu-image-gen` | AI image generation (deprecated) / AI 圖片生成（已棄用） | Use baoyu-imagine / 改用 baoyu-imagine |
| `baoyu-imagine` | AI image generation (multi-API) / AI 圖片生成（多 API） | Text-to-image / 文字轉圖片 |
| `baoyu-infographic` | Infographics (21 layouts x 21 styles) / 信息圖 | Data visualization / 數據視覺化 |
| `baoyu-slide-deck` | Slide deck images / 幻燈片圖片 | Presentations / 簡報 |
| `baoyu-xhs-images` | Xiaohongshu images (deprecated) / 小紅書圖片（已棄用） | Use baoyu-image-cards / 改用 baoyu-image-cards |
| `comfyui` | ComfyUI image/video/audio / ComfyUI 圖片/影片/音訊 | Local generation / 本地生成 |
| `html-ppt` | HTML presentations / HTML 簡報 | Interactive slides / 互動式投影片 |
| `slides` | Data-driven HTML slides / 數據驅動 HTML 投影片 | Strategic presentations / 策略簡報 |
| `visual-atelier` | Visual engine (slides, charts) / 視覺引擎 | Any visual output / 任何視覺輸出 |

---

### 📝 Content — 內容

Translation, markdown processing, URL fetching, YouTube transcripts / 翻譯、Markdown 處理、URL 抓取、YouTube 字幕。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `baoyu-danger-x-to-markdown` | X/Twitter to markdown / X 貼文轉 Markdown | Saving tweets / 儲存推文 |
| `baoyu-format-markdown` | Format markdown with frontmatter / 格式化 Markdown | Beautifying articles / 美化文章 |
| `baoyu-markdown-to-html` | Markdown to styled HTML / Markdown 轉 HTML | WeChat-compatible output / 微信兼容輸出 |
| `baoyu-translate` | Translation (3 modes) / 翻譯（3 種模式） | Chinese-English translation / 中英翻譯 |
| `baoyu-url-to-markdown` | URL to markdown / URL 轉 Markdown | Saving webpages / 儲存網頁 |
| `baoyu-youtube-transcript` | YouTube transcript download / YouTube 字幕下載 | Getting video text / 取得影片文字 |
| `humanizer` | Strip AI-isms, add real voice / 去除 AI 味 | Making text natural / 讓文字自然 |
| `youtube-content` | YouTube transcripts to summaries / YouTube 字幕轉摘要 | Content repurposing / 內容再利用 |

---

### 📱 Social Media — 社群媒體

Posting to WeChat, Weibo, X/Twitter / 發佈到微信、微博、X/Twitter。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `baoyu-post-to-wechat` | Post to WeChat Official Account / 發佈微信公眾號 | WeChat articles / 微信文章 |
| `baoyu-post-to-weibo` | Post to Weibo / 發佈微博 | Weibo posts / 微博貼文 |
| `baoyu-post-to-x` | Post to X (Twitter) / 發佈 X | Tweets and articles / 推文和文章 |
| `baoyu-wechat-summary` | WeChat group chat digest / 微信群聊摘要 | Summarizing group chats / 總結群聊 |
| `xurl` | X/Twitter CLI / X/Twitter CLI | Terminal-based X ops / 終端操作 X |

---

### 🎬 Video & Cinema — 影片與電影

Cinematic prompts, video presentations, Seedance direction / 電影級 prompt、影片簡報、Seedance 導演。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `banana-pro-director` | Character outfit and scene plates / 角色服裝與場景板 | Character reference sheets / 角色參考表 |
| `cinema-worldbuilder` | Seedance video prompt director / Seedance 影片 Prompt 導演 | Cinematic scenes / 電影級場景 |
| `html-canvas-to-video` | Canvas animation to video / Canvas 動畫轉影片 | Recording animations / 錄製動畫 |
| `manim-video` | Manim CE math animations / Manim CE 數學動畫 | 3Blue1Brown style / 3Blue1Brown 風格 |
| `web-video-presentation` | Article to video-style webpage / 文章轉影片式網頁 | Video-like presentations / 影片式簡報 |

---

### 🧊 Three.js 3D — Three.js 3D

Complete Three.js 3D graphics pipeline / 完整 Three.js 3D 圖形管線。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `threejs-animation` | Animation: keyframe, skeletal / 動畫：關鍵幀、骨骼 | Animating objects / 物件動畫 |
| `threejs-fundamentals` | Scene setup: cameras, renderer / 場景設定：相機、渲染器 | Setting up 3D scenes / 建立 3D 場景 |
| `threejs-geometry` | Geometry creation / 幾何體建立 | Creating 3D shapes / 建立 3D 造型 |
| `threejs-interaction` | Raycasting, controls / 射線投射、控制 | User interaction / 使用者互動 |
| `threejs-lighting` | Lighting and shadows / 燈光與陰影 | Adding lights / 新增燈光 |
| `threejs-loaders` | GLTF, texture loading / GLTF、紋理載入 | Loading 3D models / 載入 3D 模型 |
| `threejs-materials` | PBR, basic materials / PBR、基礎材質 | Styling meshes / 設定網格外觀 |
| `threejs-postprocessing` | Bloom, DOF, screen effects / 泛光、景深、螢幕效果 | Visual effects / 視覺效果 |
| `threejs-shaders` | GLSL, ShaderMaterial / GLSL、ShaderMaterial | Custom shaders / 自訂著色器 |
| `threejs-textures` | Texture types, UV mapping / 紋理類型、UV 映射 | Working with images / 處理圖片 |

---

### ⚡ Pro Workflow — 進階工作流

Advanced productivity: context management, wiki, commits, session, LLM council / 進階效率：上下文管理、Wiki、提交、Session、LLM 協商。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `pro-agent-teams` | Multi-agent team coordination / 多 Agent 團隊協調 | Multiple sessions / 多個 session |
| `pro-auto-setup` | Auto-configure quality gates / 自動設定品質閘控 | Onboarding new project / 新專案初始化 |
| `pro-batch-orchestration` | Decompose large changes / 拆分大型變更 | 10+ files with same pattern / 10+ 檔案相同模式 |
| `pro-bug-capture` | Capture defect as GitHub issue / 捕捉缺陷為 Issue | Reporting bugs / 報告 bug |
| `pro-compact-guard` | Smart context compaction / 智能上下文壓縮 | Before manual compact / 手動壓縮前 |
| `pro-context-engineering` | Context engineering master / 上下文工程大師 | Starting new session / 開始新 session |
| `pro-context-optimizer` | Optimize token usage / 最佳化 Token 使用 | Slow sessions / session 變慢時 |
| `pro-cost-tracker` | Track session costs / 追蹤 Session 成本 | Checking spend / 檢查花費 |
| `pro-deslop` | Remove AI code slop / 移除 AI 程式碼冗餘 | Cleaning up / 清理 |
| `pro-file-watcher` | File watching hooks / 檔案監聽 Hook | Reactive workflows / 響應式工作流 |
| `pro-insights` | Session analytics / Session 分析 | Checking stats / 檢查統計 |
| `pro-learn-rule` | Persistent learning rules / 持久化學習規則 | After mistakes / 錯誤後 |
| `pro-llm-council` | Multi-LLM deliberation / 多 LLM 協商 | High-stakes reviews / 高風險審查 |
| `pro-llm-gate` | LLM quality verification / LLM 品質驗證 | Quality guardrails / 品質閘控 |
| `pro-mcp-audit` | Audit MCP servers / 審計 MCP Server | Slow sessions / session 變慢時 |
| `pro-module-map` | One-screen code map / 一頁式程式碼地圖 | Unfamiliar code / 不熟悉程式碼 |
| `pro-orchestrate` | Multi-phase feature orchestration / 多階段功能編排 | Complex features / 複雜功能 |
| `pro-parallel-worktrees` | Git worktree parallel sessions / Git worktree 並行 | Zero dead time / 零空閒時間 |
| `pro-permission-tuner` | Optimize permission rules / 最佳化權限規則 | Too many prompts / 太多提示時 |
| `pro-plan-interrogate` | Stress-test a plan / 壓力測試計畫 | Before implementation / 實作前 |
| `pro-pro-workflow` | Complete AI coding workflow / 完整 AI 編碼工作流 | Full workflow / 完整工作流 |
| `pro-replay-learnings` | Surface past learnings / 顯示歷史教訓 | Starting a task / 開始任務時 |
| `pro-safe-mode` | Prevent destructive operations / 防止破壞性操作 | Safety-critical work / 安全關鍵工作 |
| `pro-session-handoff` | Session handoff document / Session 交棒文件 | Ending session / 結束 session 時 |
| `pro-skill-optimizer` | Offline skill training / 離線 Skill 訓練 | Improving skills / 改善 skill |
| `pro-smart-commit` | Quality gates + commit / 品質閘控 + 提交 | Ready to commit / 準備提交時 |
| `pro-sprint-status` | Parallel work status tracking / 並行工作狀態追蹤 | Multiple sessions / 多個 session |
| `pro-survey-generator` | Literature survey / 文獻調查 | Research topics / 研究主題 |
| `pro-thoroughness-scoring` | Thoroughness rating / 完整度評分 | Deciding quality level / 決定品質等級 |
| `pro-token-efficiency` | Reduce token waste / 減少 Token 浪費 | Cost optimization / 成本最化 |
| `pro-wiki-builder` | Build research wiki / 建立研究 Wiki | Long-lived knowledge base / 長期知識庫 |
| `pro-wiki-query` | Query wiki via FTS5 / 透過 FTS5 查詢 Wiki | Answering from wiki / 從 Wiki 回答 |
| `pro-wiki-research-loop` | Auto-grow wiki / 自動成長 Wiki | Research / 自動研究 |
| `pro-wiki-viewer` | Wiki HTML viewer / Wiki HTML 瀏覽器 | Browsing wiki / 瀏覽 Wiki |
| `pro-wrap-up` | End-of-session ritual / Session 結束儀式 | Finishing coding / 完成編碼時 |

---

### 🔧 Other Tools — 其他工具

Miscellaneous: caveman mode, grilling, releases, issues / 雜項：簡潔模式、壓力測試、發佈、Issue。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `caveman` | Ultra-compressed communication / 超精簡通訊 | Saving tokens / 節省 Token |
| `grill-me` | Stress-test your plan / 壓力測試你的計畫 | Before implementation / 實作前 |
| `grill-with-docs` | Grill against domain model / 針對領域模型壓力測試 | With documented decisions / 有文件記錄的決策時 |
| `release-skills` | Universal release workflow / 通用發佈工作流 | Cutting releases / 發佈新版本 |
| `to-issues` | Plan to GitHub issues / 計畫轉 GitHub Issue | Breaking down work / 拆分工作 |
| `to-prd` | Conversation to PRD / 對話轉 PRD | Creating PRDs / 建立 PRD |

---

### 🔬 Engineering Workflow (addyosmani) — 工程工作流

Production-grade engineering lifecycle: Define → Plan → Build → Verify → Review → Ship / 生產級工程生命週期：定義 → 規劃 → 建構 → 驗證 → 審查 → 發佈。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `addy-api-and-interface-design` | Stable API and interface design / 穩定 API 與介面設計 | Designing APIs / 設計 API |
| `addy-browser-testing-with-devtools` | Real browser testing via Chrome DevTools / 透過 Chrome DevTools 真實瀏覽器測試 | Browser debugging / 瀏覽器除錯 |
| `addy-ci-cd-and-automation` | CI/CD pipeline setup / CI/CD 管線設定 | Automating builds / 自動化建構 |
| `addy-code-review-and-quality` | Multi-axis code review / 多維度程式碼審查 | Before merging / 合併前 |
| `addy-code-simplification` | Simplify code for clarity / 簡化程式碼提升清晰度 | Refactoring / 重構 |
| `addy-context-engineering` | Optimize agent context setup / 最佳化 Agent 上下文設定 | New session / 新 session |
| `addy-debugging-and-error-recovery` | Systematic root-cause debugging / 系統性根因除錯 | Tests fail, builds break / 測試失敗、建構中斷 |
| `addy-deprecation-and-migration` | Manage deprecation and migration / 管理廢棄與遷移 | Removing old systems / 移除舊系統 |
| `addy-documentation-and-adrs` | Record decisions and ADRs / 記錄決策與 ADR | Architectural decisions / 架構決策 |
| `addy-doubt-driven-development` | Adversarial review before decisions / 決策前對抗性審查 | High-stakes logic / 高風險邏輯 |
| `addy-frontend-ui-engineering` | Production-quality UI / 生產級 UI | Building user interfaces / 建構使用者介面 |
| `addy-git-workflow-and-versioning` | Git workflow practices / Git 工作流實踐 | Any code change / 任何代碼變更 |
| `addy-idea-refine` | Refine raw ideas / 提煉原始構想 | Vague ideas / 構想模糊時 |
| `addy-incremental-implementation` | Deliver changes incrementally / 增量交付變更 | Large changes / 大型變更 |
| `addy-interview-me` | Extract real intent / 提取真實意圖 | Underspecified asks / 需求不明確時 |
| `addy-observability-and-instrumentation` | Production visibility / 生產可見性 | Adding logging, metrics / 新增日誌、指標 |
| `addy-performance-optimization` | Performance optimization / 效能最佳化 | Performance regressions / 效能回歸 |
| `addy-planning-and-task-breakdown` | Break work into tasks / 將工作拆分為任務 | Planning / 規劃 |
| `addy-security-and-hardening` | Security hardening / 安全加固 | Handling user input / 處理使用者輸入 |
| `addy-shipping-and-launch` | Production launch prep / 上線部署準備 | Deploying / 部署 |
| `addy-source-driven-development` | Source-cited code / 基於文件的程式碼 | Framework correctness / 框架正確性 |
| `addy-spec-driven-development` | Create specs before coding / 先建立規格再寫碼 | New projects / 新專案 |
| `addy-test-driven-development` | Test-driven development / 測試驅動開發 | Implementing logic / 實作邏輯 |
| `addy-using-agent-skills` | Skill discovery and invocation / Skill 發現與調用 | Starting session / 開始 session |

---

### 📚 Knowledge & Utilities — 知識與工具

Knowledge bases, integrations, and miscellaneous tools / 知識庫、整合、與雜項工具。

| Skill | Description / 說明 | When to use / 使用時機 |
|-------|---------------------|----------------------|
| `blogwatcher` | Monitor blogs and RSS feeds / 監控部落格與 RSS | Blog monitoring / 部落格監控 |
| `codebase-inspection` | LOC, languages, ratios / 代碼行數、語言、比率 | Codebase overview / 程式碼庫概覽 |
| `godmode` | Jailbreak LLMs / LLM 越獄 | Exploring boundaries / 探索邊界 |
| `google-workspace` | Gmail, Calendar, Drive / Gmail、Calendar、Drive | Google services / Google 服務 |
| `himalaya` | IMAP/SMTP email CLI / IMAP/SMTP email CLI | Email from terminal / 終端收發信 |
| `huggingface-hub` | HuggingFace CLI / HuggingFace CLI | Model download/upload / 模型下載/上傳 |
| `image-to-code-skill` | Image to website code / 圖片轉網站代碼 | From mockup / 從 mockup |
| `jupyter-live-kernel` | Live Jupyter kernel / 即時 Jupyter Kernel | Python iteration / Python 迭代 |
| `knowledge-consolidation` | Knowledge archive builder / 知識庫建立器 | Multi-source research / 多源研究 |
| `llm-wiki` | Karpathy-pattern LLM wiki / Karpathy 模式 LLM Wiki | Building knowledge base / 建立知識庫 |
| `macos-cleanup` | macOS disk cleanup / macOS 磁碟清理 | Freeing space / 釋放空間 |
| `maps` | Geocode, POIs, routes / 地理編碼、POI、路線 | Map operations / 地圖操作 |
| `messaging-gateway` | Chatbot on messaging platforms / 訊息平台 Bot | Telegram, Discord, LINE / Telegram、Discord、LINE |
| `multi-agent-handoff` | Cross-agent handoff / 跨 Agent 接手 | Agent crashes / Agent 崩潰時 |
| `multi-agent-orchestrator` | Multi-agent task store / 多 Agent 任務存儲 | Agent routing / Agent 路由 |
| `nano-pdf` | Edit PDF text/typos / 編輯 PDF 文字 | PDF corrections / PDF 修正 |
| `notion` | Notion API + CLI / Notion API + CLI | Notion pages / Notion 頁面 |
| `obsidian` | Obsidian vault operations / Obsidian 筆記庫操作 | Note management / 筆記管理 |
| `ocr-and-documents` | Extract text from PDFs/scans / 從 PDF/掃描提取文字 | OCR / OCR |
| `openhue` | Philips Hue light control / Philips Hue 燈光控制 | Smart home / 智慧家庭 |
| `plan` | Plan mode (write plans) / 計畫模式 | Writing plans / 撰寫計畫 |
| `polymarket` | Polymarket queries / Polymarket 查詢 | Market data / 市場數據 |
| `powerpoint` | Read/write .pptx decks / 讀寫 .pptx 簡報 | PowerPoint operations / PowerPoint 操作 |
| `pretext` | @chenglou/pretext text layout / @chenglou/pretext 文字排版 | ASCII art, typography / ASCII 藝術、排版 |
| `songsee` | Audio spectrograms / 音訊頻譜 | Audio analysis / 音訊分析 |
| `spike` | Throwaway experiments / 拋棄式實驗 | Validating ideas / 驗證想法 |
| `teams-meeting-pipeline` | Teams meeting summaries / Teams 會議摘要 | Meeting notes / 會議紀錄 |
| `touchdesigner-mcp` | TouchDesigner control / TouchDesigner 控制 | Real-time visuals / 即時視覺 |
| `understand` | Codebase knowledge graph / 程式碼庫知識圖譜 | Understanding architecture / 理解架構 |
| `understand-chat` | Knowledge graph chat / 知識圖譜對話 | Asking about code / 詢問程式碼 |
| `understand-dashboard` | Knowledge graph visualization / 知識圖譜視覺化 | Visual overview / 視覺概覽 |
| `understand-diff` | Git diff analysis / Git diff 分析 | Understanding changes / 理解變更 |
| `understand-domain` | Business domain extraction / 業務領域提取 | Domain modeling / 領域建模 |
| `understand-explain` | Deep-dive code explanation / 深入程式碼解釋 | Specific file/function / 特定檔案/函式 |
| `understand-knowledge` | Knowledge base analysis / 知識庫分析 | Wiki analysis / Wiki 分析 |
| `understand-onboard` | Onboarding guide / 新手引導指南 | New team members / 新團隊成員 |

---

## Manage Later

```bash
# List categories and current selection / 列出分類與目前選取
bash ~/.agents/skills/skill-manager.sh list

# Add a category / 新增分類
bash ~/.agents/skills/skill-manager.sh enable design

# Remove a category / 移除分類
bash ~/.agents/skills/skill-manager.sh disable social-media

# Switch profile / 切換 profile
bash ~/.agents/skills/skill-manager.sh switch minimal

# Re-apply config after updating / 更新後重新套用設定
bash ~/.agents/skills/skill-manager.sh reapply
```

## How It Works

```
~/.agents/skills/             # Full repo (git source of truth) / 完整 repo（git 來源）
~/.agents/skills-enabled/     # Only selected skills (symlinks) / 僅選取的 skill（symlink）
  ├── categories.json
  ├── agent-development/   → ../skills/agent-development/
  ├── diagnose/            → ../skills/diagnose/
  └── ...

~/.config/opencode/skills/ → ~/.agents/skills-enabled/  [symlink]
~/.claude/skills/          → ~/.agents/skills-enabled/  [symlink]
~/.cursor/skills/          → ~/.agents/skills-enabled/  [symlink]
...
```

All agents point to the same `skills-enabled/` directory. Only the skills you selected are visible to your agents — no trigger pollution, no context waste.

所有 Agent 指向同一個 `skills-enabled/` 目錄。只有你選取的 skill 對 Agent 可見 — 無 trigger 污染、無上下文浪費。

## Update

```bash
(cd ~/.agents/skills && git pull)
bash ~/.agents/skills/skill-manager.sh reapply
```

## License

MIT
